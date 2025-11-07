"""
OAuth Base Classes - Foundation for All OAuth Implementations

This module provides base classes for OAuth 2.0 and OAuth 1.0a implementations,
eliminating code duplication across platform-specific OAuth modules.

Architecture:
- OAuthBase: Common functionality for all OAuth flows
- OAuth2Base: OAuth 2.0 specific implementation (LinkedIn, Threads, Instagram)
- OAuth1Base: OAuth 1.0a specific implementation (Twitter)

Benefits:
- Single source of truth for OAuth logic
- Consistent error handling across platforms
- Easier testing and maintenance
- Reduced code duplication (2,000+ lines)

Usage:
    from utils.oauth_base import OAuth2Base

    class LinkedInOAuth(OAuth2Base):
        def get_platform_config(self):
            return {
                "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
                "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
                ...
            }
"""

import logging
import httpx
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger as loguru_logger

# Configure standard logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class OAuthException(Exception):
    """Base exception for all OAuth errors"""
    pass


class AuthenticationException(OAuthException):
    """Authentication failed (invalid credentials, expired tokens, etc.)"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class RateLimitException(OAuthException):
    """API rate limit exceeded"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class ConfigurationException(OAuthException):
    """OAuth not configured or misconfigured"""
    pass


# ============================================================================
# Base OAuth Class
# ============================================================================

class OAuthBase(ABC):
    """
    Base class for all OAuth implementations.

    Provides common functionality:
    - HTTP client management
    - Error handling
    - Logging
    - Token validation patterns

    Subclasses must implement:
    - get_platform_config(): Return platform-specific configuration
    """

    def __init__(self, platform_name: str):
        """
        Initialize OAuth base.

        Args:
            platform_name: Name of the platform (e.g., "linkedin", "twitter")
        """
        self.platform_name = platform_name
        self.logger = logger

    @abstractmethod
    def get_platform_config(self) -> Dict[str, Any]:
        """
        Get platform-specific OAuth configuration.

        Must return a dictionary with:
        - auth_url: Authorization endpoint
        - token_url: Token exchange endpoint
        - scopes: Required OAuth scopes
        - Any other platform-specific settings

        Returns:
            Dictionary with platform configuration
        """
        pass

    async def _make_http_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Make an HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: HTTP headers
            params: Query parameters
            data: Form data (application/x-www-form-urlencoded)
            json_body: JSON body (application/json)
            timeout: Request timeout in seconds

        Returns:
            Response JSON data or None if request fails

        Raises:
            AuthenticationException: For 401/403 errors
            RateLimitException: For 429 errors
            OAuthException: For other errors
        """
        try:
            async with httpx.AsyncClient() as client:
                self.logger.debug(f"Making {method} request to {url}")

                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_body,
                    timeout=timeout
                )

                # Handle successful responses
                if response.status_code == 200:
                    return response.json() if response.text else {}

                # Handle error responses
                error_data = response.json() if response.text else {}
                error_message = (
                    error_data.get("error_description") or
                    error_data.get("message") or
                    error_data.get("error") or
                    response.text
                )

                # Authentication errors
                if response.status_code in [401, 403]:
                    raise AuthenticationException(
                        f"{self.platform_name} authentication failed: {error_message}",
                        status_code=response.status_code,
                        response_text=response.text
                    )

                # Rate limit errors
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise RateLimitException(
                        f"{self.platform_name} rate limit exceeded",
                        retry_after=int(retry_after) if retry_after else None
                    )

                # Other errors
                self.logger.error(
                    f"{self.platform_name} API error: {response.status_code} - {error_message}"
                )
                return None

        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"HTTP error in {self.platform_name} request: {e.response.status_code} - {e.response.text}"
            )
            return None
        except httpx.TimeoutException:
            self.logger.error(f"{self.platform_name} request timed out")
            return None
        except Exception as e:
            self.logger.error(f"Error in {self.platform_name} request: {str(e)}")
            return None

    def _log_success(self, operation: str, details: str = ""):
        """Log successful operation"""
        message = f"{self.platform_name} {operation} successful"
        if details:
            message += f": {details}"
        self.logger.info(message)

    def _log_error(self, operation: str, error: str):
        """Log failed operation"""
        self.logger.error(f"{self.platform_name} {operation} failed: {error}")


# ============================================================================
# OAuth 2.0 Base Class
# ============================================================================

class OAuth2Base(OAuthBase):
    """
    Base class for OAuth 2.0 implementations.

    Implements the standard OAuth 2.0 authorization code flow:
    1. Generate authorization URL
    2. Exchange authorization code for access token
    3. Refresh access token (if supported)
    4. Validate access token

    Platform-specific modules only need to:
    - Provide configuration via get_platform_config()
    - Override methods for platform-specific behavior

    Supported platforms:
    - LinkedIn (OAuth 2.0 with OpenID Connect)
    - Threads (OAuth 2.0 via Meta)
    - Instagram (OAuth 2.0 via Facebook Graph API)
    """

    def get_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        state: str,
        scopes: Optional[List[str]] = None
    ) -> str:
        """
        Generate OAuth 2.0 authorization URL.

        Args:
            client_id: OAuth client ID
            redirect_uri: Callback URL after authorization
            state: CSRF protection state parameter
            scopes: List of OAuth scopes (optional, uses platform defaults)

        Returns:
            Authorization URL string
        """
        config = self.get_platform_config()
        scopes = scopes or config.get("scopes", [])

        # Platform-specific scope separator
        scope_separator = config.get("scope_separator", " ")
        scope_string = scope_separator.join(scopes)

        # Build parameters
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scope_string
        }

        # Add platform-specific parameters
        extra_params = config.get("auth_extra_params", {})
        params.update(extra_params)

        # Build URL
        from urllib.parse import urlencode
        auth_url = f"{config['auth_url']}?{urlencode(params)}"

        self._log_success("authorization URL generated", f"state: {state[:10]}...")
        return auth_url

    async def exchange_code_for_token(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access token.

        This is the standard OAuth 2.0 token exchange step.

        Args:
            code: Authorization code from callback
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: Callback URL (must match authorization request)

        Returns:
            Dictionary with:
            - access_token: Access token string
            - token_type: Token type (usually "bearer")
            - expires_in: Token lifetime in seconds (optional)
            - refresh_token: Refresh token (optional)
            - scope: Granted scopes (optional)

            None if exchange fails
        """
        config = self.get_platform_config()

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri
        }

        # Add platform-specific parameters
        extra_params = config.get("token_extra_params", {})
        token_data.update(extra_params)

        # Determine content type
        content_type = config.get("token_content_type", "application/x-www-form-urlencoded")
        headers = {"Content-Type": content_type}

        self.logger.debug(f"Exchanging authorization code for {self.platform_name} token")

        # Make request
        response_data = await self._make_http_request(
            method="POST",
            url=config["token_url"],
            headers=headers,
            data=token_data if content_type == "application/x-www-form-urlencoded" else None,
            json_body=token_data if content_type == "application/json" else None
        )

        if response_data:
            self._log_success("token exchange", f"token expires in {response_data.get('expires_in', 'N/A')}s")
            return response_data

        self._log_error("token exchange", "failed to get access token")
        return None

    async def refresh_access_token(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: str
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh an OAuth 2.0 access token.

        Note: Not all platforms support refresh tokens.

        Args:
            refresh_token: Refresh token from initial token exchange
            client_id: OAuth client ID
            client_secret: OAuth client secret

        Returns:
            Dictionary with new access_token and expires_in, or None if refresh fails
        """
        config = self.get_platform_config()

        # Check if platform supports refresh
        if not config.get("supports_refresh", True):
            self.logger.warning(f"{self.platform_name} does not support token refresh")
            return None

        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret
        }

        content_type = config.get("token_content_type", "application/x-www-form-urlencoded")
        headers = {"Content-Type": content_type}

        self.logger.debug(f"Refreshing {self.platform_name} access token")

        response_data = await self._make_http_request(
            method="POST",
            url=config["token_url"],
            headers=headers,
            data=token_data if content_type == "application/x-www-form-urlencoded" else None,
            json_body=token_data if content_type == "application/json" else None
        )

        if response_data:
            self._log_success("token refresh", f"new token expires in {response_data.get('expires_in', 'N/A')}s")
            return response_data

        self._log_error("token refresh", "failed to refresh token")
        return None

    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile information using access token.

        Args:
            access_token: OAuth access token

        Returns:
            Dictionary with user information, or None if request fails
        """
        config = self.get_platform_config()
        userinfo_url = config.get("userinfo_url")

        if not userinfo_url:
            self.logger.warning(f"{self.platform_name} does not define a userinfo_url")
            return None

        headers = {"Authorization": f"Bearer {access_token}"}

        # Add platform-specific headers
        extra_headers = config.get("userinfo_extra_headers", {})
        headers.update(extra_headers)

        # Get platform-specific query parameters
        params = config.get("userinfo_params", {})

        self.logger.debug(f"Fetching {self.platform_name} user info")

        response_data = await self._make_http_request(
            method="GET",
            url=userinfo_url,
            headers=headers,
            params=params
        )

        if response_data:
            username = response_data.get("username") or response_data.get("screen_name") or response_data.get("name", "Unknown")
            self._log_success("user info fetch", f"user: {username}")
            return response_data

        self._log_error("user info fetch", "failed to get user info")
        return None

    async def validate_token(self, access_token: str) -> bool:
        """
        Validate an OAuth 2.0 access token by making a test API call.

        Args:
            access_token: Access token to validate

        Returns:
            True if token is valid, False otherwise
        """
        try:
            user_info = await self.get_user_info(access_token)
            return user_info is not None
        except Exception as e:
            self.logger.error(f"Error validating {self.platform_name} token: {str(e)}")
            return False

    def get_scopes(self) -> List[str]:
        """
        Get list of OAuth scopes for this platform.

        Returns:
            List of scope strings
        """
        config = self.get_platform_config()
        return config.get("scopes", []).copy()

    def format_scopes(self, scopes: Optional[List[str]] = None) -> str:
        """
        Format scopes for OAuth URL.

        Args:
            scopes: List of scope strings, or None to use default scopes

        Returns:
            Formatted scope string (space or comma-separated based on platform)
        """
        config = self.get_platform_config()
        scopes = scopes or config.get("scopes", [])
        scope_separator = config.get("scope_separator", " ")
        return scope_separator.join(scopes)


# ============================================================================
# OAuth 1.0a Base Class
# ============================================================================

class OAuth1Base(OAuthBase):
    """
    Base class for OAuth 1.0a implementations (Twitter).

    Implements the OAuth 1.0a three-legged flow:
    1. Get request token
    2. User authorization
    3. Exchange for access token

    Includes signature generation and OAuth header construction.

    Note: OAuth 1.0a is more complex than OAuth 2.0 and requires
    HMAC-SHA1 signature generation for every request.
    """

    def __init__(self, platform_name: str = "twitter"):
        super().__init__(platform_name)

    def generate_nonce(self) -> str:
        """
        Generate a cryptographically secure nonce for OAuth 1.0a.

        Returns:
            32-character random hex string
        """
        import secrets
        return secrets.token_hex(16)

    def generate_timestamp(self) -> str:
        """
        Generate current Unix timestamp.

        Returns:
            Current timestamp as string
        """
        import time
        return str(int(time.time()))

    def percent_encode(self, value: str) -> str:
        """
        Percent-encode a string according to OAuth 1.0a spec (RFC 3986).

        OAuth requires specific encoding rules:
        - Letters, digits, '-', '.', '_', '~' are not encoded
        - All other characters are percent-encoded
        - Spaces are encoded as %20 (not +)

        Args:
            value: String to encode

        Returns:
            Percent-encoded string
        """
        from urllib.parse import quote
        return quote(str(value), safe='')

    def generate_oauth_signature(
        self,
        method: str,
        url: str,
        params: Dict[str, str],
        consumer_secret: str,
        token_secret: str = ""
    ) -> str:
        """
        Generate OAuth 1.0a HMAC-SHA1 signature.

        Steps:
        1. Sort parameters alphabetically
        2. Build parameter string
        3. Create signature base string
        4. Create signing key
        5. Generate HMAC-SHA1 signature
        6. Base64 encode

        Args:
            method: HTTP method (GET, POST)
            url: Request URL
            params: All request parameters (OAuth + query/body)
            consumer_secret: Consumer secret (API secret)
            token_secret: Token secret (empty for request token)

        Returns:
            Base64-encoded signature
        """
        import hmac
        import hashlib
        import base64

        # Sort parameters
        sorted_params = sorted(params.items())

        # Create parameter string
        param_string = "&".join([
            f"{self.percent_encode(k)}={self.percent_encode(v)}"
            for k, v in sorted_params
        ])

        # Create signature base string
        signature_base = (
            f"{method.upper()}&"
            f"{self.percent_encode(url)}&"
            f"{self.percent_encode(param_string)}"
        )

        # Create signing key
        signing_key = f"{self.percent_encode(consumer_secret)}&{self.percent_encode(token_secret)}"

        # Generate HMAC-SHA1 signature
        signature = hmac.new(
            signing_key.encode('utf-8'),
            signature_base.encode('utf-8'),
            hashlib.sha1
        ).digest()

        return base64.b64encode(signature).decode('utf-8')

    def generate_oauth_header(
        self,
        method: str,
        url: str,
        consumer_key: str,
        consumer_secret: str,
        token: Optional[str] = None,
        token_secret: str = "",
        params: Optional[Dict[str, str]] = None,
        callback_url: Optional[str] = None,
        verifier: Optional[str] = None
    ) -> str:
        """
        Generate OAuth 1.0a Authorization header.

        This creates the complete OAuth header with:
        - oauth_consumer_key
        - oauth_signature_method
        - oauth_timestamp
        - oauth_nonce
        - oauth_version
        - oauth_signature (computed)
        - oauth_token (if provided)
        - oauth_callback (if provided)
        - oauth_verifier (if provided)

        Args:
            method: HTTP method
            url: Request URL
            consumer_key: Consumer key (API key)
            consumer_secret: Consumer secret
            token: OAuth token (for access token requests)
            token_secret: OAuth token secret
            params: Additional request parameters
            callback_url: OAuth callback URL (for request token)
            verifier: OAuth verifier (for access token)

        Returns:
            OAuth Authorization header value
        """
        # OAuth parameters
        oauth_params = {
            "oauth_consumer_key": consumer_key,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": self.generate_timestamp(),
            "oauth_nonce": self.generate_nonce(),
            "oauth_version": "1.0"
        }

        # Add optional parameters
        if token:
            oauth_params["oauth_token"] = token
        if callback_url:
            oauth_params["oauth_callback"] = callback_url
        if verifier:
            oauth_params["oauth_verifier"] = verifier

        # Merge with request parameters for signature
        all_params = {**oauth_params}
        if params:
            all_params.update(params)

        # Generate signature
        signature = self.generate_oauth_signature(
            method, url, all_params, consumer_secret, token_secret
        )
        oauth_params["oauth_signature"] = signature

        # Build Authorization header
        header_parts = [
            f'{self.percent_encode(k)}="{self.percent_encode(v)}"'
            for k, v in sorted(oauth_params.items())
        ]

        return f"OAuth {', '.join(header_parts)}"

    async def get_request_token(
        self,
        request_token_url: str,
        consumer_key: str,
        consumer_secret: str,
        callback_url: str
    ) -> Optional[Dict[str, str]]:
        """
        Step 1 of OAuth 1.0a: Get request token.

        This obtains temporary credentials from the platform.

        Args:
            request_token_url: Platform's request token endpoint
            consumer_key: OAuth consumer key
            consumer_secret: OAuth consumer secret
            callback_url: OAuth callback URL

        Returns:
            Dictionary with:
            - oauth_token: Temporary token
            - oauth_token_secret: Temporary token secret
            - oauth_callback_confirmed: "true" if callback confirmed

            None if request fails
        """
        # Generate OAuth header
        auth_header = self.generate_oauth_header(
            method="POST",
            url=request_token_url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            callback_url=callback_url
        )

        self.logger.info(f"Requesting {self.platform_name} OAuth request token")

        # Make request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                request_token_url,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )

            if response.status_code != 200:
                self.logger.error(
                    f"Failed to get request token: {response.status_code} - {response.text}"
                )
                return None

            # Parse URL-encoded response
            from urllib.parse import parse_qs
            response_data = parse_qs(response.text)

            result = {
                "oauth_token": response_data.get("oauth_token", [None])[0],
                "oauth_token_secret": response_data.get("oauth_token_secret", [None])[0],
                "oauth_callback_confirmed": response_data.get("oauth_callback_confirmed", [None])[0]
            }

            if not result["oauth_token"] or not result["oauth_token_secret"]:
                self.logger.error("Invalid response: missing token")
                return None

            self._log_success("request token", f"token: {result['oauth_token'][:10]}...")
            return result

    def get_authorization_url(
        self,
        authorization_url: str,
        oauth_token: str
    ) -> str:
        """
        Step 2 of OAuth 1.0a: Generate authorization URL.

        Args:
            authorization_url: Platform's authorization endpoint
            oauth_token: Request token from step 1

        Returns:
            Authorization URL to redirect user to
        """
        auth_url = f"{authorization_url}?oauth_token={self.percent_encode(oauth_token)}"
        self._log_success("authorization URL generated", f"token: {oauth_token[:10]}...")
        return auth_url

    async def get_access_token(
        self,
        access_token_url: str,
        consumer_key: str,
        consumer_secret: str,
        oauth_token: str,
        oauth_token_secret: str,
        oauth_verifier: str
    ) -> Optional[Dict[str, str]]:
        """
        Step 3 of OAuth 1.0a: Exchange request token for access token.

        Args:
            access_token_url: Platform's access token endpoint
            consumer_key: OAuth consumer key
            consumer_secret: OAuth consumer secret
            oauth_token: Request token from callback
            oauth_token_secret: Request token secret from step 1
            oauth_verifier: Verifier from callback

        Returns:
            Dictionary with:
            - oauth_token: User's access token (permanent)
            - oauth_token_secret: User's access token secret
            - user_id: Platform user ID (platform-specific)
            - screen_name: Username (platform-specific)

            None if exchange fails
        """
        # Generate OAuth header with verifier
        auth_header = self.generate_oauth_header(
            method="POST",
            url=access_token_url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            token=oauth_token,
            token_secret=oauth_token_secret,
            verifier=oauth_verifier
        )

        self.logger.info(f"Exchanging request token for {self.platform_name} access token")

        # Make request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                access_token_url,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )

            if response.status_code != 200:
                self.logger.error(
                    f"Failed to get access token: {response.status_code} - {response.text}"
                )
                return None

            # Parse URL-encoded response
            from urllib.parse import parse_qs
            response_data = parse_qs(response.text)

            result = {
                "oauth_token": response_data.get("oauth_token", [None])[0],
                "oauth_token_secret": response_data.get("oauth_token_secret", [None])[0],
                "user_id": response_data.get("user_id", [None])[0],
                "screen_name": response_data.get("screen_name", [None])[0]
            }

            if not result["oauth_token"] or not result["oauth_token_secret"]:
                self.logger.error("Invalid response: missing token")
                return None

            self._log_success("access token", f"user: @{result.get('screen_name', 'unknown')}")
            return result

    async def make_authenticated_request(
        self,
        method: str,
        url: str,
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_token_secret: str,
        params: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make an authenticated API request using OAuth 1.0a.

        Use this for calling platform APIs after obtaining access tokens.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: API endpoint URL
            consumer_key: OAuth consumer key
            consumer_secret: OAuth consumer secret
            access_token: User's access token
            access_token_secret: User's access token secret
            params: Request parameters

        Returns:
            Response JSON data or None if request fails
        """
        # Generate OAuth header
        auth_header = self.generate_oauth_header(
            method=method,
            url=url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            token=access_token,
            token_secret=access_token_secret,
            params=params
        )

        self.logger.debug(f"Making authenticated {method} request to {url}")

        # Make request
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers={"Authorization": auth_header},
                params=params if method.upper() == "GET" else None,
                data=params if method.upper() == "POST" else None
            )

            if response.status_code == 200:
                return response.json() if response.text else {}

            self.logger.error(
                f"Authenticated request failed: {response.status_code} - {response.text}"
            )
            return None


# ============================================================================
# Utility Functions
# ============================================================================

def validate_credentials_format(
    client_id: str,
    client_secret: str,
    platform_name: str = "OAuth"
) -> tuple[bool, str]:
    """
    Validate OAuth credentials format.

    Args:
        client_id: Client ID to validate
        client_secret: Client secret to validate
        platform_name: Platform name for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not client_id or not client_id.strip():
        return False, f"{platform_name} Client ID is required"

    if not client_secret or not client_secret.strip():
        return False, f"{platform_name} Client Secret is required"

    if len(client_id) < 10:
        return False, f"{platform_name} Client ID appears to be invalid (too short)"

    if len(client_secret) < 10:
        return False, f"{platform_name} Client Secret appears to be invalid (too short)"

    return True, "Credentials format is valid"
