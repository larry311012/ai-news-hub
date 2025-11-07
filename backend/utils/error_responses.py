"""
Mobile API Error Response Standardization (Task 1.7)

Provides standardized error responses for mobile iOS app integration.
All errors follow a consistent format with error codes, messages, and timestamps.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Standardized error codes for mobile app"""

    # Authentication Errors (AUTH_*)
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_TOKEN_MISSING = "AUTH_TOKEN_MISSING"
    AUTH_SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"
    AUTH_USER_NOT_FOUND = "AUTH_USER_NOT_FOUND"
    AUTH_USER_INACTIVE = "AUTH_USER_INACTIVE"
    AUTH_USER_SUSPENDED = "AUTH_USER_SUSPENDED"
    AUTH_EMAIL_EXISTS = "AUTH_EMAIL_EXISTS"
    AUTH_WEAK_PASSWORD = "AUTH_WEAK_PASSWORD"
    AUTH_REFRESH_FAILED = "AUTH_REFRESH_FAILED"
    AUTH_DEVICE_NOT_REGISTERED = "AUTH_DEVICE_NOT_REGISTERED"
    AUTH_OAUTH_FAILED = "AUTH_OAUTH_FAILED"
    AUTH_OAUTH_CANCELLED = "AUTH_OAUTH_CANCELLED"

    # Validation Errors (VALIDATION_*)
    VALIDATION_INVALID_INPUT = "VALIDATION_INVALID_INPUT"
    VALIDATION_MISSING_FIELD = "VALIDATION_MISSING_FIELD"
    VALIDATION_INVALID_EMAIL = "VALIDATION_INVALID_EMAIL"
    VALIDATION_INVALID_FORMAT = "VALIDATION_INVALID_FORMAT"
    VALIDATION_FIELD_TOO_LONG = "VALIDATION_FIELD_TOO_LONG"
    VALIDATION_FIELD_TOO_SHORT = "VALIDATION_FIELD_TOO_SHORT"
    VALIDATION_INVALID_DATE = "VALIDATION_INVALID_DATE"
    VALIDATION_INVALID_URL = "VALIDATION_INVALID_URL"

    # Rate Limiting Errors (RATE_LIMIT_*)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    RATE_LIMIT_TOO_MANY_REQUESTS = "RATE_LIMIT_TOO_MANY_REQUESTS"
    RATE_LIMIT_QUOTA_EXCEEDED = "RATE_LIMIT_QUOTA_EXCEEDED"
    RATE_LIMIT_DEVICE_LIMIT = "RATE_LIMIT_DEVICE_LIMIT"
    RATE_LIMIT_API_LIMIT = "RATE_LIMIT_API_LIMIT"

    # Server Errors (SERVER_*)
    SERVER_INTERNAL_ERROR = "SERVER_INTERNAL_ERROR"
    SERVER_DATABASE_ERROR = "SERVER_DATABASE_ERROR"
    SERVER_NETWORK_ERROR = "SERVER_NETWORK_ERROR"
    SERVER_SERVICE_UNAVAILABLE = "SERVER_SERVICE_UNAVAILABLE"
    SERVER_TIMEOUT = "SERVER_TIMEOUT"
    SERVER_MAINTENANCE = "SERVER_MAINTENANCE"

    # Resource Errors (RESOURCE_*)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_DELETED = "RESOURCE_DELETED"
    RESOURCE_FORBIDDEN = "RESOURCE_FORBIDDEN"

    # API Key Errors (API_KEY_*)
    API_KEY_MISSING = "API_KEY_MISSING"
    API_KEY_INVALID = "API_KEY_INVALID"
    API_KEY_EXPIRED = "API_KEY_EXPIRED"
    API_KEY_QUOTA_EXCEEDED = "API_KEY_QUOTA_EXCEEDED"

    # Social Media Errors (SOCIAL_*)
    SOCIAL_CONNECTION_FAILED = "SOCIAL_CONNECTION_FAILED"
    SOCIAL_TOKEN_EXPIRED = "SOCIAL_TOKEN_EXPIRED"
    SOCIAL_PUBLISH_FAILED = "SOCIAL_PUBLISH_FAILED"
    SOCIAL_PLATFORM_ERROR = "SOCIAL_PLATFORM_ERROR"
    SOCIAL_NOT_CONNECTED = "SOCIAL_NOT_CONNECTED"

    # Content Errors (CONTENT_*)
    CONTENT_GENERATION_FAILED = "CONTENT_GENERATION_FAILED"
    CONTENT_TOO_LONG = "CONTENT_TOO_LONG"
    CONTENT_INVALID_FORMAT = "CONTENT_INVALID_FORMAT"
    CONTENT_MODERATION_FAILED = "CONTENT_MODERATION_FAILED"


class ErrorDetail(BaseModel):
    """Standard error detail structure"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = {}
    timestamp: str

    class Config:
        json_schema_extra = {
            "example": {
                "code": "AUTH_INVALID_CREDENTIALS",
                "message": "Invalid email or password",
                "details": {},
                "timestamp": "2025-11-04T10:30:00Z"
            }
        }


class StandardErrorResponse(BaseModel):
    """Standard error response wrapper"""
    error: ErrorDetail

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "AUTH_INVALID_CREDENTIALS",
                    "message": "Invalid email or password",
                    "details": {},
                    "timestamp": "2025-11-04T10:30:00Z"
                }
            }
        }


def create_error_response(
    code: ErrorCode,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """
    Create a standardized error response for mobile app.

    Args:
        code: Error code from ErrorCode enum
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional additional details

    Returns:
        JSONResponse with standardized error format
    """
    error_response = {
        "error": {
            "code": code.value if isinstance(code, ErrorCode) else code,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }

    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


def create_error_exception(
    code: ErrorCode,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """
    Create a standardized HTTPException for mobile app.

    Args:
        code: Error code from ErrorCode enum
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional additional details

    Returns:
        HTTPException with standardized error format
    """
    error_detail = {
        "code": code.value if isinstance(code, ErrorCode) else code,
        "message": message,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    return HTTPException(
        status_code=status_code,
        detail={"error": error_detail}
    )


# Error code documentation mapping
ERROR_CODE_DOCS = {
    # Authentication Errors
    "AUTH_INVALID_CREDENTIALS": {
        "status_code": 401,
        "description": "Invalid email or password provided during login",
        "user_action": "Check credentials and try again"
    },
    "AUTH_TOKEN_EXPIRED": {
        "status_code": 401,
        "description": "Access token has expired and needs refresh",
        "user_action": "Request token refresh using refresh token"
    },
    "AUTH_TOKEN_INVALID": {
        "status_code": 401,
        "description": "Token is malformed or invalid",
        "user_action": "Re-authenticate to get new token"
    },
    "AUTH_TOKEN_MISSING": {
        "status_code": 401,
        "description": "Authorization token not provided in request",
        "user_action": "Include valid token in Authorization header"
    },
    "AUTH_SESSION_EXPIRED": {
        "status_code": 401,
        "description": "Session has expired due to inactivity",
        "user_action": "Log in again"
    },
    "AUTH_USER_NOT_FOUND": {
        "status_code": 404,
        "description": "User account does not exist",
        "user_action": "Verify email or create new account"
    },
    "AUTH_USER_INACTIVE": {
        "status_code": 403,
        "description": "User account is inactive or deactivated",
        "user_action": "Contact support to reactivate account"
    },
    "AUTH_EMAIL_EXISTS": {
        "status_code": 400,
        "description": "Email address already registered",
        "user_action": "Use different email or log in with existing account"
    },
    "AUTH_REFRESH_FAILED": {
        "status_code": 401,
        "description": "Failed to refresh access token",
        "user_action": "Re-authenticate with credentials"
    },

    # Validation Errors
    "VALIDATION_INVALID_INPUT": {
        "status_code": 400,
        "description": "Input data validation failed",
        "user_action": "Check input format and try again"
    },
    "VALIDATION_MISSING_FIELD": {
        "status_code": 400,
        "description": "Required field is missing",
        "user_action": "Provide all required fields"
    },
    "VALIDATION_INVALID_EMAIL": {
        "status_code": 400,
        "description": "Email format is invalid",
        "user_action": "Enter valid email address"
    },

    # Rate Limiting Errors
    "RATE_LIMIT_EXCEEDED": {
        "status_code": 429,
        "description": "Too many requests in short time period",
        "user_action": "Wait before retrying (see retry_after field)"
    },
    "RATE_LIMIT_QUOTA_EXCEEDED": {
        "status_code": 429,
        "description": "Daily/monthly quota exceeded",
        "user_action": "Wait for quota reset or upgrade plan"
    },
    "RATE_LIMIT_DEVICE_LIMIT": {
        "status_code": 429,
        "description": "Too many requests from this device",
        "user_action": "Wait before retrying"
    },

    # Server Errors
    "SERVER_INTERNAL_ERROR": {
        "status_code": 500,
        "description": "Internal server error occurred",
        "user_action": "Try again later or contact support"
    },
    "SERVER_DATABASE_ERROR": {
        "status_code": 500,
        "description": "Database operation failed",
        "user_action": "Try again later"
    },
    "SERVER_SERVICE_UNAVAILABLE": {
        "status_code": 503,
        "description": "Service temporarily unavailable",
        "user_action": "Try again in a few minutes"
    },
    "SERVER_TIMEOUT": {
        "status_code": 504,
        "description": "Request timed out",
        "user_action": "Check connection and retry"
    },

    # Resource Errors
    "RESOURCE_NOT_FOUND": {
        "status_code": 404,
        "description": "Requested resource does not exist",
        "user_action": "Verify resource ID and try again"
    },
    "RESOURCE_FORBIDDEN": {
        "status_code": 403,
        "description": "Access to resource is forbidden",
        "user_action": "Ensure you have proper permissions"
    },

    # Social Media Errors
    "SOCIAL_CONNECTION_FAILED": {
        "status_code": 500,
        "description": "Failed to connect to social media platform",
        "user_action": "Try reconnecting your account"
    },
    "SOCIAL_TOKEN_EXPIRED": {
        "status_code": 401,
        "description": "Social media access token expired",
        "user_action": "Reconnect your social media account"
    },
    "SOCIAL_PUBLISH_FAILED": {
        "status_code": 500,
        "description": "Failed to publish content to platform",
        "user_action": "Check platform status and retry"
    },
    "SOCIAL_NOT_CONNECTED": {
        "status_code": 400,
        "description": "Social media account not connected",
        "user_action": "Connect your social media account first"
    },
}


def get_error_documentation(code: str) -> Dict[str, Any]:
    """
    Get documentation for an error code.

    Args:
        code: Error code string

    Returns:
        Dictionary with error documentation
    """
    return ERROR_CODE_DOCS.get(code, {
        "status_code": 500,
        "description": "Unknown error",
        "user_action": "Contact support"
    })
