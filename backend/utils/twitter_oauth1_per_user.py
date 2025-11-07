"""
Twitter OAuth 1.0a - Per-User Credentials Support

This module extends the existing Twitter OAuth 1.0a implementation to support
per-user credentials. It checks for user-provided credentials first, then falls
back to centralized admin credentials.

Key Features:
- Checks for user's own Twitter API credentials first
- Falls back to admin credentials if user hasn't set up their own
- Uses same OAuth 1.0a flow with different credentials
- Transparent to the frontend - same API endpoints

Usage:
    from utils.twitter_oauth1_per_user import (
        get_user_or_admin_credentials,
        get_request_token_with_user_creds,
        get_access_token_with_user_creds
    )

    # Get credentials (user's first, then admin's)
    creds = get_user_or_admin_credentials(db, user_id)

    # Use credentials for OAuth flow
    request_token = await get_request_token_with_user_creds(creds)
"""

import logging
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
import hmac
import hashlib
import base64
import time
import secrets
from urllib.parse import quote, urlencode
import httpx

from utils.user_oauth_credential_manager import UserOAuthCredentialManager
from utils.oauth_credential_manager import OAuthCredentialManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_user_or_admin_credentials(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get Twitter OAuth credentials with fallback logic.

    Priority:
    1. User's own credentials (from user_oauth_credentials table)
    2. Admin centralized credentials (from oauth_platform_credentials or .env)

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Dictionary with credentials:
        {
            "api_key": "...",
            "api_secret": "...",
            "callback_url": "...",
            "source": "user" or "admin",
            "oauth_version": "1.0a"
        }

        None if no credentials found
    """
    try:
        # Try user's credentials first
        user_manager = UserOAuthCredentialManager(db, user_id)
        user_creds = user_manager.get_credentials("twitter")

        if user_creds and user_creds.get("api_key") and user_creds.get("api_secret"):
            logger.info(f"Using user {user_id}'s own Twitter credentials")
            return {
                "api_key": user_creds["api_key"],
                "api_secret": user_creds["api_secret"],
                "callback_url": user_creds.get("callback_url", "http://localhost:8000/api/social-media/twitter-oauth1/callback"),
                "source": "user",
                "oauth_version": "1.0a"
            }

        # Fall back to admin credentials
        admin_manager = OAuthCredentialManager(db)
        admin_creds = admin_manager.get_credentials("twitter")

        if admin_creds and admin_creds.get("api_key") and admin_creds.get("api_secret"):
            logger.info(f"Using admin credentials for user {user_id} (user has no own credentials)")
            return {
                "api_key": admin_creds["api_key"],
                "api_secret": admin_creds["api_secret"],
                "callback_url": admin_creds.get("callback_url", "http://localhost:8000/api/social-media/twitter-oauth1/callback"),
                "source": "admin",
                "oauth_version": "1.0a"
            }

        logger.warning(f"No Twitter credentials found for user {user_id} (neither user nor admin)")
        return None

    except Exception as e:
        logger.error(f"Error getting Twitter credentials for user {user_id}: {str(e)}")
        return None


def generate_oauth_signature(
    method: str,
    url: str,
    params: Dict[str, str],
    consumer_secret: str,
    token_secret: str = ""
) -> str:
    """
    Generate OAuth 1.0a signature.

    Args:
        method: HTTP method (GET, POST)
        url: Request URL
        params: OAuth parameters
        consumer_secret: Consumer secret (API secret)
        token_secret: Token secret (empty for request token)

    Returns:
        Base64-encoded HMAC-SHA1 signature
    """
    # Sort parameters
    sorted_params = sorted(params.items())

    # Create parameter string
    param_string = "&".join([f"{quote(k, safe='')}={quote(v, safe='')}" for k, v in sorted_params])

    # Create signature base string
    signature_base = f"{method.upper()}&{quote(url, safe='')}&{quote(param_string, safe='')}"

    # Create signing key
    signing_key = f"{quote(consumer_secret, safe='')}&{quote(token_secret, safe='')}"

    # Generate signature
    signature = hmac.new(
        signing_key.encode('utf-8'),
        signature_base.encode('utf-8'),
        hashlib.sha1
    ).digest()

    return base64.b64encode(signature).decode('utf-8')


async def get_request_token_with_user_creds(credentials: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Get OAuth request token using provided credentials (user or admin).

    Args:
        credentials: OAuth credentials dictionary with api_key, api_secret, callback_url

    Returns:
        Dictionary with oauth_token and oauth_token_secret, or None if failed
    """
    try:
        url = "https://api.twitter.com/oauth/request_token"

        # OAuth parameters
        oauth_params = {
            "oauth_callback": credentials["callback_url"],
            "oauth_consumer_key": credentials["api_key"],
            "oauth_nonce": secrets.token_hex(16),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_version": "1.0"
        }

        # Generate signature
        signature = generate_oauth_signature(
            method="POST",
            url=url,
            params=oauth_params,
            consumer_secret=credentials["api_secret"],
            token_secret=""
        )

        oauth_params["oauth_signature"] = signature

        # Build Authorization header
        auth_header = "OAuth " + ", ".join([
            f'{quote(k, safe="")}="{quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        ])

        # Make request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={"Authorization": auth_header},
                timeout=10.0
            )

            if response.status_code != 200:
                logger.error(f"Failed to get request token: {response.status_code} - {response.text}")
                return None

            # Parse response
            response_params = dict(param.split('=') for param in response.text.split('&'))

            if 'oauth_token' not in response_params or 'oauth_token_secret' not in response_params:
                logger.error(f"Invalid response from Twitter: {response.text}")
                return None

            logger.info(f"Successfully obtained request token (source: {credentials.get('source', 'unknown')})")
            return response_params

    except Exception as e:
        logger.error(f"Error getting request token: {str(e)}")
        return None


async def get_access_token_with_user_creds(
    credentials: Dict[str, Any],
    oauth_token: str,
    oauth_token_secret: str,
    oauth_verifier: str
) -> Optional[Dict[str, str]]:
    """
    Exchange request token for access token using provided credentials.

    Args:
        credentials: OAuth credentials dictionary
        oauth_token: OAuth token from request token
        oauth_token_secret: OAuth token secret from request token
        oauth_verifier: OAuth verifier from Twitter callback

    Returns:
        Dictionary with oauth_token, oauth_token_secret, user_id, screen_name, or None if failed
    """
    try:
        url = "https://api.twitter.com/oauth/access_token"

        # OAuth parameters
        oauth_params = {
            "oauth_consumer_key": credentials["api_key"],
            "oauth_nonce": secrets.token_hex(16),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": oauth_token,
            "oauth_verifier": oauth_verifier,
            "oauth_version": "1.0"
        }

        # Generate signature
        signature = generate_oauth_signature(
            method="POST",
            url=url,
            params=oauth_params,
            consumer_secret=credentials["api_secret"],
            token_secret=oauth_token_secret
        )

        oauth_params["oauth_signature"] = signature

        # Build Authorization header
        auth_header = "OAuth " + ", ".join([
            f'{quote(k, safe="")}="{quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        ])

        # Make request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={"Authorization": auth_header},
                timeout=10.0
            )

            if response.status_code != 200:
                logger.error(f"Failed to get access token: {response.status_code} - {response.text}")
                return None

            # Parse response
            response_params = dict(param.split('=') for param in response.text.split('&'))

            required_fields = ['oauth_token', 'oauth_token_secret', 'user_id', 'screen_name']
            if not all(field in response_params for field in required_fields):
                logger.error(f"Invalid response from Twitter: {response.text}")
                return None

            logger.info(f"Successfully obtained access token for @{response_params['screen_name']} (source: {credentials.get('source', 'unknown')})")
            return response_params

    except Exception as e:
        logger.error(f"Error getting access token: {str(e)}")
        return None


async def get_user_info_with_user_creds(
    credentials: Dict[str, Any],
    access_token: str,
    access_token_secret: str
) -> Optional[Dict[str, Any]]:
    """
    Get Twitter user info using provided credentials.

    Args:
        credentials: OAuth credentials dictionary
        access_token: OAuth access token
        access_token_secret: OAuth access token secret

    Returns:
        Dictionary with user info, or None if failed
    """
    try:
        url = "https://api.twitter.com/1.1/account/verify_credentials.json"

        # OAuth parameters
        oauth_params = {
            "oauth_consumer_key": credentials["api_key"],
            "oauth_nonce": secrets.token_hex(16),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": access_token,
            "oauth_version": "1.0"
        }

        # Generate signature
        signature = generate_oauth_signature(
            method="GET",
            url=url,
            params=oauth_params,
            consumer_secret=credentials["api_secret"],
            token_secret=access_token_secret
        )

        oauth_params["oauth_signature"] = signature

        # Build Authorization header
        auth_header = "OAuth " + ", ".join([
            f'{quote(k, safe="")}="{quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        ])

        # Make request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": auth_header},
                timeout=10.0
            )

            if response.status_code != 200:
                logger.error(f"Failed to get user info: {response.status_code} - {response.text}")
                return None

            user_data = response.json()

            return {
                "id": str(user_data.get("id_str", user_data.get("id"))),
                "username": user_data.get("screen_name"),
                "name": user_data.get("name"),
                "profile_image_url": user_data.get("profile_image_url_https"),
                "description": user_data.get("description"),
                "followers_count": user_data.get("followers_count"),
                "following_count": user_data.get("friends_count"),
                "verified": user_data.get("verified", False)
            }

    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        return None


def check_user_has_credentials(db: Session, user_id: int) -> Tuple[bool, Optional[str]]:
    """
    Check if user has set up their own OAuth credentials.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Tuple of (has_credentials: bool, source: Optional[str])
        source can be "user", "admin", or None
    """
    try:
        # Check user credentials
        user_manager = UserOAuthCredentialManager(db, user_id)
        user_creds = user_manager.get_credentials("twitter")

        if user_creds and user_creds.get("api_key") and user_creds.get("api_secret"):
            return True, "user"

        # Check admin credentials
        admin_manager = OAuthCredentialManager(db)
        admin_creds = admin_manager.get_credentials("twitter")

        if admin_creds and admin_creds.get("api_key") and admin_creds.get("api_secret"):
            return True, "admin"

        return False, None

    except Exception as e:
        logger.error(f"Error checking credentials for user {user_id}: {str(e)}")
        return False, None
