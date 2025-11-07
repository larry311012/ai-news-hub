"""
Global Exception Handlers for Mobile API (Task 1.7)

FastAPI global exception handlers that intercept all HTTPExceptions
and convert them to standardized error responses for iOS app.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded
from datetime import datetime
from typing import Any, Dict
import logging

from utils.error_responses import ErrorCode, create_error_response

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Global handler for HTTPExceptions to standardize error responses.

    Converts all HTTPException instances to standardized error format
    with proper error codes and timestamps.

    Args:
        request: FastAPI request object
        exc: HTTPException instance

    Returns:
        JSONResponse with standardized error format
    """
    # Check if the exception already has standardized error format
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        # Already in standard format (from create_error_exception)
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )

    # Map HTTP status codes to error codes
    error_code = map_status_to_error_code(exc.status_code, str(exc.detail))

    # Create standardized response
    error_response = {
        "error": {
            "code": error_code,
            "message": str(exc.detail),
            "details": {},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }

    # Log error for monitoring
    logger.warning(
        f"HTTP Exception: {error_code} - {exc.detail} "
        f"(Status: {exc.status_code}, Path: {request.url.path})"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors with standardized format.

    Converts validation errors to user-friendly messages with
    detailed field-level error information.

    Args:
        request: FastAPI request object
        exc: RequestValidationError instance

    Returns:
        JSONResponse with validation error details
    """
    # Extract validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })

    # Create standardized response
    error_response = {
        "error": {
            "code": ErrorCode.VALIDATION_INVALID_INPUT.value,
            "message": "Validation failed for one or more fields",
            "details": {
                "validation_errors": errors
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }

    logger.warning(
        f"Validation Error: {len(errors)} field(s) failed "
        f"(Path: {request.url.path})"
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response
    )


async def rate_limit_exception_handler(
    request: Request,
    exc: RateLimitExceeded
) -> JSONResponse:
    """
    Handle rate limit exceeded errors with standardized format.

    Args:
        request: FastAPI request object
        exc: RateLimitExceeded instance

    Returns:
        JSONResponse with rate limit error
    """
    error_response = {
        "error": {
            "code": ErrorCode.RATE_LIMIT_EXCEEDED.value,
            "message": "Too many requests. Please try again later.",
            "details": {
                "retry_after": 60  # seconds
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }

    logger.warning(
        f"Rate Limit Exceeded: {request.client.host if request.client else 'unknown'} "
        f"(Path: {request.url.path})"
    )

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_response,
        headers={"Retry-After": "60"}
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions with standardized format.

    Last resort handler for any unhandled exceptions.

    Args:
        request: FastAPI request object
        exc: Exception instance

    Returns:
        JSONResponse with server error
    """
    # Log full exception for debugging
    logger.error(
        f"Unhandled Exception: {type(exc).__name__}: {str(exc)} "
        f"(Path: {request.url.path})",
        exc_info=True
    )

    error_response = {
        "error": {
            "code": ErrorCode.SERVER_INTERNAL_ERROR.value,
            "message": "An unexpected error occurred. Please try again later.",
            "details": {
                "error_type": type(exc).__name__
            } if logger.level == logging.DEBUG else {},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )


def map_status_to_error_code(status_code: int, detail: str) -> str:
    """
    Map HTTP status code to appropriate error code.

    Args:
        status_code: HTTP status code
        detail: Error detail message

    Returns:
        Error code string
    """
    detail_lower = detail.lower()

    # Authentication errors (401)
    if status_code == 401:
        if "token" in detail_lower and "expired" in detail_lower:
            return ErrorCode.AUTH_TOKEN_EXPIRED.value
        elif "token" in detail_lower and "invalid" in detail_lower:
            return ErrorCode.AUTH_TOKEN_INVALID.value
        elif "credentials" in detail_lower or "password" in detail_lower:
            return ErrorCode.AUTH_INVALID_CREDENTIALS.value
        elif "session" in detail_lower:
            return ErrorCode.AUTH_SESSION_EXPIRED.value
        else:
            return ErrorCode.AUTH_TOKEN_MISSING.value

    # Forbidden errors (403)
    elif status_code == 403:
        if "inactive" in detail_lower:
            return ErrorCode.AUTH_USER_INACTIVE.value
        elif "suspended" in detail_lower:
            return ErrorCode.AUTH_USER_SUSPENDED.value
        else:
            return ErrorCode.RESOURCE_FORBIDDEN.value

    # Not found errors (404)
    elif status_code == 404:
        if "user" in detail_lower:
            return ErrorCode.AUTH_USER_NOT_FOUND.value
        else:
            return ErrorCode.RESOURCE_NOT_FOUND.value

    # Validation errors (400)
    elif status_code == 400:
        if "email" in detail_lower and "exists" in detail_lower:
            return ErrorCode.AUTH_EMAIL_EXISTS.value
        elif "password" in detail_lower:
            return ErrorCode.AUTH_WEAK_PASSWORD.value
        elif "validation" in detail_lower or "invalid" in detail_lower:
            return ErrorCode.VALIDATION_INVALID_INPUT.value
        else:
            return ErrorCode.VALIDATION_INVALID_INPUT.value

    # Rate limiting (429)
    elif status_code == 429:
        if "quota" in detail_lower:
            return ErrorCode.RATE_LIMIT_QUOTA_EXCEEDED.value
        else:
            return ErrorCode.RATE_LIMIT_EXCEEDED.value

    # Server errors (500+)
    elif status_code >= 500:
        if "database" in detail_lower:
            return ErrorCode.SERVER_DATABASE_ERROR.value
        elif "timeout" in detail_lower:
            return ErrorCode.SERVER_TIMEOUT.value
        elif status_code == 503:
            return ErrorCode.SERVER_SERVICE_UNAVAILABLE.value
        else:
            return ErrorCode.SERVER_INTERNAL_ERROR.value

    # Default fallback
    return ErrorCode.SERVER_INTERNAL_ERROR.value


def register_exception_handlers(app):
    """
    Register all custom exception handlers with FastAPI app.

    Call this function from main.py to enable standardized error handling.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Registered standardized exception handlers for mobile API")
