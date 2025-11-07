"""
Threads OAuth 2.0 Utilities

This module provides OAuth 2.0 flow implementation for Threads (Meta platform).
Threads uses the Instagram Graph API for authentication and publishing.

OAuth Flow:
1. Authorization: Redirect user to Threads OAuth URL
2. Token Exchange: Exchange authorization code for short-lived access token
3. Long-Lived Token: Exchange short-lived for long-lived token (60 days)
4. Token Refresh: Refresh long-lived token before expiry

API Documentation:
- https://developers.facebook.com/docs/threads
- https://developers.facebook.com/docs/instagram-api/overview

REFACTORED: Now inherits from OAuth2Base to eliminate code duplication.
"""
import os
import logging
import httpx
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from utils.oauth_base import OAuth2Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Threads OAuth Configuration
# ============================================================================
THREADS_CLIENT_ID = os.getenv("THREADS_CLIENT_ID")
THREADS_CLIENT_SECRET = os.getenv("THREADS_CLIENT_SECRET")
THREADS_REDIRECT_URI = os.getenv(
    "THREADS_REDIRECT_URI",
    "http://localhost:8000/api/social-media/threads/callback"
)

# Threads API endpoints (uses Instagram Graph API infrastructure)
THREADS_AUTH_URL = "https://threads.net/oauth/authorize"
THREADS_TOKEN_URL = "https://graph.threads.net/oauth/access_token"
THREADS_LONG_LIVED_TOKEN_URL = "https://graph.threads.net/access_token"
THREADS_REFRESH_TOKEN_URL = "https://graph.threads.net/refresh_access_token"
THREADS_USERINFO_URL = "https://graph.threads.net/v1.0/me"

# Threads required scopes
THREADS_SCOPES = [
    "threads_basic",            # Basic profile access
    "threads_content_publish"   # Permission to publish posts
]


# ============================================================================
# Threads OAuth 2.0 Implementation
# ============================================================================

class ThreadsOAuth(OAuth2Base):
    """
    Threads OAuth 2.0 implementation using base class.

    Inherits from OAuth2Base to eliminate code duplication while
    providing Threads-specific configuration and behavior.
    """

    def __init__(self):
        super().__init__(platform_name="Threads")

    def get_platform_config(self) -> Dict[str, Any]:
        """
        Get Threads-specific OAuth configuration.

        Returns:
            Configuration dictionary for OAuth2Base
        """
        return {
            "auth_url": THREADS_AUTH_URL,
            "token_url": THREADS_TOKEN_URL,
            "userinfo_url": THREADS_USERINFO_URL,
            "scopes": THREADS_SCOPES,
            "scope_separator": ",",  # Threads uses comma-separated scopes
            "token_content_type": "application/x-www-form-urlencoded",
            "supports_refresh": True,
            "auth_extra_params": {},
            "token_extra_params": {},
            "userinfo_params": {
                "fields": "id,username,name,threads_profile_picture_url,threads_biography"
            },
            "userinfo_extra_headers": {}
        }

    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get Threads user profile information.

        Args:
            access_token: Threads access token (short-lived or long-lived)

        Returns:
            Dictionary with user info or None on error
            Example: {
                "id": "12345678901234567",
                "username": "my_username",
                "name": "Display Name",
                "threads_profile_picture_url": "https://..."
            }
        """
        # Threads requires access_token as query parameter
        config = self.get_platform_config()
        params = {**config["userinfo_params"], "access_token": access_token}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(THREADS_USERINFO_URL, params=params, timeout=10.0)

                if response.status_code == 200:
                    user_info = response.json()
                    logger.info(f"Retrieved Threads user info for: @{user_info.get('username')}")
                    return user_info
                else:
                    error_data = response.json() if response.text else {}
                    logger.error(f"Failed to get Threads user info: {response.status_code} - {error_data}")
                    return None

            except Exception as e:
                logger.error(f"Error getting Threads user info: {str(e)}")
                return None


# ============================================================================
# Threads-Specific Token Management
# ============================================================================

async def exchange_for_long_lived_token(short_lived_token: str) -> Optional[Dict[str, Any]]:
    """
    Exchange Threads short-lived token for long-lived token.

    Long-lived tokens are valid for 60 days and can be refreshed.
    This should be called immediately after getting a short-lived token.

    Args:
        short_lived_token: Short-lived access token from exchange_code_for_token

    Returns:
        Dictionary with access_token, token_type, and expires_in, or None on error
        Example: {
            "access_token": "...",
            "token_type": "bearer",
            "expires_in": 5183944  # ~60 days in seconds
        }
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "grant_type": "th_exchange_token",
                "client_secret": THREADS_CLIENT_SECRET,
                "access_token": short_lived_token
            }

            logger.debug("Exchanging short-lived token for long-lived token")
            response = await client.get(THREADS_LONG_LIVED_TOKEN_URL, params=params)
            response.raise_for_status()
            tokens = response.json()

            logger.info(f"Successfully exchanged for long-lived token (expires in {tokens.get('expires_in', 0)} seconds)")
            return tokens

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error exchanging for long-lived token: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Error exchanging for long-lived token: {str(e)}")
        return None


async def refresh_long_lived_token(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Refresh Threads long-lived access token.

    Long-lived tokens should be refreshed before they expire (60 days).
    Refreshing extends the token for another 60 days.

    Args:
        access_token: Current Threads access token to refresh

    Returns:
        Dictionary with new access_token, token_type, and expires_in, or None on error
        Example: {
            "access_token": "...",
            "token_type": "bearer",
            "expires_in": 5183944  # ~60 days in seconds
        }
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "grant_type": "th_refresh_token",
                "access_token": access_token
            }

            logger.debug("Refreshing Threads access token")
            response = await client.get(THREADS_REFRESH_TOKEN_URL, params=params)
            response.raise_for_status()
            tokens = response.json()

            logger.info(f"Successfully refreshed Threads token (expires in {tokens.get('expires_in', 0)} seconds)")
            return tokens

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error refreshing Threads token: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Error refreshing Threads token: {str(e)}")
        return None


# ============================================================================
# OAuth Configuration Checks
# ============================================================================

def is_threads_configured() -> bool:
    """
    Check if Threads OAuth is configured.

    Returns:
        True if Threads OAuth credentials are configured, False otherwise
    """
    return bool(THREADS_CLIENT_ID and THREADS_CLIENT_SECRET)


def get_threads_config_status() -> Dict[str, Any]:
    """
    Get detailed Threads OAuth configuration status.

    Returns:
        Dictionary with configuration status details
    """
    return {
        "configured": is_threads_configured(),
        "client_id_set": bool(THREADS_CLIENT_ID),
        "client_secret_set": bool(THREADS_CLIENT_SECRET),
        "redirect_uri": THREADS_REDIRECT_URI,
        "scopes": THREADS_SCOPES,
        "oauth_version": "2.0",
        "platform": "threads"
    }


# ============================================================================
# Module-Level Functions (For Backward Compatibility)
# ============================================================================

# Create singleton instance
_threads_oauth = ThreadsOAuth()


def get_authorization_url(state: str) -> str:
    """
    Generate Threads OAuth 2.0 authorization URL.

    Args:
        state: Random state parameter for CSRF protection

    Returns:
        Authorization URL string

    Raises:
        ValueError: If Threads OAuth not configured

    Example:
        >>> state = secrets.token_urlsafe(32)
        >>> auth_url = get_authorization_url(state)
        >>> # Redirect user to auth_url
    """
    if not is_threads_configured():
        raise ValueError(
            "Threads OAuth not configured - missing THREADS_CLIENT_ID or THREADS_CLIENT_SECRET"
        )

    logger.info(f"Generated Threads OAuth authorization URL with state: {state[:10]}...")
    return _threads_oauth.get_authorization_url(
        THREADS_CLIENT_ID,
        THREADS_REDIRECT_URI,
        state
    )


async def exchange_code_for_token(code: str) -> Optional[Dict[str, Any]]:
    """
    Exchange Threads authorization code for short-lived access token.

    This is step 2 of the OAuth flow. The returned token is short-lived
    and should be immediately exchanged for a long-lived token.

    Args:
        code: Authorization code from OAuth callback

    Returns:
        Dictionary with access_token and user_id, or None on error
        Example: {
            "access_token": "...",
            "user_id": "12345678901234567"
        }
    """
    logger.debug(f"Exchanging authorization code for token")
    result = await _threads_oauth.exchange_code_for_token(
        code,
        THREADS_CLIENT_ID,
        THREADS_CLIENT_SECRET,
        THREADS_REDIRECT_URI
    )

    if result:
        logger.info(f"Successfully exchanged Threads authorization code for user {result.get('user_id')}")
    else:
        logger.error("Failed to exchange Threads authorization code")

    return result


async def refresh_access_token(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Refresh Threads access token.

    This is a wrapper that calls refresh_long_lived_token for consistency
    with other OAuth implementations.

    Args:
        access_token: Current Threads access token to refresh

    Returns:
        Dictionary with new access_token, token_type, and expires_in, or None on error
    """
    return await refresh_long_lived_token(access_token)


async def get_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get Threads user profile information.

    Args:
        access_token: Threads access token (short-lived or long-lived)

    Returns:
        Dictionary with user info or None on error
        Example: {
            "id": "12345678901234567",
            "username": "my_username",
            "name": "Display Name",
            "threads_profile_picture_url": "https://..."
        }
    """
    return await _threads_oauth.get_user_info(access_token)


async def get_user_profile(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Alias for get_user_info() for consistency with other OAuth implementations.

    Args:
        access_token: Threads access token

    Returns:
        Dictionary with user profile info or None on error
    """
    return await get_user_info(access_token)


async def validate_token(access_token: str) -> bool:
    """
    Validate a Threads access token by making a test API call.

    Args:
        access_token: Threads access token to validate

    Returns:
        True if token is valid, False otherwise
    """
    return await _threads_oauth.validate_token(access_token)


# ============================================================================
# Helper Functions
# ============================================================================

async def get_token_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a Threads access token.

    This can be used to check token validity and expiration.

    Args:
        access_token: Threads access token

    Returns:
        Dictionary with token info including expiration, or None on error
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "access_token": access_token
            }

            # Note: Threads doesn't have a dedicated token info endpoint
            # We use the user info endpoint as a proxy for validation
            response = await client.get(
                THREADS_USERINFO_URL,
                params={"fields": "id", "access_token": access_token}
            )
            response.raise_for_status()

            return {
                "valid": True,
                "user_id": response.json().get("id")
            }

    except Exception as e:
        logger.error(f"Error getting token info: {str(e)}")
        return None


def get_scopes() -> list:
    """
    Get list of Threads OAuth scopes.

    Returns:
        List of scope strings
    """
    return _threads_oauth.get_scopes()


def format_scopes(scopes: list = None) -> str:
    """
    Format scopes for OAuth URL (comma-separated for Threads).

    Args:
        scopes: List of scope strings, or None to use default scopes

    Returns:
        Comma-separated scope string
    """
    return _threads_oauth.format_scopes(scopes)
