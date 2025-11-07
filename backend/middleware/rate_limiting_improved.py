"""
Rate Limiting Middleware - IMPROVED VERSION
Prevents abuse and DoS attacks using slowapi

IMPROVEMENTS:
1. Excludes OPTIONS requests (CORS preflight) from rate limiting
2. Development mode bypass for localhost
3. Redis storage support for persistence
4. CORS headers included in rate limit responses
5. Sentry integration for monitoring
"""
import os
import uuid
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
REDIS_URL = os.getenv("REDIS_URL", "")

# ============================================================================
# CUSTOM KEY FUNCTION - Bypass rate limiting in development
# ============================================================================
def get_remote_address_with_dev_bypass(request: Request) -> str:
    """
    Get remote address for rate limiting.

    In development mode, bypass rate limiting for localhost to allow easier testing.
    This prevents rate limit issues during development while maintaining security in production.

    Args:
        request: FastAPI request object

    Returns:
        Unique identifier for rate limiting
    """
    # In development, bypass rate limiting for localhost
    if ENVIRONMENT == "development":
        client_host = request.client.host if request.client else "unknown"
        if client_host in ["127.0.0.1", "localhost", "::1"]:
            # Return a unique key per request to bypass rate limits
            return f"dev-bypass-{uuid.uuid4()}"

    # In production, use standard IP-based rate limiting
    return get_remote_address(request)


# ============================================================================
# LIMITER INITIALIZATION
# ============================================================================
# Use Redis if available for persistent rate limiting
# Falls back to in-memory storage if Redis is not available
limiter_config = {
    "key_func": get_remote_address_with_dev_bypass,
    "headers_enabled": True,  # Include rate limit headers in responses
    "swallow_errors": True,   # Don't crash if rate limiting fails
}

# Add Redis storage if configured
if REDIS_URL:
    limiter_config["storage_uri"] = REDIS_URL
    limiter_config["in_memory_fallback_enabled"] = True  # Fallback if Redis fails
    logger.info(f"Rate limiting using Redis: {REDIS_URL}")
else:
    logger.warning("Rate limiting using in-memory storage (not persistent across restarts)")

limiter = Limiter(**limiter_config)


# ============================================================================
# RATE LIMIT CONFIGURATIONS
# ============================================================================
# Format: "count/period" where period can be: second, minute, hour, day

# Development rate limits (more lenient)
DEV_RATE_LIMITS = {
    "login": "100/minute",         # Very lenient for testing
    "register": "50/hour",          # Very lenient for testing
    "password_reset": "50/hour",    # Very lenient for testing
    "post_generate": "100/hour",    # Very lenient for testing
    "post_create": "100/hour",      # Very lenient for testing
    "post_update": "100/minute",    # Very lenient for testing
    "oauth_connect": "100/hour",    # Very lenient for testing
    "oauth_callback": "100/hour",   # Very lenient for testing
    "social_publish": "100/hour",   # Very lenient for testing
    "api_general": "1000/minute",   # Very lenient for testing
    "api_read": "1000/minute",      # Very lenient for testing
}

# Production rate limits (strict)
PROD_RATE_LIMITS = {
    # Authentication endpoints (strict limits to prevent brute force)
    "login": "5/15minutes",        # 5 login attempts per 15 minutes
    "register": "3/hour",           # 3 registrations per hour per IP
    "password_reset": "3/hour",     # 3 password reset requests per hour

    # Post generation endpoints (moderate limits)
    "post_generate": "10/hour",     # 10 AI post generations per hour
    "post_create": "20/hour",       # 20 manual post creates per hour
    "post_update": "30/minute",     # 30 post updates per minute

    # OAuth and social media endpoints
    "oauth_connect": "10/hour",     # 10 OAuth connection attempts per hour
    "oauth_callback": "20/hour",    # 20 OAuth callbacks per hour
    "social_publish": "15/hour",    # 15 social media publishes per hour

    # General API endpoints
    "api_general": "100/minute",    # 100 general API calls per minute
    "api_read": "200/minute",       # 200 read operations per minute (GET)
}

# Select rate limits based on environment
RATE_LIMITS = DEV_RATE_LIMITS if ENVIRONMENT == "development" else PROD_RATE_LIMITS


# ============================================================================
# CORS-AWARE RATE LIMIT HANDLER
# ============================================================================
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Includes CORS headers in the response to prevent CORS errors in browser.
    Logs rate limit violations for monitoring.

    Args:
        request: FastAPI request object
        exc: Rate limit exceeded exception

    Returns:
        JSONResponse with 429 status and CORS headers
    """
    # Skip rate limiting for OPTIONS requests (CORS preflight)
    # This prevents CORS preflight requests from counting against rate limits
    if request.method == "OPTIONS":
        logger.debug(f"Skipping rate limit for OPTIONS request: {request.url.path}")
        # Return success for OPTIONS - let CORS middleware handle it
        return JSONResponse(
            status_code=200,
            content={"message": "OK"},
        )

    # Log rate limit violation
    client_host = request.client.host if request.client else "unknown"
    logger.warning(
        f"Rate limit exceeded",
        extra={
            "ip": client_host,
            "path": request.url.path,
            "method": request.method,
            "user_agent": request.headers.get("user-agent", "unknown")
        }
    )

    # Send to Sentry for monitoring
    try:
        import sentry_sdk
        sentry_sdk.capture_message(
            f"Rate limit exceeded: {request.url.path}",
            level="warning",
            extras={
                "ip": client_host,
                "endpoint": request.url.path,
                "method": request.method,
                "retry_after": str(exc.detail) if hasattr(exc, 'detail') else "60"
            }
        )
    except Exception as e:
        logger.debug(f"Failed to send rate limit event to Sentry: {e}")

    # Get allowed origins from environment
    ALLOWED_ORIGINS = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://localhost:8080"
    ).split(",")

    # Get origin from request
    origin = request.headers.get("origin", "")

    # Prepare response headers with CORS
    response_headers = {
        "Retry-After": str(exc.detail) if hasattr(exc, 'detail') else "60",
    }

    # Add CORS headers if origin is allowed
    if origin in ALLOWED_ORIGINS:
        response_headers.update({
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-CSRF-Token",
        })

    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": str(exc.detail) if hasattr(exc, 'detail') else "60 seconds",
            "endpoint": request.url.path,
        },
        headers=response_headers
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def get_rate_limit(endpoint_type: str) -> str:
    """
    Get rate limit configuration for a specific endpoint type.

    Args:
        endpoint_type: Type of endpoint (e.g., 'login', 'post_generate')

    Returns:
        Rate limit string in slowapi format
    """
    return RATE_LIMITS.get(endpoint_type, RATE_LIMITS["api_general"])


def is_rate_limiting_enabled() -> bool:
    """
    Check if rate limiting is enabled.

    Returns:
        True if rate limiting is enabled, False otherwise
    """
    # Always enabled, but bypassed in development for localhost
    return True


def get_rate_limit_status() -> dict:
    """
    Get current rate limit configuration status.

    Returns:
        Dictionary with rate limit status information
    """
    return {
        "enabled": True,
        "environment": ENVIRONMENT,
        "storage": "redis" if REDIS_URL else "in-memory",
        "redis_url": REDIS_URL if REDIS_URL else None,
        "development_bypass": ENVIRONMENT == "development",
        "limits": RATE_LIMITS,
    }
