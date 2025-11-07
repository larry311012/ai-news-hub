"""
Twitter OAuth 1.0a Endpoints - Centralized Authentication

This module provides Twitter OAuth 1.0a endpoints for centralized authentication.
These endpoints work alongside the existing OAuth 2.0 endpoints to provide
a migration path to centralized Twitter app authentication.

Usage:
- New connections: Use /twitter-oauth1/connect
- Existing OAuth 2.0 connections: Continue to work
- Gradual migration: Users can reconnect using OAuth 1.0a

To use in main.py:
```python
from api.social_media_twitter_oauth1 import router as twitter_oauth1_router
app.include_router(twitter_oauth1_router, prefix="/api/social-media", tags=["social-media"])
```
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging

from database import get_db, User
from database_social_media import SocialMediaConnection
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.social_connection_manager import SocialConnectionManager
from utils.twitter_oauth1 import (
    get_request_token,
    get_authorization_url,
    get_access_token,
    get_user_info,
    is_oauth1_configured,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Temporary storage for request token secrets
# In production, use Redis with TTL
# Key: oauth_token, Value: dict with oauth_token_secret and user_id
request_token_storage = {}


# ============================================================================
# Twitter OAuth 1.0a Endpoints (Centralized)
# ============================================================================


@router.get("/twitter-oauth1/connect")
async def twitter_oauth1_connect(
    request: Request,
    return_url: Optional[str] = Query(None, description="Frontend URL to redirect after OAuth"),
    user: User = Depends(get_current_user_dependency),
):
    """
    Initiate Twitter OAuth 1.0a flow (Centralized).

    This endpoint uses a centralized Twitter app for authentication,
    eliminating the need for users to create their own Twitter apps.

    Flow:
    1. Request temporary credentials (request token) from Twitter
    2. Store request token secret temporarily
    3. Return authorization URL to redirect user

    Returns:
        {
            "success": true,
            "authorization_url": "https://api.twitter.com/oauth/authorize?oauth_token=...",
            "platform": "twitter",
            "oauth_version": "1.0a"
        }
    """
    try:
        # Check if OAuth 1.0a is configured
        if not is_oauth1_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Twitter OAuth 1.0a is not configured on this server. Please set TWITTER_API_KEY and TWITTER_API_SECRET.",
            )

        # Step 1: Get request token from Twitter
        request_token_data = await get_request_token()

        if not request_token_data:
            logger.error("Failed to obtain request token from Twitter")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate Twitter OAuth. Please try again.",
            )

        oauth_token = request_token_data["oauth_token"]
        oauth_token_secret = request_token_data["oauth_token_secret"]

        # Step 2: Store request token secret and user context
        # Note: In production, use Redis with 10-minute TTL
        request_token_storage[oauth_token] = {
            "oauth_token_secret": oauth_token_secret,
            "user_id": user.id,
            "return_url": return_url,
            "created_at": datetime.utcnow(),
        }

        # Clean up old request tokens (older than 10 minutes)
        current_time = datetime.utcnow()
        expired_tokens = [
            token
            for token, data in request_token_storage.items()
            if (current_time - data["created_at"]).total_seconds() > 600
        ]
        for token in expired_tokens:
            del request_token_storage[token]
            logger.debug(f"Cleaned up expired request token: {token[:10]}...")

        # Step 3: Generate authorization URL
        auth_url = get_authorization_url(oauth_token)

        logger.info(f"Generated Twitter OAuth 1.0a authorization URL for user {user.id}")

        return {
            "success": True,
            "authorization_url": auth_url,
            "platform": "twitter",
            "oauth_version": "1.0a",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating Twitter OAuth 1.0a URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while initiating OAuth",
        )


@router.get("/twitter-oauth1/callback")
async def twitter_oauth1_callback(
    oauth_token: str = Query(..., description="OAuth token from Twitter"),
    oauth_verifier: Optional[str] = Query(None, description="OAuth verifier from Twitter"),
    denied: Optional[str] = Query(None, description="Present if user denied access"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Handle Twitter OAuth 1.0a callback (Centralized).

    Twitter redirects here after user authorizes the app.

    Flow:
    1. Retrieve stored request token secret
    2. Exchange request token + verifier for access token
    3. Get user info from Twitter
    4. Store connection in database
    5. Redirect back to frontend

    Query Parameters:
        oauth_token: Request token from step 1
        oauth_verifier: Verifier provided by Twitter after user authorization
        denied: Present if user denied access

    Returns:
        Redirect to frontend with success/error parameters
    """
    try:
        # Handle user denial
        if denied:
            logger.warning(f"User denied Twitter authorization: {denied}")
            # Try to get return_url from storage
            stored_data = request_token_storage.get(oauth_token, {})
            return_url = stored_data.get("return_url")

            # Clean up
            if oauth_token in request_token_storage:
                del request_token_storage[oauth_token]

            if return_url:
                error_url = f"{return_url}?error=user_denied&platform=twitter"
                return RedirectResponse(url=error_url)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User denied Twitter authorization"
            )

        # Step 1: Retrieve stored request token secret
        if oauth_token not in request_token_storage:
            logger.warning(f"Request token not found in storage: {oauth_token[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth token. Please try again.",
            )

        stored_data = request_token_storage[oauth_token]
        oauth_token_secret = stored_data["oauth_token_secret"]
        user_id = stored_data["user_id"]
        return_url = stored_data.get("return_url")

        # Clean up (one-time use)
        del request_token_storage[oauth_token]

        # Validate oauth_verifier is provided
        if not oauth_verifier:
            logger.error("OAuth verifier not provided")
            if return_url:
                error_url = f"{return_url}?error=oauth_failed&platform=twitter"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth verifier is required"
            )

        # Step 2: Exchange for access token
        access_token_data = await get_access_token(
            oauth_token=oauth_token,
            oauth_token_secret=oauth_token_secret,
            oauth_verifier=oauth_verifier,
        )

        if not access_token_data:
            logger.error("Failed to exchange Twitter request token for access token")
            if return_url:
                error_url = f"{return_url}?error=oauth_failed&platform=twitter"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to authenticate with Twitter",
            )

        access_token = access_token_data["oauth_token"]
        access_token_secret = access_token_data["oauth_token_secret"]
        twitter_user_id = access_token_data["user_id"]
        twitter_username = access_token_data["screen_name"]

        # Step 3: Get detailed user info
        user_info = await get_user_info(access_token, access_token_secret)

        if not user_info:
            logger.warning("Failed to get Twitter user info, using basic data from access token")
            # Fallback to basic data from access token response
            user_info = {
                "id": twitter_user_id,
                "username": twitter_username,
                "name": twitter_username,
            }

        # Step 4: Store connection in database
        manager = SocialConnectionManager(db)
        connection = manager.create_connection(
            user_id=user_id,
            platform="twitter",
            access_token=access_token,
            # Note: In OAuth 1.0a, we store access_token_secret in the refresh_token field
            # This is a clever reuse of the existing schema
            refresh_token=access_token_secret,
            expires_in=None,  # OAuth 1.0a tokens don't expire
            scope=None,  # OAuth 1.0a doesn't use scopes
            platform_user_id=user_info.get("id"),
            platform_username=user_info.get("username"),
            metadata=user_info,
        )

        logger.info(
            f"Twitter OAuth 1.0a connection created for user {user_id} (@{user_info.get('username')})"
        )

        # Step 5: Redirect to frontend
        if return_url:
            success_url = f"{return_url}?success=true&platform=twitter&username={user_info.get('username', '')}&oauth_version=1.0a"
            return RedirectResponse(url=success_url)

        return {
            "success": True,
            "message": "Twitter account connected successfully (OAuth 1.0a)",
            "platform": "twitter",
            "username": user_info.get("username"),
            "oauth_version": "1.0a",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Twitter OAuth 1.0a callback: {str(e)}")
        if "return_url" in locals() and return_url:
            error_url = f"{return_url}?error=server_error&platform=twitter"
            return RedirectResponse(url=error_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during OAuth authentication",
        )


@router.get("/twitter-oauth1/status")
async def twitter_oauth1_status():
    """
    Get Twitter OAuth 1.0a configuration status.

    Returns:
        {
            "configured": true/false,
            "api_key_set": true/false,
            "api_secret_set": true/false,
            "oauth_version": "1.0a"
        }
    """
    from utils.twitter_oauth1 import get_oauth_config_status

    return get_oauth_config_status()


# ============================================================================
# Helper Endpoint for Debugging (Development Only)
# ============================================================================


@router.get("/twitter-oauth1/debug/storage")
async def twitter_oauth1_debug_storage(user: User = Depends(get_current_user_dependency)):
    """
    Debug endpoint to view request token storage.

    WARNING: Remove this endpoint in production!

    Returns:
        Number of stored request tokens and their ages
    """
    current_time = datetime.utcnow()
    storage_info = []

    for token, data in request_token_storage.items():
        age_seconds = (current_time - data["created_at"]).total_seconds()
        storage_info.append(
            {
                "token_prefix": token[:10] + "...",
                "user_id": data["user_id"],
                "age_seconds": age_seconds,
                "expires_in_seconds": 600 - age_seconds,
            }
        )

    return {"total_tokens": len(request_token_storage), "tokens": storage_info}
