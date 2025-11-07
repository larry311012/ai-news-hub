"""
AI provider error handler that maps provider-specific errors to our custom exceptions
"""
from typing import Optional, Dict, Any
from loguru import logger
import time

from src.utils.ai_exceptions import (
    AIProviderError,
    AuthenticationError,
    QuotaError,
    RateLimitError,
    ServiceError,
    RequestError,
    NetworkError,
    ErrorType,
    get_error_info,
)


class AIErrorHandler:
    """
    Handles and maps AI provider errors to user-friendly exceptions
    """

    @staticmethod
    def handle_openai_error(
        error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> AIProviderError:
        """
        Map OpenAI errors to custom exceptions

        Args:
            error: Original OpenAI exception
            context: Additional context (user_id, post_id, etc.)

        Returns:
            AIProviderError subclass with user-friendly message
        """
        from openai import (
            APIError,
            APIConnectionError,
            RateLimitError as OpenAIRateLimitError,
            AuthenticationError as OpenAIAuthenticationError,
        )

        context = context or {}
        provider = "openai"

        # Log the original error for debugging
        error_str = str(error).replace("{", "{{").replace("}", "}}")
        logger.error(
            f"OpenAI error: {type(error).__name__}: {error_str}", extra={"context": context}
        )

        # Check error type and status code
        error_message = str(error).lower()
        status_code = getattr(error, "status_code", None)

        # Authentication errors (401)
        if isinstance(error, OpenAIAuthenticationError) or status_code == 401:
            if "invalid" in error_message or "incorrect" in error_message:
                error_type = ErrorType.INVALID_API_KEY
                error_info = get_error_info(provider, error_type)
                return AuthenticationError(
                    provider=provider,
                    error_type=error_type,
                    message=error_info["message"],
                    original_error=error,
                    code=401,
                    action=error_info["action"],
                    help_url=error_info["help_url"],
                    context=context,
                )

        # Rate limit and quota errors (429)
        if isinstance(error, OpenAIRateLimitError) or status_code == 429:
            # Check if it's a quota issue vs rate limit
            if any(
                keyword in error_message
                for keyword in ["quota", "insufficient_quota", "billing", "credit"]
            ):
                error_type = ErrorType.QUOTA_EXCEEDED
                error_info = get_error_info(provider, error_type)
                return QuotaError(
                    provider=provider,
                    error_type=error_type,
                    message=error_info["message"],
                    original_error=error,
                    code=429,
                    action=error_info["action"],
                    help_url=error_info["help_url"],
                    context=context,
                )
            else:
                # Regular rate limit
                error_type = ErrorType.RATE_LIMIT_EXCEEDED
                error_info = get_error_info(provider, error_type)
                return RateLimitError(
                    provider=provider,
                    error_type=error_type,
                    message=error_info["message"],
                    original_error=error,
                    code=429,
                    action=error_info["action"],
                    help_url=error_info["help_url"],
                    context=context,
                )

        # Service errors (500, 503)
        if status_code in [500, 502, 503, 504]:
            error_type = ErrorType.SERVICE_UNAVAILABLE
            error_info = get_error_info(provider, error_type)
            return ServiceError(
                provider=provider,
                error_type=error_type,
                message=error_info["message"],
                original_error=error,
                code=status_code,
                action=error_info["action"],
                help_url=error_info["help_url"],
                context=context,
            )

        # Connection errors
        if isinstance(error, APIConnectionError) or "connection" in error_message:
            if "timeout" in error_message or "timed out" in error_message:
                error_type = ErrorType.TIMEOUT
            else:
                error_type = ErrorType.CONNECTION_ERROR

            error_info = get_error_info(provider, error_type)
            return NetworkError(
                provider=provider,
                error_type=error_type,
                message=error_info["message"],
                original_error=error,
                code=None,
                action=error_info["action"],
                help_url=error_info["help_url"],
                context=context,
            )

        # Content filter / moderation errors
        if "content_filter" in error_message or "content_policy" in error_message:
            error_type = ErrorType.CONTENT_FILTER
            error_info = get_error_info(provider, error_type)
            return RequestError(
                provider=provider,
                error_type=error_type,
                message=error_info["message"],
                original_error=error,
                code=400,
                action=error_info["action"],
                help_url=error_info["help_url"],
                context=context,
            )

        # Context length errors
        if any(
            keyword in error_message
            for keyword in ["context_length", "maximum context", "token limit"]
        ):
            error_type = ErrorType.CONTEXT_LENGTH_EXCEEDED
            error_info = get_error_info(provider, error_type)
            return RequestError(
                provider=provider,
                error_type=error_type,
                message=error_info["message"],
                original_error=error,
                code=400,
                action=error_info["action"],
                help_url=error_info["help_url"],
                context=context,
            )

        # Generic API error
        if isinstance(error, APIError):
            error_type = ErrorType.SERVICE_ERROR
            error_info = get_error_info(provider, error_type)
            return ServiceError(
                provider=provider,
                error_type=error_type,
                message=error_info["message"],
                original_error=error,
                code=status_code,
                action=error_info["action"],
                help_url=error_info["help_url"],
                context=context,
            )

        # Unknown error
        error_type = ErrorType.UNKNOWN_ERROR
        return AIProviderError(
            provider=provider,
            error_type=error_type,
            message=f"An unexpected error occurred with OpenAI: {str(error)}",
            original_error=error,
            code=status_code,
            action="Please try again. If the problem persists, contact support.",
            help_url="https://platform.openai.com/docs/guides/error-codes",
            context=context,
        )

    @staticmethod
    def handle_anthropic_error(
        error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> AIProviderError:
        """
        Map Anthropic errors to custom exceptions

        Args:
            error: Original Anthropic exception
            context: Additional context (user_id, post_id, etc.)

        Returns:
            AIProviderError subclass with user-friendly message
        """
        from anthropic import (
            APIError,
            APIConnectionError,
            RateLimitError as AnthropicRateLimitError,
            AuthenticationError as AnthropicAuthenticationError,
        )

        context = context or {}
        provider = "anthropic"

        # Log the original error for debugging
        error_str = str(error).replace("{", "{{").replace("}", "}}")
        logger.error(
            f"Anthropic error: {type(error).__name__}: {error_str}", extra={"context": context}
        )

        # Check error type and status code
        error_message = str(error).lower()
        status_code = getattr(error, "status_code", None)

        # Authentication errors (401)
        if isinstance(error, AnthropicAuthenticationError) or status_code == 401:
            error_type = ErrorType.INVALID_API_KEY
            error_info = get_error_info(provider, error_type)
            return AuthenticationError(
                provider=provider,
                error_type=error_type,
                message=error_info["message"],
                original_error=error,
                code=401,
                action=error_info["action"],
                help_url=error_info["help_url"],
                context=context,
            )

        # Rate limit and quota errors (429)
        if isinstance(error, AnthropicRateLimitError) or status_code == 429:
            # Check if it's a quota issue
            if any(keyword in error_message for keyword in ["quota", "usage limit", "credit"]):
                error_type = ErrorType.QUOTA_EXCEEDED
                error_info = get_error_info(provider, error_type)
                return QuotaError(
                    provider=provider,
                    error_type=error_type,
                    message=error_info["message"],
                    original_error=error,
                    code=429,
                    action=error_info["action"],
                    help_url=error_info["help_url"],
                    context=context,
                )
            else:
                # Regular rate limit
                error_type = ErrorType.RATE_LIMIT_EXCEEDED
                error_info = get_error_info(provider, error_type)
                return RateLimitError(
                    provider=provider,
                    error_type=error_type,
                    message=error_info["message"],
                    original_error=error,
                    code=429,
                    action=error_info["action"],
                    help_url=error_info["help_url"],
                    context=context,
                )

        # Service errors (500, 503)
        if status_code in [500, 502, 503, 504]:
            error_type = ErrorType.SERVICE_UNAVAILABLE
            error_info = get_error_info(provider, error_type)
            return ServiceError(
                provider=provider,
                error_type=error_type,
                message=error_info["message"],
                original_error=error,
                code=status_code,
                action=error_info["action"],
                help_url=error_info["help_url"],
                context=context,
            )

        # Connection errors
        if isinstance(error, APIConnectionError) or "connection" in error_message:
            if "timeout" in error_message or "timed out" in error_message:
                error_type = ErrorType.TIMEOUT
            else:
                error_type = ErrorType.CONNECTION_ERROR

            error_info = get_error_info(provider, error_type)
            return NetworkError(
                provider=provider,
                error_type=error_type,
                message=error_info["message"],
                original_error=error,
                code=None,
                action=error_info["action"],
                help_url=error_info["help_url"],
                context=context,
            )

        # Context length errors
        if any(
            keyword in error_message
            for keyword in ["context_length", "maximum context", "token limit", "too long"]
        ):
            error_type = ErrorType.CONTEXT_LENGTH_EXCEEDED
            error_info = get_error_info(provider, error_type)
            return RequestError(
                provider=provider,
                error_type=error_type,
                message=error_info["message"],
                original_error=error,
                code=400,
                action=error_info["action"],
                help_url=error_info["help_url"],
                context=context,
            )

        # Generic API error
        if isinstance(error, APIError):
            error_type = ErrorType.SERVICE_ERROR
            error_info = get_error_info(provider, error_type)
            return ServiceError(
                provider=provider,
                error_type=error_type,
                message=error_info["message"],
                original_error=error,
                code=status_code,
                action=error_info["action"],
                help_url=error_info["help_url"],
                context=context,
            )

        # Unknown error
        error_type = ErrorType.UNKNOWN_ERROR
        return AIProviderError(
            provider=provider,
            error_type=error_type,
            message=f"An unexpected error occurred with Anthropic: {str(error)}",
            original_error=error,
            code=status_code,
            action="Please try again. If the problem persists, contact support.",
            help_url="https://docs.anthropic.com/claude/reference/errors",
            context=context,
        )

    @staticmethod
    def handle_generic_error(
        error: Exception, provider: str, context: Optional[Dict[str, Any]] = None
    ) -> AIProviderError:
        """
        Handle generic/unknown errors

        Args:
            error: Original exception
            provider: AI provider name
            context: Additional context

        Returns:
            AIProviderError with generic message
        """
        context = context or {}

        logger.error(f"Generic {provider} error: {type(error).__name__}: {str(error)}", extra={"context": context})

        error_type = ErrorType.UNKNOWN_ERROR
        return AIProviderError(
            provider=provider,
            error_type=error_type,
            message=f"An unexpected error occurred with {provider}: {str(error)}",
            original_error=error,
            code=None,
            action="Please try again. If the problem persists, contact support.",
            help_url=None,
            context=context,
        )

    @staticmethod
    def should_retry(error: AIProviderError, attempt: int, max_retries: int) -> bool:
        """
        Determine if an error should be retried

        Args:
            error: The AIProviderError
            attempt: Current attempt number (0-indexed)
            max_retries: Maximum number of retries

        Returns:
            True if should retry, False otherwise
        """
        # Don't retry if we've exceeded max attempts
        if attempt >= max_retries:
            return False

        # Check if error type is retryable
        return error.is_retryable()

    @staticmethod
    def get_retry_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
        """
        Calculate exponential backoff delay

        Args:
            attempt: Current attempt number (0-indexed)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds

        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * 2^attempt
        delay = min(base_delay * (2**attempt), max_delay)
        return delay

    @staticmethod
    def log_error(
        error: AIProviderError, user_id: Optional[int] = None, additional_context: Optional[Dict] = None
    ):
        """
        Log error with full context for debugging

        Args:
            error: The AIProviderError
            user_id: User ID if available
            additional_context: Additional context to log
        """
        log_context = {
            "provider": error.provider,
            "error_type": error.error_type.value,
            "code": error.code,
            "user_id": user_id,
            **error.context,
            **(additional_context or {}),
        }

        logger.error(
            f"AI Provider Error: {error.message}",
            extra={
                "context": log_context,
                "original_error": str(error.original_error) if error.original_error else None,
            },
        )
