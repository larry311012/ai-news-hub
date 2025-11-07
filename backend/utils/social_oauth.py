"""
Social Media OAuth Utilities for LinkedIn, Twitter, and Threads

This module provides OAuth 2.0 flow implementations for social media platforms:
- LinkedIn OAuth 2.0
- Twitter/X OAuth 2.0
- Threads (Meta) OAuth 2.0
"""
import os
import logging
import httpx
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# LinkedIn OAuth Configuration
# ============================================================================
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv(
    "LINKEDIN_REDIRECT_URI", "http://localhost:8000/api/social-media/linkedin/callback"
)

# LinkedIn API endpoints
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_PROFILE_URL = "https://api.linkedin.com/v2/me"

# LinkedIn required scopes
LINKEDIN_SCOPES = [
    "openid",
    "profile",
    "email",
    "w_member_social",  # Permission to post on behalf of user
]


def get_linkedin_auth_url(state: str) -> str:
    """
    Generate LinkedIn OAuth authorization URL.

    Args:
        state: Random state parameter for CSRF protection

    Returns:
        Authorization URL string

    Raises:
        ValueError: If LinkedIn OAuth not configured
    """
    if not LINKEDIN_CLIENT_ID:
        raise ValueError("LinkedIn OAuth not configured - missing LINKEDIN_CLIENT_ID")

    params = {
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "state": state,
        "scope": " ".join(LINKEDIN_SCOPES),
    }

    auth_url = f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"
    logger.info("Generated LinkedIn OAuth authorization URL")
    return auth_url


async def exchange_linkedin_code(code: str) -> Optional[Dict[str, Any]]:
    """
    Exchange LinkedIn authorization code for access token.

    Args:
        code: Authorization code from OAuth callback

    Returns:
        Dictionary with access_token, expires_in, scope, or None on error
    """
    try:
        async with httpx.AsyncClient() as client:
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET,
                "redirect_uri": LINKEDIN_REDIRECT_URI,
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            response = await client.post(LINKEDIN_TOKEN_URL, data=token_data, headers=headers)
            response.raise_for_status()
            tokens = response.json()

            logger.info("Successfully exchanged LinkedIn authorization code")
            return tokens

    except Exception as e:
        logger.error(f"Error exchanging LinkedIn code: {str(e)}")
        return None


async def get_linkedin_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get LinkedIn user information using access token.

    Args:
        access_token: LinkedIn access token

    Returns:
        Dictionary with user info (sub, name, email, picture) or None on error
    """
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

            # Get basic profile info
            userinfo_response = await client.get(LINKEDIN_USERINFO_URL, headers=headers)
            userinfo_response.raise_for_status()
            user_info = userinfo_response.json()

            logger.info(f"Retrieved LinkedIn user info for: {user_info.get('email')}")
            return user_info

    except Exception as e:
        logger.error(f"Error getting LinkedIn user info: {str(e)}")
        return None


async def refresh_linkedin_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """
    Refresh LinkedIn access token using refresh token.

    Note: LinkedIn OAuth 2.0 tokens typically expire after 60 days.
    As of 2024, LinkedIn does not provide refresh tokens in standard OAuth flow.

    Args:
        refresh_token: LinkedIn refresh token

    Returns:
        Dictionary with new access_token, expires_in, or None on error
    """
    try:
        async with httpx.AsyncClient() as client:
            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET,
            }

            response = await client.post(LINKEDIN_TOKEN_URL, data=token_data)
            response.raise_for_status()
            tokens = response.json()

            logger.info("Successfully refreshed LinkedIn token")
            return tokens

    except Exception as e:
        logger.error(f"Error refreshing LinkedIn token: {str(e)}")
        return None


# ============================================================================
# Twitter/X OAuth Configuration
# ============================================================================
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
TWITTER_REDIRECT_URI = os.getenv(
    "TWITTER_REDIRECT_URI", "http://localhost:8000/api/social-media/twitter/callback"
)

# Twitter API v2 endpoints
TWITTER_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TWITTER_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
TWITTER_USERINFO_URL = "https://api.twitter.com/2/users/me"
TWITTER_REVOKE_URL = "https://api.twitter.com/2/oauth2/revoke"

# Twitter required scopes
TWITTER_SCOPES = [
    "tweet.read",
    "tweet.write",
    "users.read",
    "offline.access",  # Required for refresh tokens
]


def get_twitter_auth_url(state: str, code_challenge: str) -> str:
    """
    Generate Twitter OAuth 2.0 authorization URL with PKCE.

    Twitter requires PKCE (Proof Key for Code Exchange) for OAuth 2.0.

    Args:
        state: Random state parameter for CSRF protection
        code_challenge: PKCE code challenge (SHA-256 hash of code_verifier)

    Returns:
        Authorization URL string

    Raises:
        ValueError: If Twitter OAuth not configured
    """
    if not TWITTER_CLIENT_ID:
        raise ValueError("Twitter OAuth not configured - missing TWITTER_CLIENT_ID")

    params = {
        "response_type": "code",
        "client_id": TWITTER_CLIENT_ID,
        "redirect_uri": TWITTER_REDIRECT_URI,
        "state": state,
        "scope": " ".join(TWITTER_SCOPES),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    auth_url = f"{TWITTER_AUTH_URL}?{urlencode(params)}"
    logger.info("Generated Twitter OAuth authorization URL with PKCE")
    return auth_url


async def exchange_twitter_code(code: str, code_verifier: str) -> Optional[Dict[str, Any]]:
    """
    Exchange Twitter authorization code for access token with PKCE.

    Args:
        code: Authorization code from OAuth callback
        code_verifier: PKCE code verifier (original random string)

    Returns:
        Dictionary with access_token, refresh_token, expires_in, scope, or None on error
    """
    try:
        async with httpx.AsyncClient() as client:
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": TWITTER_CLIENT_ID,
                "redirect_uri": TWITTER_REDIRECT_URI,
                "code_verifier": code_verifier,
            }

            # Twitter requires Basic Auth for token endpoint
            auth = (TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET)

            response = await client.post(TWITTER_TOKEN_URL, data=token_data, auth=auth)
            response.raise_for_status()
            tokens = response.json()

            logger.info("Successfully exchanged Twitter authorization code")
            return tokens

    except Exception as e:
        logger.error(f"Error exchanging Twitter code: {str(e)}")
        return None


async def get_twitter_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get Twitter user information using access token.

    Args:
        access_token: Twitter access token

    Returns:
        Dictionary with user info (id, username, name) or None on error
    """
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

            params = {"user.fields": "id,username,name,profile_image_url"}

            response = await client.get(TWITTER_USERINFO_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            user_info = data.get("data", {})
            logger.info(f"Retrieved Twitter user info for: @{user_info.get('username')}")
            return user_info

    except Exception as e:
        logger.error(f"Error getting Twitter user info: {str(e)}")
        return None


async def refresh_twitter_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """
    Refresh Twitter access token using refresh token.

    Args:
        refresh_token: Twitter refresh token

    Returns:
        Dictionary with new access_token, refresh_token, expires_in, or None on error
    """
    try:
        async with httpx.AsyncClient() as client:
            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": TWITTER_CLIENT_ID,
            }

            # Twitter requires Basic Auth
            auth = (TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET)

            response = await client.post(TWITTER_TOKEN_URL, data=token_data, auth=auth)
            response.raise_for_status()
            tokens = response.json()

            logger.info("Successfully refreshed Twitter token")
            return tokens

    except Exception as e:
        logger.error(f"Error refreshing Twitter token: {str(e)}")
        return None


# ============================================================================
# Threads (Meta) OAuth Configuration
# ============================================================================
THREADS_CLIENT_ID = os.getenv("THREADS_CLIENT_ID")
THREADS_CLIENT_SECRET = os.getenv("THREADS_CLIENT_SECRET")
THREADS_REDIRECT_URI = os.getenv(
    "THREADS_REDIRECT_URI", "http://localhost:8000/api/social-media/threads/callback"
)

# Threads API endpoints (uses Instagram Graph API)
THREADS_AUTH_URL = "https://threads.net/oauth/authorize"
THREADS_TOKEN_URL = "https://graph.threads.net/oauth/access_token"
THREADS_LONG_LIVED_TOKEN_URL = "https://graph.threads.net/access_token"
THREADS_USERINFO_URL = "https://graph.threads.net/v1.0/me"

# Threads required scopes
THREADS_SCOPES = ["threads_basic", "threads_content_publish"]


def get_threads_auth_url(state: str) -> str:
    """
    Generate Threads OAuth authorization URL.

    Args:
        state: Random state parameter for CSRF protection

    Returns:
        Authorization URL string

    Raises:
        ValueError: If Threads OAuth not configured
    """
    if not THREADS_CLIENT_ID:
        raise ValueError("Threads OAuth not configured - missing THREADS_CLIENT_ID")

    params = {
        "client_id": THREADS_CLIENT_ID,
        "redirect_uri": THREADS_REDIRECT_URI,
        "scope": ",".join(THREADS_SCOPES),
        "response_type": "code",
        "state": state,
    }

    auth_url = f"{THREADS_AUTH_URL}?{urlencode(params)}"
    logger.info("Generated Threads OAuth authorization URL")
    return auth_url


async def exchange_threads_code(code: str) -> Optional[Dict[str, Any]]:
    """
    Exchange Threads authorization code for access token.

    Returns a short-lived token (60 days). Use exchange_threads_long_lived_token
    to get a long-lived token (60 days, refreshable).

    Args:
        code: Authorization code from OAuth callback

    Returns:
        Dictionary with access_token, user_id, or None on error
    """
    try:
        async with httpx.AsyncClient() as client:
            token_data = {
                "client_id": THREADS_CLIENT_ID,
                "client_secret": THREADS_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": THREADS_REDIRECT_URI,
                "code": code,
            }

            response = await client.post(THREADS_TOKEN_URL, data=token_data)
            response.raise_for_status()
            tokens = response.json()

            logger.info("Successfully exchanged Threads authorization code")
            return tokens

    except Exception as e:
        logger.error(f"Error exchanging Threads code: {str(e)}")
        return None


async def exchange_threads_long_lived_token(short_lived_token: str) -> Optional[Dict[str, Any]]:
    """
    Exchange Threads short-lived token for long-lived token.

    Long-lived tokens last 60 days and can be refreshed.

    Args:
        short_lived_token: Threads short-lived access token

    Returns:
        Dictionary with access_token, token_type, expires_in, or None on error
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "grant_type": "th_exchange_token",
                "client_secret": THREADS_CLIENT_SECRET,
                "access_token": short_lived_token,
            }

            response = await client.get(THREADS_LONG_LIVED_TOKEN_URL, params=params)
            response.raise_for_status()
            tokens = response.json()

            logger.info("Successfully exchanged Threads long-lived token")
            return tokens

    except Exception as e:
        logger.error(f"Error exchanging Threads long-lived token: {str(e)}")
        return None


async def get_threads_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get Threads user information using access token.

    Args:
        access_token: Threads access token

    Returns:
        Dictionary with user info (id, username, name, threads_profile_picture_url) or None on error
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "fields": "id,username,name,threads_profile_picture_url",
                "access_token": access_token,
            }

            response = await client.get(THREADS_USERINFO_URL, params=params)
            response.raise_for_status()
            user_info = response.json()

            logger.info(f"Retrieved Threads user info for: @{user_info.get('username')}")
            return user_info

    except Exception as e:
        logger.error(f"Error getting Threads user info: {str(e)}")
        return None


async def refresh_threads_token(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Refresh Threads long-lived token.

    Long-lived tokens should be refreshed before they expire (60 days).

    Args:
        access_token: Current Threads access token

    Returns:
        Dictionary with new access_token, token_type, expires_in, or None on error
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {"grant_type": "th_refresh_token", "access_token": access_token}

            response = await client.get(THREADS_LONG_LIVED_TOKEN_URL, params=params)
            response.raise_for_status()
            tokens = response.json()

            logger.info("Successfully refreshed Threads token")
            return tokens

    except Exception as e:
        logger.error(f"Error refreshing Threads token: {str(e)}")
        return None


# ============================================================================
# PKCE Utilities for Twitter
# ============================================================================
import secrets
import hashlib
import base64


def generate_pkce_pair() -> Tuple[str, str]:
    """
    Generate PKCE code_verifier and code_challenge pair.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate random code_verifier (43-128 characters)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8")
    code_verifier = code_verifier.rstrip("=")  # Remove padding

    # Generate code_challenge (SHA-256 hash of code_verifier)
    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
    code_challenge = code_challenge.rstrip("=")  # Remove padding

    return code_verifier, code_challenge


# ============================================================================
# Token Validation
# ============================================================================


def is_token_expired(expires_at: Optional[datetime]) -> bool:
    """
    Check if a token is expired.

    Args:
        expires_at: Token expiration datetime

    Returns:
        True if token is expired or about to expire (within 5 minutes)
    """
    if not expires_at:
        return False

    # Consider token expired if it expires within 5 minutes
    buffer_time = timedelta(minutes=5)
    return datetime.utcnow() + buffer_time >= expires_at


def calculate_token_expiry(expires_in: int) -> datetime:
    """
    Calculate token expiration datetime from expires_in seconds.

    Args:
        expires_in: Seconds until token expires

    Returns:
        Expiration datetime
    """
    return datetime.utcnow() + timedelta(seconds=expires_in)
