"""
DeepSeek AI Provider Client

DeepSeek API client implementation following OpenAI-compatible interface.
API Documentation: https://api-docs.deepseek.com/
"""
import os
import logging
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """
    DeepSeek API client with OpenAI-compatible interface.

    DeepSeek uses OpenAI-compatible API format, allowing seamless integration.
    Base URL: https://api.deepseek.com/v1
    """

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        """
        Initialize DeepSeek client

        Args:
            api_key: DeepSeek API key
            base_url: API base URL (defaults to official endpoint)
        """
        if not api_key or not api_key.strip():
            raise ValueError("DeepSeek API key cannot be empty")

        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip('/')
        self.session = self._create_session()

        logger.info("DeepSeek client initialized successfully")

    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry logic

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # Configure retry strategy for transient errors
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def chat_completion(
        self,
        messages: list[Dict[str, str]],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        timeout: float = 30.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create chat completion (OpenAI-compatible)

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (deepseek-chat, deepseek-coder)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            **kwargs: Additional parameters

        Returns:
            Response dict with 'choices' containing generated text

        Raises:
            DeepSeekError: If API call fails
        """
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout
            )

            # Log rate limit headers for monitoring
            if "x-ratelimit-remaining-tokens" in response.headers:
                logger.debug(
                    f"DeepSeek rate limit - Remaining tokens: {response.headers['x-ratelimit-remaining-tokens']}"
                )

            response.raise_for_status()

            result = response.json()
            logger.debug(f"DeepSeek API call successful - Model: {model}")

            return result

        except requests.exceptions.HTTPError as e:
            self._handle_http_error(e, response)

        except requests.exceptions.Timeout:
            logger.error(f"DeepSeek API timeout after {timeout}s")
            raise DeepSeekTimeout(
                f"Request timed out after {timeout} seconds",
                timeout=timeout
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API request failed: {e}")
            raise DeepSeekConnectionError(
                f"Failed to connect to DeepSeek API: {str(e)}"
            )

    def _handle_http_error(self, error: requests.exceptions.HTTPError, response: requests.Response):
        """
        Handle HTTP errors from DeepSeek API

        Args:
            error: HTTPError exception
            response: Response object

        Raises:
            Appropriate DeepSeekError subclass
        """
        status_code = response.status_code

        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", str(error))
            error_type = error_data.get("error", {}).get("type", "unknown_error")
        except:
            error_message = str(error)
            error_type = "unknown_error"

        logger.error(f"DeepSeek API error {status_code}: {error_message}")

        # Map status codes to specific exceptions
        if status_code == 401:
            raise DeepSeekAuthenticationError(
                "Invalid API key. Please check your DeepSeek API key.",
                status_code=status_code
            )

        elif status_code == 429:
            retry_after = response.headers.get("retry-after")
            raise DeepSeekRateLimitError(
                "Rate limit exceeded. Please try again later.",
                status_code=status_code,
                retry_after=int(retry_after) if retry_after else None
            )

        elif status_code == 400:
            raise DeepSeekInvalidRequestError(
                f"Invalid request: {error_message}",
                status_code=status_code
            )

        elif status_code >= 500:
            raise DeepSeekServerError(
                f"DeepSeek server error: {error_message}",
                status_code=status_code
            )

        else:
            raise DeepSeekError(
                f"DeepSeek API error: {error_message}",
                status_code=status_code,
                error_type=error_type
            )

    def list_models(self, timeout: float = 10.0) -> Dict[str, Any]:
        """
        List available models

        Args:
            timeout: Request timeout in seconds

        Returns:
            Response dict with 'data' containing model list

        Raises:
            DeepSeekError: If API call fails
        """
        url = f"{self.base_url}/models"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=timeout
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list DeepSeek models: {e}")
            raise DeepSeekError(f"Failed to list models: {str(e)}")


# ============================================================================
# EXCEPTION CLASSES
# ============================================================================

class DeepSeekError(Exception):
    """Base exception for DeepSeek API errors"""

    def __init__(self, message: str, status_code: Optional[int] = None, error_type: str = "unknown_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type


class DeepSeekAuthenticationError(DeepSeekError):
    """Authentication failed - invalid API key"""

    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message, status_code, "authentication_error")


class DeepSeekRateLimitError(DeepSeekError):
    """Rate limit exceeded"""

    def __init__(self, message: str, status_code: int = 429, retry_after: Optional[int] = None):
        super().__init__(message, status_code, "rate_limit_error")
        self.retry_after = retry_after


class DeepSeekInvalidRequestError(DeepSeekError):
    """Invalid request parameters"""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, status_code, "invalid_request_error")


class DeepSeekServerError(DeepSeekError):
    """DeepSeek server error"""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message, status_code, "server_error")


class DeepSeekTimeout(DeepSeekError):
    """Request timeout"""

    def __init__(self, message: str, timeout: float):
        super().__init__(message, None, "timeout_error")
        self.timeout = timeout


class DeepSeekConnectionError(DeepSeekError):
    """Connection error"""

    def __init__(self, message: str):
        super().__init__(message, None, "connection_error")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_deepseek_api_key(api_key: str, timeout: float = 10.0) -> tuple[bool, Optional[str]]:
    """
    Validate DeepSeek API key by making a test request

    Args:
        api_key: DeepSeek API key to validate
        timeout: Request timeout in seconds

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        client = DeepSeekClient(api_key)

        # Try to list models as a validation check
        client.list_models(timeout=timeout)

        logger.info("DeepSeek API key validation successful")
        return True, None

    except DeepSeekAuthenticationError as e:
        return False, "Invalid API key"

    except DeepSeekError as e:
        return False, str(e)

    except Exception as e:
        logger.error(f"Unexpected error validating DeepSeek API key: {e}")
        return False, "Validation failed"


def get_deepseek_client_from_env() -> DeepSeekClient:
    """
    Create DeepSeek client from environment variable

    Returns:
        DeepSeekClient instance

    Raises:
        ValueError: If DEEPSEEK_API_KEY not set
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable not set")

    return DeepSeekClient(api_key)
