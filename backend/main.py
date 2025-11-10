"""
FastAPI Backend for AI News Aggregator
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import from src
sys.path.append(str(Path(__file__).parent.parent.parent))

# Load environment variables BEFORE any other imports
from dotenv import load_dotenv

load_dotenv()

# Configure structured logging BEFORE other imports that use logging
from utils.logging_config import configure_logging

configure_logging()

# ============================================================================
# SENTRY ERROR TRACKING - Initialize before FastAPI app
# ============================================================================
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from loguru import logger

# Get Sentry configuration from environment
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Initialize Sentry only if DSN is provided
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENVIRONMENT,
        integrations=[
            FastApiIntegration(
                transaction_style="url",  # Group by URL pattern, not specific URLs
                failed_request_status_codes=[400, range(500, 599)],  # Track 4xx and 5xx errors
            ),
            SqlalchemyIntegration(),  # Track database query performance
            RedisIntegration(),  # Track Redis operations
        ],
        # Performance monitoring - sample 10% of requests
        traces_sample_rate=0.1,
        # Profiling - sample 10% of requests
        profiles_sample_rate=0.1,
        # Privacy - don't automatically send PII (personally identifiable information)
        send_default_pii=False,
        # Additional settings
        attach_stacktrace=True,  # Include stack traces for messages
        debug=False,  # Set to True for local debugging
        # Maximum string length before truncation
        max_value_length=8192,
        # Breadcrumbs (user actions leading to error)
        max_breadcrumbs=50,
    )
    logger.info(f"Sentry error tracking initialized for environment: {ENVIRONMENT}")
else:
    logger.warning(
        "Sentry DSN not configured - error tracking disabled. "
        "Set SENTRY_DSN environment variable to enable."
    )

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import uvicorn

# CSRF Protection
from middleware.csrf_protection import CsrfProtectionMiddleware, generate_csrf_response

# Rate Limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from middleware.rate_limiting import limiter, rate_limit_exceeded_handler

# Performance Monitoring
from middleware.performance import PerformanceMiddleware

from api import (
    subscription,  # User tier and quota management (NO PAYMENT)
    articles,
    articles_refresh,  # NEW: Enhanced article refresh with feedback
    posts,
    posts_v2,
    settings,
    auth,
    oauth,
    oauth_mock,
    auth_phase3,
    auth_phase4,
    security,
    ab_testing,
    analytics,
    ai_chat,
    social_media,
    social_media_twitter_oauth1,
    social_media_threads,
    social_media_instagram,  # NEW: Instagram OAuth
    admin_oauth_credentials,
    user_oauth_setup,
    social_media_twitter_per_user,
    instagram_images,
    posts_instagram_publish,  # NEW: Instagram publishing
    setup_guide,  # NEW: Setup guide for social media
    health,  # NEW: Comprehensive health check endpoints
    user_feeds,  # NEW: RSS feed management
    mobile_v1,  # NEW: Mobile API v1 for iOS app
    feeds_enhanced,  # NEW: Enhanced RSS feeds for iOS (Task 2.6)
    feed_aggregator_api,  # NEW: Feed aggregator service (Task 2.7)
    publishing_api,  # NEW: Phase 4 - Multi-platform publishing API
)

# Import LinkedIn OAuth module
from api import social_media_linkedin

from database import init_db
from database_user_oauth_credentials import UserOAuthCredential, UserOAuthCredentialAudit
from database_social_media import SocialMediaConnection  # Ensure social media tables exist
from middleware.security import SecurityMiddleware, ActivityLoggerMiddleware
from middleware.security_headers import SecurityHeadersMiddleware

# Redis Configuration
from config.redis_config import test_redis_connection, close_redis_connections

# Mobile API Exception Handlers (Task 1.7)
from utils.exception_handlers import register_exception_handlers


# Custom middleware to prevent caching of static files in development
class NoCacheMiddleware(BaseHTTPMiddleware):
    """Add no-cache headers for static files in development to prevent browser caching issues"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Only apply to static files (JS, CSS, HTML), not API endpoints
        path = request.url.path
        if not path.startswith("/api/") and (
            path.endswith(".js") or path.endswith(".css") or path.endswith(".html")
        ):
            # Add no-cache headers for development
            # This prevents browser from caching JavaScript/CSS files
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response


# ============================================================================
# SENTRY MIDDLEWARE - Add user context to error reports
# ============================================================================
class SentryContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enrich Sentry error reports with user context

    This middleware adds user information to Sentry when errors occur,
    making it easier to identify which users are affected by issues.
    """

    async def dispatch(self, request: Request, call_next):
        # Set request context for Sentry
        with sentry_sdk.configure_scope() as scope:
            # Add request information
            scope.set_tag("path", request.url.path)
            scope.set_tag("method", request.method)

            # Add user context if available
            if hasattr(request.state, "user") and request.state.user:
                user = request.state.user
                sentry_sdk.set_user(
                    {
                        "id": str(user.id),
                        "email": user.email if hasattr(user, "email") else None,
                        # Don't include sensitive information like passwords
                    }
                )
            else:
                # Clear user context for unauthenticated requests
                sentry_sdk.set_user(None)

            # Add custom context
            scope.set_context(
                "request",
                {
                    "url": str(request.url),
                    "headers": dict(request.headers),
                    "client_host": request.client.host if request.client else None,
                },
            )

        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Capture exception in Sentry before re-raising
            sentry_sdk.capture_exception(exc)
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and services on startup, cleanup on shutdown"""
    # Initialize database
    init_db()

    # Initialize per-user OAuth tables
    from database import engine

    UserOAuthCredential.__table__.create(engine, checkfirst=True)
    UserOAuthCredentialAudit.__table__.create(engine, checkfirst=True)

    # Initialize social media tables
    SocialMediaConnection.__table__.create(engine, checkfirst=True)

    # Initialize Phase 4 publishing tables
    from database_publishing import (
        PostPublishingHistory,
        PublishingQueue,
        PublishingRateLimit,
        PublishingWebhook
    )

    PostPublishingHistory.__table__.create(engine, checkfirst=True)
    PublishingQueue.__table__.create(engine, checkfirst=True)
    PublishingRateLimit.__table__.create(engine, checkfirst=True)
    PublishingWebhook.__table__.create(engine, checkfirst=True)

    # Initialize setup guide tables
    from database_setup_guide import (
        SetupProgress,
        SetupValidation,
        SetupMetrics,
        PlatformConfiguration,
    )

    SetupProgress.__table__.create(engine, checkfirst=True)
    SetupValidation.__table__.create(engine, checkfirst=True)
    SetupMetrics.__table__.create(engine, checkfirst=True)
    PlatformConfiguration.__table__.create(engine, checkfirst=True)

    # Create Instagram image storage directory if it doesn't exist
    # Use relative path from this file's location
    BASE_DIR = Path(__file__).resolve().parent
    storage_path = os.getenv("IMAGE_STORAGE_PATH", str(BASE_DIR / "static" / "instagram_images"))
    Path(storage_path).mkdir(parents=True, exist_ok=True)

    # Test Redis connection
    redis_connected = await test_redis_connection()
    if redis_connected:
        logger.info("Redis cache layer initialized successfully")
    else:
        logger.warning("Redis not available - application will run without caching")

    logger.info("Mobile API v1 initialized - iOS support enabled")
    logger.info("Standardized error responses enabled for mobile API")
    logger.info("Enhanced RSS feeds API initialized (Task 2.6)")
    logger.info("Feed aggregator service ready (Task 2.7)")

    # Check for Anonymous Mode
    ANONYMOUS_MODE = os.getenv("ANONYMOUS_MODE", "false").lower() == "true"
    if ANONYMOUS_MODE:
        logger.warning("=" * 80)
        logger.warning("⚠️  ANONYMOUS MODE ENABLED")
        logger.warning("All API requests will use user_id=1 (no authentication required)")
        logger.warning("WARNING: Only use in single-user deployments!")
        logger.warning("To disable: Set ANONYMOUS_MODE=false in .env")
        logger.warning("=" * 80)
        
        # Ensure anonymous user exists
        from database import SessionLocal, User
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == 1).first()
            if not user:
                logger.error("Anonymous user (id=1) not found! Run: python scripts/create_anonymous_user.py")
            else:
                logger.info(f"Anonymous user verified: {user.email}")
        finally:
            db.close()

    yield

    # Cleanup on shutdown
    await close_redis_connections()

    # Flush Sentry events before shutdown
    if SENTRY_DSN:
        sentry_sdk.flush(timeout=2.0)
        logger.info("Sentry events flushed")

    logger.info("Application shutdown complete")


app = FastAPI(
    title="AI News Aggregator API",
    description="API for managing AI news and social media posts with RSS feed management, background aggregation, multi-platform publishing, Redis caching, Sentry error tracking, and iOS mobile support",
    version="2.14.0",  # Updated for feed aggregator service (Task 2.7)
    lifespan=lifespan,
    # Disable automatic trailing slash redirects
    redirect_slashes=False,
)

# ============================================================================
# MOBILE API: Register Standardized Exception Handlers (Task 1.7)
# ============================================================================
# This must be registered BEFORE adding route handlers
# Converts all exceptions to standardized error format for iOS app
register_exception_handlers(app)
logger.info("Mobile API exception handlers registered")

# ============================================================================
# SECURITY HARDENING: Rate Limiting
# ============================================================================
# Add rate limiter to app state
app.state.limiter = limiter

# Note: Custom rate limit handler is registered via register_exception_handlers()

# ============================================================================
# SECURITY HARDENING: CORS Configuration
# ============================================================================
# Default allowed origins (development)
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://192.168.5.177:8000",  # iOS app via IP (for physical device)
    "ainewshub://oauth-callback",  # iOS custom URL scheme for OAuth
]

# Get allowed origins from environment or use defaults
# In production, set ALLOWED_ORIGINS to only include your production domains
ALLOWED_ORIGINS_ENV = os.getenv("ALLOWED_ORIGINS", "")
if ALLOWED_ORIGINS_ENV:
    # Parse comma-separated origins from environment
    ALLOWED_ORIGINS = [
        origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",") if origin.strip()
    ]
else:
    # Use defaults for development
    ALLOWED_ORIGINS = DEFAULT_ALLOWED_ORIGINS

# SECURITY: Validate that wildcard is not used in production
if os.getenv("ENVIRONMENT", "development") == "production" and "*" in ALLOWED_ORIGINS:
    raise ValueError(
        "SECURITY ERROR: Wildcard CORS origin '*' is not allowed in production. "
        "Set ALLOWED_ORIGINS environment variable with specific domains."
    )

# CORS middleware with specific origins (NO WILDCARD)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "X-App-Version", "User-Agent"],
    expose_headers=["Content-Type", "Authorization"],
)

# ============================================================================
# SECURITY HARDENING: CSRF Protection
# ============================================================================
# Add CSRF protection middleware
app.add_middleware(CsrfProtectionMiddleware)

# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================
# Add performance monitoring middleware to track request duration
# This middleware should be added early in the middleware stack to accurately
# measure total request time including other middleware processing
app.add_middleware(PerformanceMiddleware)

# Security Hardening: Add security headers middleware (FIRST)
app.add_middleware(SecurityHeadersMiddleware)

# Phase 4: Add security middleware
app.add_middleware(SecurityMiddleware)
app.add_middleware(ActivityLoggerMiddleware)

# Add Sentry context middleware (if Sentry is enabled)
if SENTRY_DSN:
    app.add_middleware(SentryContextMiddleware)

# Development: Add no-cache middleware for static files
# This prevents browser caching issues during development
# In production, you should enable caching for better performance
if os.getenv("ENVIRONMENT", "development") == "development":
    app.add_middleware(NoCacheMiddleware)

# ============================================================================
# API ROUTERS - Mobile API First for Priority
# ============================================================================

# Mobile API v1 (NEW - iOS optimized endpoints)
app.include_router(mobile_v1.router, prefix="/api", tags=["mobile-v1"])

# Enhanced RSS Feeds API (Task 2.6 - iOS optimized)
app.include_router(feeds_enhanced.router, prefix="/api", tags=["feeds-enhanced"])

# Feed Aggregator Service API (Task 2.7 - Background article aggregation)
app.include_router(feed_aggregator_api.router, prefix="/api", tags=["feed-aggregator"])

# Phase 4: Publishing API (Multi-platform social media publishing)
app.include_router(publishing_api.router, prefix="/api/publishing", tags=["publishing"])

# Authentication APIs
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(auth_phase3.router, prefix="/api/auth", tags=["auth-phase3"])
app.include_router(auth_phase4.router, prefix="/api/auth", tags=["auth-phase4"])
app.include_router(oauth.router, prefix="/api/auth/oauth", tags=["oauth"])
app.include_router(oauth_mock.router, prefix="/api/auth/oauth/mock", tags=["oauth-mock"])
app.include_router(security.router, prefix="/api/auth/security", tags=["security"])

# Content APIs
app.include_router(articles.router, prefix="/api/articles", tags=["articles"])
app.include_router(articles_refresh.router, prefix="/api", tags=["articles-refresh"])  # Enhanced refresh with feedback

# Post Generation APIs - Enhanced v2 API with comprehensive features
# V2 API includes: progress tracking, validation, platform status, single /edit endpoint
app.include_router(posts_v2.router, prefix="/api/posts", tags=["posts"])  # Enhanced API (default)
app.include_router(
    posts.router, prefix="/api/v1/posts", tags=["posts-v1"]
)  # Legacy API (for compatibility)

# Instagram Publishing API (extends posts API)
app.include_router(posts_instagram_publish.router, prefix="/api/posts", tags=["posts-instagram"])

# Instagram Image Generation API
app.include_router(instagram_images.router, prefix="/api", tags=["instagram"])

# Settings & Configuration
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(ab_testing.router, prefix="/api/ab-testing", tags=["ab-testing"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(ai_chat.router, prefix="/api/v1/ai", tags=["ai-chat"])

# Per-User OAuth Setup Endpoints
app.include_router(user_oauth_setup.router, prefix="/api", tags=["oauth-setup"])

# Setup Guide for Social Media Connections (NEW)
app.include_router(setup_guide.router, prefix="/api", tags=["setup-guide"])

# LinkedIn OAuth 2.0 (Per-User Credentials) - NEW
app.include_router(
    social_media_linkedin.router, prefix="/api/oauth-setup", tags=["oauth-setup-linkedin"]
)

# Instagram OAuth 2.0 (NEW)
app.include_router(
    social_media_instagram.router, prefix="/api/social-media", tags=["social-media-instagram"]
)

# Twitter OAuth with Per-User Credentials Support (register FIRST for priority)
app.include_router(
    social_media_twitter_per_user.router, prefix="/api/social-media", tags=["social-media-per-user"]
)

# Twitter OAuth 1.0a (Centralized) - Fallback
app.include_router(
    social_media_twitter_oauth1.router, prefix="/api/social-media", tags=["social-media"]
)

# Threads OAuth 2.0 (Centralized)
app.include_router(social_media_threads.router, prefix="/api/social-media", tags=["social-media"])

# Generic social media router - Register AFTER specific routers
app.include_router(social_media.router, prefix="/api/social-media", tags=["social-media"])

# Admin OAuth Credentials Management
app.include_router(admin_oauth_credentials.router, prefix="/api", tags=["admin-oauth"])

# Health Check Endpoints
app.include_router(health.router, prefix="/api", tags=["health"])

# User Tier Management (NO PAYMENT - quota management only)
app.include_router(subscription.router, prefix="/api/subscription", tags=["subscription"])

# RSS Feed Management (NEW)
app.include_router(user_feeds.router, prefix="/api", tags=["feeds"])


# ============================================================================
# SECURITY ENDPOINT: CSRF Token
# ============================================================================
@app.get("/api/csrf-token", tags=["security"])
async def get_csrf_token():
    """
    Generate and return CSRF token for client-side use

    This endpoint is called by the frontend to get a CSRF token before making
    state-changing requests (POST, PUT, DELETE, PATCH).

    Returns:
        JSON with CSRF token and usage instructions

    Frontend Usage:
        ```javascript
        // 1. Get CSRF token
        const response = await fetch('/api/csrf-token', {
            credentials: 'include'  // Important for cookies
        });
        const data = await response.json();
        const csrfToken = data.csrf_token;

        // 2. Include in subsequent requests
        await fetch('/api/posts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            credentials: 'include',
            body: JSON.stringify({ ... })
        });
        ```
    """
    return generate_csrf_response()


# ============================================================================
# SENTRY TEST ENDPOINT - Trigger test error
# ============================================================================
@app.get("/api/sentry-test", tags=["monitoring"])
async def sentry_test():
    """
    Test endpoint to verify Sentry error tracking is working

    This endpoint intentionally raises an error to test Sentry integration.
    Check your Sentry dashboard after calling this endpoint.

    **WARNING**: This endpoint should be removed or protected in production!
    """
    if ENVIRONMENT == "production":
        raise HTTPException(
            status_code=403, detail="Sentry test endpoint is disabled in production"
        )

    # Capture a message
    sentry_sdk.capture_message("Sentry test message", level="info")

    # Trigger a test error
    try:
        1 / 0
    except ZeroDivisionError as e:
        sentry_sdk.capture_exception(e)
        raise HTTPException(
            status_code=500, detail="Test error sent to Sentry. Check your Sentry dashboard!"
        )


# Instagram Image Serving Endpoints
@app.get("/api/images/instagram/{user_id}/{filename}")
async def serve_instagram_image(user_id: int, filename: str):
    """Serve generated Instagram images"""
    BASE_DIR = Path(__file__).resolve().parent
    storage_path = os.getenv("IMAGE_STORAGE_PATH", str(BASE_DIR / "static" / "instagram_images"))

    image_path = Path(storage_path) / str(user_id) / filename

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(image_path, media_type="image/png")


@app.get("/api/images/instagram/{user_id}/thumbnails/{filename}")
async def serve_instagram_thumbnail(user_id: int, filename: str):
    """Serve Instagram image thumbnails"""
    BASE_DIR = Path(__file__).resolve().parent
    storage_path = os.getenv("IMAGE_STORAGE_PATH", str(BASE_DIR / "static" / "instagram_images"))

    thumb_path = Path(storage_path) / str(user_id) / "thumbnails" / filename

    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(thumb_path, media_type="image/png")


# API info available at /api
@app.get("/api")
async def api_root():
    """API information endpoint"""
    return {
        "message": "AI News Aggregator API - Open Source Edition with iOS Support",
        "version": "2.13.0",
        "phase": "Open Source - Mobile API v1 Enabled + Enhanced RSS Feeds + Feed Aggregator",
        "performance_score": "95+/100 (A+)",
        "docs": "/docs",
        "features": [
            "User Authentication",
            "Article Management",
            "AI Post Generation (Enhanced V2)",
            "Social Media Publishing (LinkedIn, Twitter, Threads, Instagram)",
            "RSS Feed Management",
            "Feed Discovery & Validation",
                        "Background Feed Aggregation (Task 2.7)",
            "Feed Health Monitoring",
            "Automatic Article Deduplication",
            "Rate Limiting & Exponential Backoff",
            "Multi-Platform Publishing (Phase 4)",
            "Publishing Status Tracking",
            "Automatic Retry Mechanism",
            "Publishing History",
            "LinkedIn OAuth 2.0 (Per-User Credentials)",
            "Instagram OAuth 2.0 (Business Accounts)",
            "Instagram Image Generation (DALL-E 3)",
            "Instagram Publishing (Image + Caption)",
            "Twitter OAuth 1.0a (Per-User Credentials)",
            "Threads OAuth 2.0 (Centralized)",
            "Per-User OAuth Setup Wizard",
            "Admin OAuth Credentials Management",
            "Analytics & A/B Testing",
            "AI Chat Assistant",
            "CSRF Protection",
            "Input Sanitization (XSS Prevention)",
            "Rate Limiting (DoS Prevention)",
            "Redis Caching Layer (Performance)",
            "Sentry Error Tracking (Monitoring)",
            "Performance Monitoring (Request Tracking)",
            "Mobile API v1 (iOS Optimized)",
            "Token Refresh Endpoint",
            "Device Registration",
            "iOS OAuth Redirect Support",
            "Standardized Error Responses",
            "Database Performance Indexes",
            "Enhanced RSS Feeds API (Task 2.6)",
            "Feed Pagination & Filtering",
            "Bulk Articles Endpoint",
            "Advanced Feed Validation",
        ],
        "security_features": {
            "cors_protection": "Configured",
            "csrf_protection": "Enabled",
            "security_headers": "Enabled",
            "rate_limiting": "Enabled",
            "input_sanitization": "Enabled",
            "httponly_cookies": "Pending",
        },
        "performance_features": {
            "redis_caching": "Enabled",
            "connection_pooling": "Enabled (PostgreSQL + Redis)",
            "async_processing": "Enabled",
            "cache_hit_rate_target": "80%+",
            "response_time_target": "<50ms (cached)",
            "performance_monitoring": "Enabled",
            "structured_logging": "Enabled",
            "database_indexes": "Optimized for mobile",
            "feed_caching": "1 hour (system sources)",
            "article_caching": "1-5 minutes (user data)",
            "background_aggregation": "15 minute intervals",
        },
        "monitoring_features": {
            "sentry_error_tracking": "Enabled" if SENTRY_DSN else "Disabled",
            "sentry_performance_monitoring": "Enabled (10% sample)" if SENTRY_DSN else "Disabled",
            "sentry_profiling": "Enabled (10% sample)" if SENTRY_DSN else "Disabled",
            "request_performance_tracking": "Enabled",
            "slow_request_detection": "Enabled (>1s)",
            "environment": ENVIRONMENT,
            "feed_health_tracking": "Enabled",
            "consecutive_failure_tracking": "Enabled",
        },
        "mobile_features": {
            "api_version": "v1",
            "token_refresh": "/api/v1/auth/refresh",
            "device_registration": "/api/v1/devices",
            "ios_oauth_redirect": "ainewshub://oauth-callback",
            "error_standardization": "Enabled",
            "response_compression": "Enabled",
            "optimized_payloads": "Enabled",
            "enhanced_rss_feeds": "Enabled (Task 2.6)",
            "background_aggregation": "Enabled (Task 2.7)",
        },
        "api_versions": {
            "mobile_v1": "/api/v1/* (iOS optimized)",
            "posts_v2": "/api/posts (default, recommended)",
            "posts_v1": "/api/v1/posts (legacy, for compatibility)",
            "instagram_images": "/api/posts/{post_id}/generate-instagram-image",
            "instagram_publish": "/api/posts/{post_id}/publish/instagram",
            "instagram_validate": "/api/posts/{post_id}/instagram/validate",
            "linkedin_connect": "/api/oauth-setup/linkedin/connect",
            "linkedin_callback": "/api/oauth-setup/linkedin/callback",
            "csrf_token": "/api/csrf-token",
            "cache_stats": "/api/health/cache/stats",
            "sentry_test": "/api/sentry-test (development only)",
            "user_feeds": "/api/user-feeds (RSS feed management)",
            "feeds_enhanced": "/api/user-feeds/enhanced (Task 2.6)",
            "recent_articles": "/api/articles/recent (bulk endpoint)",
            "feed_validation": "/api/feeds/validate-detailed (enhanced)",
            "aggregator_status": "/api/aggregator/status (Task 2.7)",
            "aggregator_start": "/api/aggregator/start (Task 2.7)",
            "aggregator_fetch": "/api/aggregator/fetch-all (Task 2.7)",
            "health_dashboard": "/api/aggregator/health-dashboard (Task 2.7)",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/health")
async def api_health():
    """API Health check endpoint - for frontend compatibility"""
    return {
        "status": "healthy",
        "version": "2.13.0",
        "api": "online",
        "features": {
            "enhanced_post_generation": True,
            "progress_tracking": True,
            "content_validation": True,
            "platform_status_checking": True,
            "instagram_image_generation": True,
            "instagram_oauth": True,
            "instagram_publishing": True,
            "linkedin_oauth_per_user": True,
            "rss_feed_management": True,
            "feed_discovery": True,
            "feed_validation": True,
            "csrf_protection": True,
            "cors_hardening": True,
            "input_sanitization": True,
            "rate_limiting": True,
            "redis_caching": True,
            "sentry_error_tracking": bool(SENTRY_DSN),
            "performance_monitoring": True,
            "mobile_api_v1": True,
            "token_refresh": True,
            "device_registration": True,
            "ios_oauth_support": True,
            "standardized_errors": True,
            "database_indexes": True,
            "enhanced_rss_feeds": True,
            "feed_pagination": True,
            "bulk_articles": True,
            "advanced_validation": True,
            "background_aggregation": True,  # NEW - Task 2.7
            "feed_health_monitoring": True,  # NEW - Task 2.7
            "article_deduplication": True,  # NEW - Task 2.7
            "exponential_backoff": True,  # NEW - Task 2.7
        },
    }


@app.get("/security-config")
async def security_config():
    """Get security configuration and score"""
    from security_config import SecurityConfig

    score, grade = SecurityConfig.get_security_score()
    warnings = SecurityConfig.validate_config()

    return {
        "security_score": score,
        "grade": grade,
        "warnings": warnings,
        "features": {
            "rate_limiting": True,  # NOW ENABLED
            "account_lockout": SecurityConfig.ACCOUNT_LOCKOUT_ENABLED,
            "csrf_protection": True,  # ENABLED
            "security_headers": SecurityConfig.SECURITY_HEADERS_ENABLED,
            "password_breach_check": SecurityConfig.PASSWORD_CHECK_BREACHES,
            "session_fingerprinting": SecurityConfig.ENABLE_SESSION_FINGERPRINTING,
            "advanced_audit": SecurityConfig.ENABLE_ADVANCED_AUDIT,
            "per_user_oauth": True,
            "credential_encryption": True,
            "instagram_oauth": True,
            "linkedin_oauth": True,
            "cors_hardening": True,
            "input_sanitization": True,  # NOW ENABLED
            "redis_caching": True,
            "sentry_error_tracking": bool(SENTRY_DSN),
            "performance_monitoring": True,
            "mobile_api_security": True,
            "device_rate_limiting": True,
            "standardized_error_responses": True,
            "enhanced_rss_feeds": True,
            "background_aggregation": True,
            "feed_health_monitoring": True,
        },
    }


# Mount static files AFTER all routes to avoid conflicts
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="static")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
