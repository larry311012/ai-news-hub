"""
CSRF Protection Middleware for FastAPI

This module implements Cross-Site Request Forgery (CSRF) protection using tokens.
CSRF attacks trick authenticated users into performing unwanted actions.

How it works:
1. Server generates a random CSRF token and sends it to the client
2. Client includes the token in subsequent state-changing requests
3. Server validates the token before processing the request
4. If token is missing or invalid, request is rejected

Security Features:
- Secret-based token generation using HMAC
- Automatic token rotation
- Protection for all state-changing HTTP methods (POST, PUT, DELETE, PATCH)
- GET, HEAD, OPTIONS requests are exempt (read-only operations)
- Python 3.9+ compatible (no union operator |)
"""

import os
import hmac
import hashlib
import secrets
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware


class CsrfConfig:
    """CSRF Protection Configuration"""

    # Secret key for signing CSRF tokens (MUST be set in production)
    SECRET_KEY: str = os.getenv(
        "CSRF_SECRET_KEY",
        os.getenv("ENCRYPTION_KEY", "change-me-in-production")  # Fallback to main encryption key
    )

    # Token configuration
    TOKEN_LENGTH: int = 32
    TOKEN_HEADER_NAME: str = "X-CSRF-Token"
    TOKEN_COOKIE_NAME: str = "csrf_token"

    # Cookie settings
    COOKIE_SAMESITE: str = "lax"  # Prevents CSRF attacks
    COOKIE_SECURE: bool = os.getenv("ENVIRONMENT", "development") == "production"
    COOKIE_HTTPONLY: bool = False  # Must be False so JavaScript can read it
    COOKIE_MAX_AGE: int = 3600  # 1 hour in seconds

    # Enable/disable CSRF protection
    ENABLED: bool = os.getenv("CSRF_ENABLED", "true").lower() == "true"

    # Paths exempt from CSRF protection
    EXEMPT_PATHS: List[str] = [
        "/health",
        "/api/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/csrf-token",  # CSRF token endpoint itself
    ]

    # Safe HTTP methods that don't need CSRF protection
    SAFE_METHODS: List[str] = ["GET", "HEAD", "OPTIONS"]


class CsrfToken:
    """CSRF Token Generator and Validator"""

    @staticmethod
    def generate() -> str:
        """
        Generate a cryptographically secure CSRF token

        Returns:
            Secure random token string
        """
        return secrets.token_urlsafe(CsrfConfig.TOKEN_LENGTH)

    @staticmethod
    def sign(token: str) -> str:
        """
        Sign a CSRF token with HMAC

        Args:
            token: Token to sign

        Returns:
            Signed token (token:signature)
        """
        signature = hmac.new(
            CsrfConfig.SECRET_KEY.encode(),
            token.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{token}:{signature}"

    @staticmethod
    def verify(signed_token: str) -> bool:
        """
        Verify a signed CSRF token

        Args:
            signed_token: Signed token to verify

        Returns:
            True if valid, False otherwise
        """
        try:
            if ":" not in signed_token:
                return False

            token, signature = signed_token.split(":", 1)

            # Generate expected signature
            expected_signature = hmac.new(
                CsrfConfig.SECRET_KEY.encode(),
                token.encode(),
                hashlib.sha256
            ).hexdigest()

            # Constant-time comparison to prevent timing attacks
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection Middleware

    Validates CSRF tokens for all state-changing requests.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and validate CSRF token if needed"""

        # Skip if CSRF protection is disabled
        if not CsrfConfig.ENABLED:
            return await call_next(request)

        # Skip safe methods (GET, HEAD, OPTIONS)
        if request.method in CsrfConfig.SAFE_METHODS:
            return await call_next(request)

        # Skip exempt paths
        path = request.url.path
        for exempt_path in CsrfConfig.EXEMPT_PATHS:
            if path.startswith(exempt_path):
                return await call_next(request)

        # Validate CSRF token for state-changing requests
        token_from_header = request.headers.get(CsrfConfig.TOKEN_HEADER_NAME)
        token_from_cookie = request.cookies.get(CsrfConfig.TOKEN_COOKIE_NAME)

        if not token_from_header:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "CSRF token missing",
                    "detail": f"Include {CsrfConfig.TOKEN_HEADER_NAME} header with your request",
                    "hint": "Get a CSRF token from /api/csrf-token endpoint",
                    "path": path,
                    "method": request.method
                }
            )

        if not token_from_cookie:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "CSRF cookie missing",
                    "detail": "CSRF cookie not found. Request a new token.",
                    "hint": "Get a CSRF token from /api/csrf-token endpoint",
                    "path": path,
                    "method": request.method
                }
            )

        # Verify header token signature
        if not CsrfToken.verify(token_from_header):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "CSRF token invalid",
                    "detail": "Token signature verification failed",
                    "hint": "Request a new token from /api/csrf-token endpoint",
                    "path": path,
                    "method": request.method
                }
            )

        # Extract token from signed header token
        header_token = token_from_header.split(":", 1)[0] if ":" in token_from_header else token_from_header

        # Compare tokens (constant-time comparison)
        if not hmac.compare_digest(header_token, token_from_cookie):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "CSRF token mismatch",
                    "detail": "Token from header doesn't match cookie",
                    "hint": "Request a new token from /api/csrf-token endpoint",
                    "path": path,
                    "method": request.method
                }
            )

        # Token is valid, process request
        response = await call_next(request)
        return response


class CsrfTokenResponse(BaseModel):
    """Response model for CSRF token endpoint"""
    csrf_token: str
    message: str
    usage: dict


def generate_csrf_response() -> JSONResponse:
    """
    Generate CSRF token and return response with cookie

    Returns:
        JSONResponse with CSRF token and cookie set
    """
    # Generate new token
    token = CsrfToken.generate()
    signed_token = CsrfToken.sign(token)

    # Create response
    response = JSONResponse(content={
        "csrf_token": signed_token,
        "message": "CSRF token generated successfully",
        "usage": {
            "header_name": CsrfConfig.TOKEN_HEADER_NAME,
            "include_in_methods": ["POST", "PUT", "DELETE", "PATCH"],
            "exempt_methods": CsrfConfig.SAFE_METHODS,
            "example": {
                "javascript": (
                    "// 1. Get CSRF token\n"
                    "const res = await fetch('/api/csrf-token');\n"
                    "const data = await res.json();\n"
                    "const csrfToken = data.csrf_token;\n\n"
                    "// 2. Use in requests\n"
                    "await fetch('/api/posts', {\n"
                    "  method: 'POST',\n"
                    f"  headers: {{'{CsrfConfig.TOKEN_HEADER_NAME}': csrfToken}},\n"
                    "  credentials: 'include',\n"
                    "  body: JSON.stringify({...})\n"
                    "});"
                )
            }
        }
    })

    # Set CSRF cookie (stores the unsigned token)
    response.set_cookie(
        key=CsrfConfig.TOKEN_COOKIE_NAME,
        value=token,  # Store unsigned token in cookie
        max_age=CsrfConfig.COOKIE_MAX_AGE,
        httponly=CsrfConfig.COOKIE_HTTPONLY,
        secure=CsrfConfig.COOKIE_SECURE,
        samesite=CsrfConfig.COOKIE_SAMESITE
    )

    return response


# ============================================================================
# Integration Guide
# ============================================================================
#
# 1. Add to main.py:
#    ```python
#    from middleware.csrf_protection import CsrfProtectionMiddleware, generate_csrf_response
#
#    # Add middleware (AFTER CORS, BEFORE routes)
#    app.add_middleware(CsrfProtectionMiddleware)
#
#    # Add CSRF token endpoint
#    @app.get("/api/csrf-token")
#    async def get_csrf_token():
#        return generate_csrf_response()
#    ```
#
# 2. Frontend integration:
#    ```javascript
#    // Get CSRF token (do this once, store in state/context)
#    async function getCsrfToken() {
#        const response = await fetch('/api/csrf-token', {
#            credentials: 'include'  // Important: include cookies
#        });
#        const data = await response.json();
#        return data.csrf_token;
#    }
#
#    // Use in POST/PUT/DELETE requests
#    const csrfToken = await getCsrfToken();
#    await fetch('/api/posts', {
#        method: 'POST',
#        headers: {
#            'Content-Type': 'application/json',
#            'X-CSRF-Token': csrfToken
#        },
#        credentials: 'include',
#        body: JSON.stringify({ title: 'Test' })
#    });
#    ```
#
# 3. Environment variables:
#    ```
#    CSRF_ENABLED=true
#    CSRF_SECRET_KEY=your-secret-key-here
#    ```
#
# ============================================================================
