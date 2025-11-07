"""
LinkedIn OAuth 2.0 Utilities

This module provides OAuth 2.0 flow implementation for LinkedIn.
Supports per-user credentials where each user provides their own LinkedIn app credentials.

OAuth Flow:
1. Authorization: Redirect user to LinkedIn OAuth URL
2. Token Exchange: Exchange authorization code for access token
3. User Info: Fetch user profile information

API Documentation:
- https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow
- https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin

IMPORTANT - LinkedIn API v2 Migration (2023):
LinkedIn deprecated r_liteprofile and r_basicprofile in favor of OpenID Connect.
This module uses the new OpenID Connect scopes (openid, profile) for compliance.

REFACTORED: Now inherits from OAuth2Base to eliminate code duplication.
"""
import os
import logging
import httpx
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from utils.oauth_base import OAuth2Base, validate_credentials_format

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# LinkedIn OAuth Configuration
# ============================================================================

# LinkedIn API endpoints
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

# LinkedIn required scopes (Updated for OpenID Connect - 2023)
# BREAKING CHANGE: r_liteprofile and r_basicprofile are DEPRECATED
# Migration guide: https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/migration-faq
#
# New scopes (effective 2023):
# - openid: Required for OpenID Connect authentication
# - profile: Replaces r_liteprofile - provides name, photo, etc.
# - email: Replaces r_emailaddress - provides email address
# - w_member_social: Permission to post on behalf of user
#
# Products required in LinkedIn App:
# 1. "Sign In with LinkedIn using OpenID Connect" - for openid, profile, email
# 2. "Share on LinkedIn" - for w_member_social
LINKEDIN_SCOPES = [
    "openid",           # Required for OpenID Connect (replaces deprecated r_liteprofile)
    "profile",          # Read basic profile (name, photo, etc.)
    "w_member_social"   # Permission to share posts on behalf of user
]

# Optional scope (requires additional approval in most cases):
# "email" - Access to user's email address
# Note: Only request email if absolutely necessary, as it may require LinkedIn review


# ============================================================================
# LinkedIn OAuth 2.0 Implementation
# ============================================================================

class LinkedInOAuth(OAuth2Base):
    """
    LinkedIn OAuth 2.0 implementation using base class.

    Inherits from OAuth2Base to eliminate code duplication while
    providing LinkedIn-specific configuration and behavior.
    """

    def __init__(self):
        super().__init__(platform_name="LinkedIn")

    def get_platform_config(self) -> Dict[str, Any]:
        """
        Get LinkedIn-specific OAuth configuration.

        Returns:
            Configuration dictionary for OAuth2Base
        """
        return {
            "auth_url": LINKEDIN_AUTH_URL,
            "token_url": LINKEDIN_TOKEN_URL,
            "userinfo_url": LINKEDIN_USERINFO_URL,
            "scopes": LINKEDIN_SCOPES,
            "scope_separator": " ",  # LinkedIn uses space-separated scopes
            "token_content_type": "application/x-www-form-urlencoded",
            "supports_refresh": True,
            "auth_extra_params": {},
            "token_extra_params": {},
            "userinfo_params": {},
            "userinfo_extra_headers": {}
        }

    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get LinkedIn user profile information using v2 API (OpenID Connect).

        This function uses the new OpenID Connect /userinfo endpoint which works
        with the 'openid' and 'profile' scopes. Includes fallback to legacy endpoint.

        Args:
            access_token: LinkedIn access token

        Returns:
            Dictionary with user info or None on error
            Example: {
                "sub": "abc123...",  # LinkedIn member ID
                "name": "John Doe",
                "given_name": "John",
                "family_name": "Doe",
                "email": "user@example.com"  # Only if email scope granted
            }
        """
        # Try OpenID Connect endpoint first (preferred)
        user_info = await super().get_user_info(access_token)

        if user_info:
            logger.info(f"Retrieved LinkedIn user info for: {user_info.get('name', 'Unknown')}")
            return user_info

        # Fallback to legacy /v2/me endpoint if OpenID Connect fails
        logger.warning("OpenID Connect userinfo failed, attempting fallback to legacy /v2/me endpoint")

        try:
            async with httpx.AsyncClient() as client:
                profile_response = await client.get(
                    "https://api.linkedin.com/v2/me",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                profile_response.raise_for_status()
                profile_data = profile_response.json()

                # Extract name from localized data
                first_name = profile_data.get("localizedFirstName", "")
                last_name = profile_data.get("localizedLastName", "")
                full_name = f"{first_name} {last_name}".strip()

                user_info = {
                    "sub": profile_data.get("id", ""),
                    "name": full_name,
                    "given_name": first_name,
                    "family_name": last_name,
                    "email": None  # Not available without email scope
                }

                logger.info(f"Retrieved LinkedIn user info (fallback): {full_name}")
                return user_info

        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {str(fallback_error)}")
            return None


# ============================================================================
# Module-Level Functions (For Backward Compatibility)
# ============================================================================

# Create singleton instance
_linkedin_oauth = LinkedInOAuth()


def get_authorization_url(client_id: str, redirect_uri: str, state: str, scopes: list = None) -> str:
    """
    Generate LinkedIn OAuth 2.0 authorization URL using per-user credentials.

    Args:
        client_id: User's LinkedIn Client ID
        redirect_uri: OAuth redirect URI (should match app settings)
        state: Random state parameter for CSRF protection
        scopes: List of OAuth scopes (optional, defaults to LINKEDIN_SCOPES)

    Returns:
        Authorization URL string

    Example:
        >>> client_id = "user_provided_client_id"
        >>> redirect_uri = "http://localhost:8000/api/oauth-setup/linkedin/callback"
        >>> state = secrets.token_urlsafe(32)
        >>> auth_url = get_authorization_url(client_id, redirect_uri, state)
        >>> # Redirect user to auth_url
    """
    logger.info(f"Generated LinkedIn OAuth authorization URL with state: {state[:10]}...")
    logger.info(f"Using scopes: {', '.join(scopes or LINKEDIN_SCOPES)}")
    return _linkedin_oauth.get_authorization_url(client_id, redirect_uri, state, scopes)


async def exchange_code_for_token(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str
) -> Optional[Dict[str, Any]]:
    """
    Exchange LinkedIn authorization code for access token.

    Args:
        code: Authorization code from OAuth callback
        client_id: User's LinkedIn Client ID
        client_secret: User's LinkedIn Client Secret
        redirect_uri: OAuth redirect URI (must match authorization request)

    Returns:
        Dictionary with access_token, expires_in, and scope, or None on error
        Example: {
            "access_token": "...",
            "expires_in": 5184000,  # 60 days in seconds
            "scope": "openid profile email w_member_social"
        }
    """
    logger.debug(f"Exchanging LinkedIn authorization code for token")
    result = await _linkedin_oauth.exchange_code_for_token(code, client_id, client_secret, redirect_uri)

    if result:
        logger.info(f"Successfully exchanged LinkedIn authorization code for access token")
    else:
        logger.error(f"Failed to exchange LinkedIn authorization code")

    return result


async def get_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get LinkedIn user profile information using v2 API (OpenID Connect).

    This function uses the new OpenID Connect /userinfo endpoint which works
    with the 'openid' and 'profile' scopes.

    Args:
        access_token: LinkedIn access token

    Returns:
        Dictionary with user info or None on error
        Example: {
            "sub": "abc123...",  # LinkedIn member ID
            "name": "John Doe",
            "given_name": "John",
            "family_name": "Doe",
            "email": "user@example.com"  # Only if email scope granted
        }
    """
    return await _linkedin_oauth.get_user_info(access_token)


async def get_user_profile(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Alias for get_user_info() for consistency with other OAuth implementations.

    Args:
        access_token: LinkedIn access token

    Returns:
        Dictionary with user profile info or None on error
    """
    return await get_user_info(access_token)


async def validate_token(access_token: str) -> bool:
    """
    Validate a LinkedIn access token by making a test API call.

    Args:
        access_token: LinkedIn access token to validate

    Returns:
        True if token is valid, False otherwise
    """
    return await _linkedin_oauth.validate_token(access_token)


async def refresh_access_token(
    refresh_token: str,
    client_id: str,
    client_secret: str
) -> Optional[Dict[str, Any]]:
    """
    Refresh LinkedIn access token.

    Note: LinkedIn's refresh token flow may vary depending on your app configuration.
    Some LinkedIn apps don't support refresh tokens and require re-authorization.

    Args:
        refresh_token: LinkedIn refresh token
        client_id: User's LinkedIn Client ID
        client_secret: User's LinkedIn Client Secret

    Returns:
        Dictionary with new access_token and expires_in, or None on error
    """
    logger.debug("Refreshing LinkedIn access token")
    result = await _linkedin_oauth.refresh_access_token(refresh_token, client_id, client_secret)

    if result:
        logger.info(f"Successfully refreshed LinkedIn token")
    else:
        logger.error(f"Failed to refresh LinkedIn token")

    return result


# ============================================================================
# Helper Functions
# ============================================================================

def get_scopes() -> list:
    """
    Get list of LinkedIn OAuth scopes.

    Returns:
        List of scope strings
    """
    return _linkedin_oauth.get_scopes()


def format_scopes(scopes: list = None) -> str:
    """
    Format scopes for OAuth URL (space-separated for LinkedIn).

    Args:
        scopes: List of scope strings, or None to use default scopes

    Returns:
        Space-separated scope string
    """
    return _linkedin_oauth.format_scopes(scopes)


def validate_credentials_format_linkedin(client_id: str, client_secret: str) -> tuple[bool, str]:
    """
    Validate LinkedIn credentials format.

    Args:
        client_id: LinkedIn Client ID to validate
        client_secret: LinkedIn Client Secret to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_credentials_format(client_id, client_secret, "LinkedIn")
