"""
Phase 4: Enhanced Security middleware for rate limiting and activity tracking
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import os

from database import SessionLocal, UserSession, get_db
from utils.rate_limiter import RateLimiter, RateLimitExceeded
from utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced middleware for security features:
    - Granular rate limiting
    - Activity tracking
    - Session last activity updates

    IMPORTANT: Skips rate limiting for:
    - OPTIONS requests (CORS preflight)
    - Localhost in development mode
    """

    # Enhanced rate limits - more granular control
    RATE_LIMITS = {
        # Authentication endpoints (stricter)
        "/api/auth/login": {"requests": 5, "window": 900},  # 5 per 15 min
        "/api/auth/register": {"requests": 3, "window": 3600},  # 3 per hour
        "/api/auth/forgot-password": {"requests": 3, "window": 3600},
        "/api/auth/reset-password": {"requests": 5, "window": 3600},
        "/api/auth/send-verification": {"requests": 3, "window": 3600},
        "/api/auth/resend-verification": {"requests": 3, "window": 3600},
        # Sensitive operations (moderate)
        "/api/auth/change-password": {"requests": 5, "window": 3600},
        "/api/auth/delete-account": {"requests": 2, "window": 86400},  # 2 per day
        "/api/auth/api-keys": {"requests": 10, "window": 3600},
        # Regular operations (lenient)
        "/api/auth/me": {"requests": 100, "window": 60},
        "/api/auth/profile": {"requests": 50, "window": 60},
    }

    # Global rate limit per IP
    GLOBAL_RATE_LIMIT = {"requests": 100, "window": 60}  # 100 req/min per IP

    async def dispatch(self, request: Request, call_next):
        """Process request through security checks"""
        # IMPORTANT: Skip rate limiting for OPTIONS requests (CORS preflight)
        # OPTIONS requests MUST pass through to allow CORS middleware to add headers
        if request.method == "OPTIONS":
            response = await call_next(request)
            return response

        # Skip rate limiting for localhost in development
        environment = os.getenv("ENVIRONMENT", "development")
        client_ip = self._get_client_ip(request)
        is_localhost = client_ip in ["127.0.0.1", "::1", "localhost"]

        if environment == "development" and is_localhost:
            # In development, skip rate limiting for localhost
            response = await call_next(request)
            return response

        # Get database session
        db = SessionLocal()

        try:
            # Get client IP address
            ip_address = self._get_client_ip(request)

            # Apply global rate limit
            try:
                self._check_global_rate_limit(ip_address, db)
            except RateLimitExceeded as e:
                db.close()
                return self._rate_limit_response(e.retry_after, "Global rate limit exceeded")

            # Apply endpoint-specific rate limiting
            if request.url.path in self.RATE_LIMITS:
                limit_config = self.RATE_LIMITS[request.url.path]
                try:
                    self._check_endpoint_rate_limit(ip_address, request.url.path, limit_config, db)
                except RateLimitExceeded as e:
                    # Log rate limit exceeded
                    AuditLogger.log_security_event(
                        "rate_limit_exceeded",
                        db,
                        ip_address=ip_address,
                        details={"endpoint": request.url.path, "retry_after": e.retry_after},
                        risk_level="medium",
                    )
                    db.close()
                    return self._rate_limit_response(e.retry_after, "Endpoint rate limit exceeded")

            # Update session last activity if authenticated
            await self._update_session_activity(request, db)

            # Process request
            response = await call_next(request)

            return response

        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}")
            raise
        finally:
            db.close()

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded header (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _check_global_rate_limit(self, ip_address: str, db: Session):
        """Check global rate limit"""
        RateLimiter.check_rate_limit(
            identifier=ip_address,
            endpoint="global",
            db=db,
            max_attempts=self.GLOBAL_RATE_LIMIT["requests"],
            window_minutes=int(self.GLOBAL_RATE_LIMIT["window"] / 60),
        )

    def _check_endpoint_rate_limit(
        self, ip_address: str, endpoint: str, limit_config: dict, db: Session
    ):
        """Check endpoint-specific rate limit"""
        RateLimiter.check_rate_limit(
            identifier=ip_address,
            endpoint=endpoint,
            db=db,
            max_attempts=limit_config["requests"],
            window_minutes=int(limit_config["window"] / 60),
        )

    async def _update_session_activity(self, request: Request, db: Session):
        """Update last activity timestamp for authenticated sessions"""
        # Only update for authenticated requests
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return

        try:
            # Extract token
            token = auth_header.split(" ")[1]

            # Find session
            session = db.query(UserSession).filter(UserSession.token == token).first()

            if session:
                # Update last activity
                session.last_activity = datetime.utcnow()
                db.commit()

        except Exception as e:
            logger.debug(f"Could not update session activity: {str(e)}")
            # Don't fail request if activity update fails

    def _rate_limit_response(self, retry_after: int, message: str = "Rate limit exceeded"):
        """Generate rate limit exceeded response"""
        from starlette.responses import JSONResponse

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error": "Rate limit exceeded",
                "message": f"{message}. Please try again in {retry_after} seconds.",
                "retry_after": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Reset": str(int(datetime.utcnow().timestamp()) + retry_after),
            },
        )


class ActivityLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging security-relevant activities.
    """

    # Endpoints to log
    LOG_ENDPOINTS = {
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/register",
        "/api/auth/change-password",
        "/api/auth/delete-account",
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
    }

    async def dispatch(self, request: Request, call_next):
        """Log security-relevant requests"""
        should_log = request.url.path in self.LOG_ENDPOINTS

        if should_log:
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("User-Agent")

            # Store request info for post-processing
            request.state.log_info = {
                "ip_address": ip_address,
                "user_agent": user_agent,
                "endpoint": request.url.path,
                "method": request.method,
            }

        # Process request
        response = await call_next(request)

        # Log after response (to capture success/failure)
        if should_log and hasattr(request.state, "log_info"):
            # You can extend this to log based on response status
            pass

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"
