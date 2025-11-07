"""
Custom exceptions for AI provider errors with user-friendly messages
"""
from typing import Optional, Dict, Any
from enum import Enum


class ErrorType(str, Enum):
    """Enumeration of AI provider error types"""

    # Authentication errors
    INVALID_API_KEY = "invalid_api_key"
    AUTHENTICATION_FAILED = "authentication_failed"

    # Quota and billing errors
    QUOTA_EXCEEDED = "quota_exceeded"
    INSUFFICIENT_QUOTA = "insufficient_quota"

    # Rate limiting errors
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    TOO_MANY_REQUESTS = "too_many_requests"

    # Service availability errors
    SERVICE_UNAVAILABLE = "service_unavailable"
    SERVICE_ERROR = "service_error"
    TIMEOUT = "timeout"

    # Request errors
    INVALID_REQUEST = "invalid_request"
    CONTENT_FILTER = "content_filter"
    CONTEXT_LENGTH_EXCEEDED = "context_length_exceeded"

    # Network errors
    CONNECTION_ERROR = "connection_error"
    NETWORK_TIMEOUT = "network_timeout"

    # Unknown errors
    UNKNOWN_ERROR = "unknown_error"


class AIProviderError(Exception):
    """
    Base exception class for AI provider errors with structured information

    Attributes:
        provider: AI provider name ("openai", "anthropic")
        error_type: Type of error from ErrorType enum
        message: User-friendly error message
        original_error: Original exception that was raised
        code: HTTP status code (if applicable)
        action: Suggested user action
        help_url: URL for more information
        context: Additional context for debugging
    """

    def __init__(
        self,
        provider: str,
        error_type: ErrorType,
        message: str,
        original_error: Optional[Exception] = None,
        code: Optional[int] = None,
        action: Optional[str] = None,
        help_url: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.provider = provider
        self.error_type = error_type
        self.message = message
        self.original_error = original_error
        self.code = code
        self.action = action
        self.help_url = help_url
        self.context = context or {}

        super().__init__(self.get_full_message())

    def get_full_message(self) -> str:
        """Get complete error message with action and help URL"""
        parts = [self.message]

        if self.action:
            parts.append(f"\n\nAction: {self.action}")

        if self.help_url:
            parts.append(f"\nHelp: {self.help_url}")

        return "".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses"""
        return {
            "provider": self.provider,
            "error_type": self.error_type.value,
            "message": self.message,
            "code": self.code,
            "action": self.action,
            "help_url": self.help_url,
            "context": self.context,
        }

    def is_retryable(self) -> bool:
        """Check if this error type should be retried"""
        retryable_types = {
            ErrorType.RATE_LIMIT_EXCEEDED,
            ErrorType.TOO_MANY_REQUESTS,
            ErrorType.SERVICE_UNAVAILABLE,
            ErrorType.SERVICE_ERROR,
            ErrorType.TIMEOUT,
            ErrorType.CONNECTION_ERROR,
            ErrorType.NETWORK_TIMEOUT,
        }
        return self.error_type in retryable_types


# Specific exception classes for different error categories


class AuthenticationError(AIProviderError):
    """Authentication-related errors (invalid API key, etc.)"""

    pass


class QuotaError(AIProviderError):
    """Quota and billing-related errors"""

    pass


class RateLimitError(AIProviderError):
    """Rate limiting errors (429 errors)"""

    pass


class ServiceError(AIProviderError):
    """Service availability errors (500, 503)"""

    pass


class RequestError(AIProviderError):
    """Invalid request errors (400, content filter, etc.)"""

    pass


class NetworkError(AIProviderError):
    """Network and connection errors"""

    pass


# Error message templates with placeholders

ERROR_MESSAGES = {
    # OpenAI error messages
    "openai": {
        ErrorType.INVALID_API_KEY: {
            "message": "Invalid OpenAI API key. Your API key is either incorrect or has been revoked.",
            "action": "Update your OpenAI API key in Profile > Settings > AI Provider.",
            "help_url": "https://platform.openai.com/account/api-keys",
        },
        ErrorType.QUOTA_EXCEEDED: {
            "message": "OpenAI quota exceeded. You've reached your usage limit or billing quota.",
            "action": "Add billing information or upgrade your plan at OpenAI's billing dashboard.",
            "help_url": "https://platform.openai.com/account/billing",
        },
        ErrorType.INSUFFICIENT_QUOTA: {
            "message": "Insufficient OpenAI quota. Your account doesn't have enough credits.",
            "action": "Add payment method or purchase more credits at OpenAI's billing dashboard.",
            "help_url": "https://platform.openai.com/account/billing",
        },
        ErrorType.RATE_LIMIT_EXCEEDED: {
            "message": "Too many requests to OpenAI. You're sending requests too quickly.",
            "action": "Wait a moment and try again. Consider upgrading your plan for higher rate limits.",
            "help_url": "https://platform.openai.com/account/rate-limits",
        },
        ErrorType.SERVICE_UNAVAILABLE: {
            "message": "OpenAI service is temporarily unavailable. The API is experiencing issues.",
            "action": "Try again in a few minutes. Check OpenAI's status page for updates.",
            "help_url": "https://status.openai.com",
        },
        ErrorType.TIMEOUT: {
            "message": "Request to OpenAI timed out. The request took too long to complete.",
            "action": "Check your internet connection and try again. If the problem persists, try a shorter request.",
            "help_url": "https://platform.openai.com/docs/guides/rate-limits",
        },
        ErrorType.CONTENT_FILTER: {
            "message": "Content was flagged by OpenAI's safety system.",
            "action": "Review your content and ensure it complies with OpenAI's usage policies.",
            "help_url": "https://platform.openai.com/docs/guides/moderation",
        },
        ErrorType.CONTEXT_LENGTH_EXCEEDED: {
            "message": "Content is too long for OpenAI's model. The input exceeds the maximum token limit.",
            "action": "Reduce the length of your input or use a model with a larger context window.",
            "help_url": "https://platform.openai.com/docs/guides/rate-limits",
        },
    },
    # Anthropic error messages
    "anthropic": {
        ErrorType.INVALID_API_KEY: {
            "message": "Invalid Anthropic API key. Your API key is either incorrect or has been revoked.",
            "action": "Update your Anthropic API key in Profile > Settings > AI Provider.",
            "help_url": "https://console.anthropic.com/account/keys",
        },
        ErrorType.QUOTA_EXCEEDED: {
            "message": "Anthropic quota exceeded. You've reached your usage limit.",
            "action": "Upgrade your plan or wait for your quota to reset at Anthropic's console.",
            "help_url": "https://console.anthropic.com/account/billing",
        },
        ErrorType.RATE_LIMIT_EXCEEDED: {
            "message": "Too many requests to Anthropic. You're sending requests too quickly.",
            "action": "Wait a moment and try again. Consider upgrading for higher rate limits.",
            "help_url": "https://console.anthropic.com/account/limits",
        },
        ErrorType.SERVICE_UNAVAILABLE: {
            "message": "Anthropic service is temporarily unavailable. The API is experiencing issues.",
            "action": "Try again in a few minutes. Check Anthropic's status page for updates.",
            "help_url": "https://status.anthropic.com",
        },
        ErrorType.TIMEOUT: {
            "message": "Request to Anthropic timed out. The request took too long to complete.",
            "action": "Check your internet connection and try again.",
            "help_url": "https://docs.anthropic.com/claude/reference/errors",
        },
        ErrorType.CONTEXT_LENGTH_EXCEEDED: {
            "message": "Content is too long for Claude. The input exceeds the maximum token limit.",
            "action": "Reduce the length of your input or split into multiple requests.",
            "help_url": "https://docs.anthropic.com/claude/reference/input-and-output-sizes",
        },
    },
}


def get_error_info(provider: str, error_type: ErrorType) -> Dict[str, str]:
    """
    Get error message template for a specific provider and error type

    Args:
        provider: AI provider name
        error_type: Type of error

    Returns:
        Dictionary with message, action, and help_url
    """
    provider_messages = ERROR_MESSAGES.get(provider, {})
    return provider_messages.get(
        error_type,
        {
            "message": f"An error occurred with {provider}.",
            "action": "Please try again. If the problem persists, contact support.",
            "help_url": None,
        },
    )
