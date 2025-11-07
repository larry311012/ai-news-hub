"""
AI API Error Handler

Provides detailed error parsing and structured error responses for AI API failures.
Supports OpenAI and Anthropic errors with actionable user guidance.
"""

from typing import Dict, Optional, Any
import logging
import re

logger = logging.getLogger(__name__)


class AIErrorType:
    """Error type constants for AI API errors"""
    QUOTA_EXCEEDED = "quota_exceeded"
    INVALID_API_KEY = "invalid_api_key"
    RATE_LIMIT = "rate_limit_exceeded"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"
    CONTEXT_LENGTH = "context_length_exceeded"
    CONTENT_FILTER = "content_filter"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown_error"


def parse_ai_error(exception: Exception, provider: str = "openai") -> Dict[str, Any]:
    """
    Parse AI API exception into structured error information.

    Args:
        exception: The exception from OpenAI or Anthropic API
        provider: The AI provider ("openai" or "anthropic")

    Returns:
        Dictionary with structured error information:
        {
            "type": str,           # Error type constant
            "message": str,        # User-friendly message
            "provider": str,       # AI provider
            "action": str,         # Recommended action
            "documentation": str,  # Link to relevant docs
            "technical_detail": str,  # Technical error for debugging
            "retry_after": int,    # Seconds to wait before retry (if applicable)
        }
    """
    error_str = str(exception)
    error_type = AIErrorType.UNKNOWN
    user_message = "An error occurred while generating content"
    action = "Please try again later"
    documentation = ""
    retry_after = None
    technical_detail = error_str

    # Detect error type from exception
    if provider == "openai":
        error_type, user_message, action, documentation, retry_after = _parse_openai_error(
            exception, error_str
        )
    elif provider == "anthropic":
        error_type, user_message, action, documentation, retry_after = _parse_anthropic_error(
            exception, error_str
        )

    return {
        "type": error_type,
        "message": user_message,
        "provider": provider,
        "action": action,
        "documentation": documentation,
        "technical_detail": technical_detail[:500],  # Limit length
        "retry_after": retry_after,
    }


def _parse_openai_error(exception: Exception, error_str: str) -> tuple:
    """Parse OpenAI-specific errors"""
    error_type = AIErrorType.UNKNOWN
    user_message = "An error occurred while generating content"
    action = "Please try again later"
    documentation = "https://platform.openai.com/docs/guides/error-codes"
    retry_after = None

    # Check exception type
    exception_type = type(exception).__name__

    # 429 - Quota exceeded
    if "429" in error_str or "quota" in error_str.lower():
        error_type = AIErrorType.QUOTA_EXCEEDED
        user_message = "You've exceeded your OpenAI API quota"
        action = "Add billing information or upgrade your plan at https://platform.openai.com/account/billing"
        documentation = "https://platform.openai.com/docs/guides/rate-limits"

    # 401 - Invalid API key
    elif "401" in error_str or "unauthorized" in error_str.lower() or "invalid api key" in error_str.lower():
        error_type = AIErrorType.INVALID_API_KEY
        user_message = "Your OpenAI API key is invalid or expired"
        action = "Update your API key in Profile settings. Get a new key at https://platform.openai.com/api-keys"
        documentation = "https://platform.openai.com/docs/guides/authentication"

    # 429 - Rate limit
    elif "rate" in error_str.lower() and "limit" in error_str.lower():
        error_type = AIErrorType.RATE_LIMIT
        user_message = "Too many requests to OpenAI API"
        action = "Wait a moment before trying again. Consider upgrading your plan for higher limits."
        documentation = "https://platform.openai.com/docs/guides/rate-limits"
        retry_after = 60  # Suggest 60 second wait

    # 500/502/503 - Server errors
    elif any(code in error_str for code in ["500", "502", "503", "504"]):
        error_type = AIErrorType.SERVER_ERROR
        user_message = "OpenAI API is temporarily unavailable"
        action = "The service is experiencing issues. Please try again in a few minutes."
        documentation = "https://status.openai.com/"
        retry_after = 30

    # Timeout
    elif "timeout" in error_str.lower() or exception_type == "Timeout":
        error_type = AIErrorType.TIMEOUT
        user_message = "Request to OpenAI API timed out"
        action = "The request took too long. Please try again."
        retry_after = 10

    # Context length exceeded
    elif "context_length" in error_str.lower() or "maximum context" in error_str.lower():
        error_type = AIErrorType.CONTEXT_LENGTH
        user_message = "Content is too long for OpenAI to process"
        action = "Try selecting fewer articles or shorter content"
        documentation = "https://platform.openai.com/docs/guides/chat/managing-tokens"

    # Content filter
    elif "content_filter" in error_str.lower() or "content policy" in error_str.lower():
        error_type = AIErrorType.CONTENT_FILTER
        user_message = "Content violates OpenAI's usage policies"
        action = "Please select different articles that comply with OpenAI's content policy"
        documentation = "https://platform.openai.com/docs/guides/moderation"

    # Network/connection errors
    elif any(keyword in error_str.lower() for keyword in ["connection", "network", "dns", "unreachable"]):
        error_type = AIErrorType.NETWORK_ERROR
        user_message = "Unable to connect to OpenAI API"
        action = "Check your internet connection and try again"
        retry_after = 10

    # Invalid request
    elif "400" in error_str or "invalid" in error_str.lower():
        error_type = AIErrorType.INVALID_REQUEST
        user_message = "Invalid request to OpenAI API"
        action = "There was a problem with the request. Please try again or contact support."

    return error_type, user_message, action, documentation, retry_after


def _parse_anthropic_error(exception: Exception, error_str: str) -> tuple:
    """Parse Anthropic-specific errors"""
    error_type = AIErrorType.UNKNOWN
    user_message = "An error occurred while generating content"
    action = "Please try again later"
    documentation = "https://docs.anthropic.com/en/api/errors"
    retry_after = None

    # Check exception type
    exception_type = type(exception).__name__

    # 429 - Quota exceeded
    if "429" in error_str or "quota" in error_str.lower() or "credit" in error_str.lower():
        error_type = AIErrorType.QUOTA_EXCEEDED
        user_message = "You've exceeded your Anthropic API quota"
        action = "Add credits or upgrade your plan at https://console.anthropic.com/settings/plans"
        documentation = "https://docs.anthropic.com/en/api/rate-limits"

    # 401 - Invalid API key
    elif "401" in error_str or "unauthorized" in error_str.lower() or "invalid api key" in error_str.lower():
        error_type = AIErrorType.INVALID_API_KEY
        user_message = "Your Anthropic API key is invalid or expired"
        action = "Update your API key in Profile settings. Get a new key at https://console.anthropic.com/settings/keys"
        documentation = "https://docs.anthropic.com/en/api/getting-started"

    # 429 - Rate limit
    elif "rate" in error_str.lower() and "limit" in error_str.lower():
        error_type = AIErrorType.RATE_LIMIT
        user_message = "Too many requests to Anthropic API"
        action = "Wait a moment before trying again. Consider upgrading for higher limits."
        documentation = "https://docs.anthropic.com/en/api/rate-limits"
        retry_after = 60

    # 500/502/503 - Server errors
    elif any(code in error_str for code in ["500", "502", "503", "504"]):
        error_type = AIErrorType.SERVER_ERROR
        user_message = "Anthropic API is temporarily unavailable"
        action = "The service is experiencing issues. Please try again in a few minutes."
        documentation = "https://status.anthropic.com/"
        retry_after = 30

    # Timeout
    elif "timeout" in error_str.lower() or exception_type == "Timeout":
        error_type = AIErrorType.TIMEOUT
        user_message = "Request to Anthropic API timed out"
        action = "The request took too long. Please try again."
        retry_after = 10

    # Context length exceeded
    elif "context" in error_str.lower() or "token" in error_str.lower():
        error_type = AIErrorType.CONTEXT_LENGTH
        user_message = "Content is too long for Claude to process"
        action = "Try selecting fewer articles or shorter content"
        documentation = "https://docs.anthropic.com/en/api/messages"

    # Network/connection errors
    elif any(keyword in error_str.lower() for keyword in ["connection", "network", "dns", "unreachable"]):
        error_type = AIErrorType.NETWORK_ERROR
        user_message = "Unable to connect to Anthropic API"
        action = "Check your internet connection and try again"
        retry_after = 10

    # Invalid request
    elif "400" in error_str or "invalid" in error_str.lower():
        error_type = AIErrorType.INVALID_REQUEST
        user_message = "Invalid request to Anthropic API"
        action = "There was a problem with the request. Please try again or contact support."

    return error_type, user_message, action, documentation, retry_after


def format_error_for_user(error_details: Dict[str, Any]) -> str:
    """
    Format structured error details into a user-friendly message.

    Args:
        error_details: Structured error dict from parse_ai_error()

    Returns:
        Formatted error message for display
    """
    message = error_details.get("message", "An error occurred")
    action = error_details.get("action", "Please try again")

    return f"{message}. {action}"


def should_retry_error(error_details: Dict[str, Any]) -> bool:
    """
    Determine if an error is retryable.

    Args:
        error_details: Structured error dict from parse_ai_error()

    Returns:
        True if error is retryable (temporary issue)
    """
    retryable_types = [
        AIErrorType.RATE_LIMIT,
        AIErrorType.SERVER_ERROR,
        AIErrorType.TIMEOUT,
        AIErrorType.NETWORK_ERROR,
    ]

    return error_details.get("type") in retryable_types


def get_retry_delay(error_details: Dict[str, Any]) -> Optional[int]:
    """
    Get recommended retry delay in seconds.

    Args:
        error_details: Structured error dict from parse_ai_error()

    Returns:
        Delay in seconds, or None if not retryable
    """
    if not should_retry_error(error_details):
        return None

    return error_details.get("retry_after", 10)
