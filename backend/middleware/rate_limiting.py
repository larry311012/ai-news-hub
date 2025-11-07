"""
Rate Limiting Middleware
Prevents abuse and DoS attacks using slowapi
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

# Initialize limiter with remote address as key
limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations
# Format: "count/period" where period can be: second, minute, hour, day
RATE_LIMITS = {
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


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Returns a 429 status code with retry information.
    """
    logger.warning(
        f"Rate limit exceeded for {request.client.host} on {request.url.path}",
        extra={
            "ip": request.client.host,
            "path": request.url.path,
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": str(exc.detail) if hasattr(exc, 'detail') else "60 seconds"
        },
        headers={
            "Retry-After": str(exc.detail) if hasattr(exc, 'detail') else "60"
        }
    )


def get_rate_limit(endpoint_type: str) -> str:
    """
    Get rate limit configuration for a specific endpoint type.

    Args:
        endpoint_type: Type of endpoint (e.g., 'login', 'post_generate')

    Returns:
        Rate limit string in slowapi format
    """
    return RATE_LIMITS.get(endpoint_type, RATE_LIMITS["api_general"])
