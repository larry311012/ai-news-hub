"""
Instagram OAuth 2.0 Utilities via Facebook Graph API

This module provides utilities for Instagram OAuth 2.0 authentication
via Facebook Graph API. Instagram uses Facebook's OAuth infrastructure.

Instagram Publishing Requirements:
- Instagram Business Account (not personal account)
- Instagram Business Account linked to a Facebook Page
- Facebook App with Instagram permissions

API Documentation:
- https://developers.facebook.com/docs/instagram-api/
- https://developers.facebook.com/docs/instagram-api/getting-started

REFACTORED: Now inherits from OAuth2Base to eliminate code duplication.
"""

import os
import httpx
from typing import Optional, Dict, List, Any
from loguru import logger

from utils.oauth_base import OAuth2Base


# ============================================================================
# Configuration
# ============================================================================

def get_instagram_config() -> Dict[str, Optional[str]]:
    """
    Get Instagram OAuth configuration from environment variables.

    Returns:
        {
            "app_id": "...",
            "app_secret": "...",
            "redirect_uri": "..."
        }
    """
    return {
        "app_id": os.getenv("INSTAGRAM_APP_ID"),
        "app_secret": os.getenv("INSTAGRAM_APP_SECRET"),
        "redirect_uri": os.getenv(
            "INSTAGRAM_CALLBACK_URL",
            "http://localhost:8000/api/social-media/instagram/callback"
        )
    }


def is_instagram_configured() -> bool:
    """
    Check if Instagram OAuth is properly configured.

    Returns:
        True if all required environment variables are set
    """
    config = get_instagram_config()
    return bool(config["app_id"] and config["app_secret"])


def get_instagram_config_status() -> Dict[str, Any]:
    """
    Get Instagram OAuth configuration status.

    Returns:
        {
            "configured": bool,
            "app_id_set": bool,
            "app_secret_set": bool,
            "redirect_uri": str
        }
    """
    config = get_instagram_config()
    return {
        "configured": is_instagram_configured(),
        "app_id_set": bool(config["app_id"]),
        "app_secret_set": bool(config["app_secret"]),
        "redirect_uri": config["redirect_uri"]
    }


# ============================================================================
# Instagram OAuth 2.0 Implementation
# ============================================================================

class InstagramOAuth(OAuth2Base):
    """
    Instagram OAuth 2.0 implementation via Facebook Graph API.

    Inherits from OAuth2Base to eliminate code duplication while
    providing Instagram-specific configuration and behavior.
    """

    def __init__(self):
        super().__init__(platform_name="Instagram")

    def get_platform_config(self) -> Dict[str, Any]:
        """
        Get Instagram-specific OAuth configuration.

        Returns:
            Configuration dictionary for OAuth2Base
        """
        config = get_instagram_config()

        return {
            "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
            "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
            "userinfo_url": None,  # Instagram uses custom flow
            "scopes": [
                "instagram_basic",
                "instagram_content_publish",
                "pages_read_engagement",
                "pages_show_list"
            ],
            "scope_separator": ",",  # Facebook uses comma-separated scopes
            "token_content_type": "application/x-www-form-urlencoded",
            "supports_refresh": False,  # Instagram uses long-lived tokens
            "auth_extra_params": {},
            "token_extra_params": {},
            "userinfo_params": {},
            "userinfo_extra_headers": {},
            "app_id": config["app_id"],
            "app_secret": config["app_secret"],
            "redirect_uri": config["redirect_uri"]
        }


# Create singleton instance
_instagram_oauth = InstagramOAuth()


# ============================================================================
# OAuth Flow
# ============================================================================

def get_authorization_url(state: str) -> str:
    """
    Generate Facebook OAuth authorization URL for Instagram.

    The user will be redirected to Facebook to authorize Instagram permissions.

    Args:
        state: Random state string for CSRF protection

    Returns:
        Authorization URL

    Required Scopes:
        - instagram_basic: Basic profile access
        - instagram_content_publish: Publish photos and videos
        - pages_read_engagement: Read page data to find Instagram account
    """
    config = get_instagram_config()

    return _instagram_oauth.get_authorization_url(
        config["app_id"],
        config["redirect_uri"],
        state
    )


async def exchange_code_for_token(code: str) -> Optional[Dict[str, Any]]:
    """
    Exchange authorization code for short-lived access token.

    Args:
        code: Authorization code from Facebook callback

    Returns:
        {
            "access_token": "...",
            "token_type": "bearer",
            "expires_in": 3600
        }
        Or None if exchange fails
    """
    config = get_instagram_config()

    result = await _instagram_oauth.exchange_code_for_token(
        code,
        config["app_id"],
        config["app_secret"],
        config["redirect_uri"]
    )

    if result:
        logger.info("Successfully exchanged Instagram authorization code for token")
    else:
        logger.error("Failed to exchange Instagram code")

    return result


async def exchange_for_long_lived_token(short_lived_token: str) -> Optional[Dict[str, Any]]:
    """
    Exchange short-lived token for long-lived token (60 days).

    Facebook/Instagram provides long-lived tokens that last 60 days
    and can be refreshed before expiry.

    Args:
        short_lived_token: Short-lived access token (1 hour)

    Returns:
        {
            "access_token": "...",
            "token_type": "bearer",
            "expires_in": 5183944  # ~60 days in seconds
        }
        Or None if exchange fails
    """
    try:
        config = get_instagram_config()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": config["app_id"],
                    "client_secret": config["app_secret"],
                    "fb_exchange_token": short_lived_token
                },
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                logger.info("Successfully exchanged for long-lived Instagram token")
                return data
            else:
                error_data = response.json() if response.text else {}
                logger.error(f"Failed to exchange for long-lived token: {error_data}")
                return None

    except Exception as e:
        logger.error(f"Error exchanging for long-lived token: {str(e)}")
        return None


async def refresh_long_lived_token(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Refresh a long-lived access token (extends by 60 days).

    Long-lived tokens should be refreshed before they expire to maintain
    continuous access.

    Args:
        access_token: Current long-lived access token

    Returns:
        {
            "access_token": "...",
            "token_type": "bearer",
            "expires_in": 5183944  # ~60 days
        }
        Or None if refresh fails
    """
    try:
        config = get_instagram_config()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": config["app_id"],
                    "client_secret": config["app_secret"],
                    "fb_exchange_token": access_token
                },
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                logger.info("Successfully refreshed Instagram token")
                return data
            else:
                error_data = response.json() if response.text else {}
                logger.error(f"Failed to refresh Instagram token: {error_data}")
                return None

    except Exception as e:
        logger.error(f"Error refreshing Instagram token: {str(e)}")
        return None


# ============================================================================
# Facebook Pages & Instagram Account Discovery
# ============================================================================

async def get_facebook_pages(access_token: str) -> Optional[List[Dict[str, Any]]]:
    """
    Get list of Facebook Pages managed by the user.

    Each page may have an Instagram Business Account linked to it.

    Args:
        access_token: User access token

    Returns:
        List of pages:
        [
            {
                "id": "page_id",
                "name": "Page Name",
                "access_token": "page_access_token"
            }
        ]
        Or None if request fails
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.facebook.com/v18.0/me/accounts",
                params={
                    "access_token": access_token
                },
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                pages = data.get("data", [])
                logger.info(f"Found {len(pages)} Facebook Pages")
                return pages
            else:
                error_data = response.json() if response.text else {}
                logger.error(f"Failed to get Facebook Pages: {error_data}")
                return None

    except Exception as e:
        logger.error(f"Error getting Facebook Pages: {str(e)}")
        return None


async def get_instagram_account(page_id: str, page_access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get Instagram Business Account linked to a Facebook Page.

    Args:
        page_id: Facebook Page ID
        page_access_token: Page access token

    Returns:
        {
            "id": "instagram_account_id",
            "username": "instagram_username"
        }
        Or None if no Instagram account is linked
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://graph.facebook.com/v18.0/{page_id}",
                params={
                    "fields": "instagram_business_account",
                    "access_token": page_access_token
                },
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                ig_account = data.get("instagram_business_account")

                if ig_account:
                    logger.info(f"Found Instagram account: {ig_account.get('id')}")
                    return ig_account
                else:
                    logger.debug(f"No Instagram account linked to page {page_id}")
                    return None
            else:
                error_data = response.json() if response.text else {}
                logger.error(f"Failed to get Instagram account: {error_data}")
                return None

    except Exception as e:
        logger.error(f"Error getting Instagram account: {str(e)}")
        return None


async def get_instagram_user_info(instagram_account_id: str, access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get Instagram user profile information.

    Args:
        instagram_account_id: Instagram Business Account ID
        access_token: Page access token (not user token)

    Returns:
        {
            "id": "...",
            "username": "...",
            "name": "...",
            "profile_picture_url": "...",
            "biography": "...",
            "followers_count": 1000,
            "follows_count": 500,
            "media_count": 250
        }
        Or None if request fails
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://graph.facebook.com/v18.0/{instagram_account_id}",
                params={
                    "fields": "id,username,name,profile_picture_url,biography,followers_count,follows_count,media_count",
                    "access_token": access_token
                },
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Retrieved Instagram profile: @{data.get('username')}")
                return data
            else:
                error_data = response.json() if response.text else {}
                logger.error(f"Failed to get Instagram user info: {error_data}")
                return None

    except Exception as e:
        logger.error(f"Error getting Instagram user info: {str(e)}")
        return None


# ============================================================================
# Token Validation
# ============================================================================

async def validate_access_token(access_token: str) -> bool:
    """
    Validate if an access token is still valid.

    Args:
        access_token: Access token to validate

    Returns:
        True if token is valid, False otherwise
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.facebook.com/v18.0/me",
                params={
                    "fields": "id",
                    "access_token": access_token
                },
                timeout=10.0
            )

            return response.status_code == 200

    except Exception as e:
        logger.error(f"Error validating access token: {str(e)}")
        return False


async def get_token_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get information about an access token (expiry, scopes, etc).

    Args:
        access_token: Access token to inspect

    Returns:
        {
            "app_id": "...",
            "type": "USER",
            "application": "...",
            "expires_at": 1234567890,
            "is_valid": true,
            "scopes": ["instagram_basic", "instagram_content_publish"]
        }
        Or None if request fails
    """
    try:
        config = get_instagram_config()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.facebook.com/v18.0/debug_token",
                params={
                    "input_token": access_token,
                    "access_token": f"{config['app_id']}|{config['app_secret']}"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data")
            else:
                error_data = response.json() if response.text else {}
                logger.error(f"Failed to get token info: {error_data}")
                return None

    except Exception as e:
        logger.error(f"Error getting token info: {str(e)}")
        return None
