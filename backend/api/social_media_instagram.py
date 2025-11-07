"""
Instagram OAuth 2.0 Endpoints - Business Account Publishing

This module provides Instagram OAuth 2.0 endpoints for connecting Instagram
Business accounts via Facebook Graph API for publishing content.

Features:
- OAuth 2.0 authorization flow via Facebook
- Long-lived token management (60-day tokens)
- Encrypted token storage
- CSRF protection via state parameter
- Instagram Business Account linking
- Support for image + caption publishing

Requirements:
- Instagram Business Account (not personal)
- Instagram Business Account linked to Facebook Page
- Facebook App with Instagram Basic Display + Instagram Graph API

Usage in main.py:
```python
from api.social_media_instagram import router as instagram_router
app.include_router(instagram_router, prefix="/api/social-media", tags=["social-media"])
```

OAuth Flow:
1. User clicks "Connect Instagram"
2. GET /instagram/connect -> Returns authorization URL
3. User authorizes on Facebook
4. Facebook redirects to /instagram/callback
5. Exchange code for access token
6. Get Facebook Pages
7. Find Instagram Business Account linked to page
8. Store encrypted tokens in database
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging
import secrets

from database import get_db, User
from database_social_media import SocialMediaConnection
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.social_connection_manager import SocialConnectionManager
from utils.instagram_oauth import (
    get_authorization_url,
    exchange_code_for_token,
    exchange_for_long_lived_token,
    get_facebook_pages,
    get_instagram_account,
    get_instagram_user_info,
    is_instagram_configured,
    get_instagram_config_status
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Temporary storage for OAuth state
# In production, use Redis with TTL
# Key: state, Value: dict with user_id and return_url
oauth_state_storage = {}


# ============================================================================
# Instagram OAuth 2.0 Endpoints
# ============================================================================

@router.get("/instagram/connect")
async def instagram_connect(
    request: Request,
    return_url: Optional[str] = Query(None, description="Frontend URL to redirect after OAuth"),
    user: User = Depends(get_current_user_dependency)
):
    """
    Initiate Instagram OAuth 2.0 flow via Facebook.

    This endpoint generates an authorization URL and redirects the user
    to Facebook to authorize the application. The user must have an
    Instagram Business Account linked to a Facebook Page.

    Flow:
    1. Generate random state for CSRF protection
    2. Store state with user context
    3. Generate authorization URL
    4. Return URL to frontend

    Query Parameters:
        return_url: Optional URL to redirect to after OAuth completion

    Returns:
        {
            "success": true,
            "authorization_url": "https://www.facebook.com/v18.0/dialog/oauth?...",
            "platform": "instagram",
            "oauth_version": "2.0",
            "requirements": {
                "business_account": true,
                "facebook_page": true
            }
        }

    Raises:
        HTTPException 503: Instagram OAuth not configured
        HTTPException 500: Error generating authorization URL
    """
    try:
        # Check if Instagram OAuth is configured
        if not is_instagram_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Instagram OAuth is not configured on this server. Please set INSTAGRAM_APP_ID and INSTAGRAM_APP_SECRET."
            )

        # Generate random state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state with user context
        # Note: In production, use Redis with 10-minute TTL
        oauth_state_storage[state] = {
            "user_id": user.id,
            "return_url": return_url,
            "created_at": datetime.utcnow()
        }

        # Clean up old states (older than 10 minutes)
        current_time = datetime.utcnow()
        expired_states = [
            s for s, data in oauth_state_storage.items()
            if (current_time - data['created_at']).total_seconds() > 600
        ]
        for state_key in expired_states:
            del oauth_state_storage[state_key]
            logger.debug(f"Cleaned up expired OAuth state: {state_key[:10]}...")

        # Generate authorization URL
        auth_url = get_authorization_url(state)

        logger.info(f"Generated Instagram OAuth authorization URL for user {user.id}")

        return {
            "success": True,
            "authorization_url": auth_url,
            "platform": "instagram",
            "oauth_version": "2.0",
            "requirements": {
                "business_account": True,
                "facebook_page": True,
                "setup_guide": "https://help.instagram.com/502981923235522"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating Instagram OAuth URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while initiating OAuth"
        )


@router.get("/instagram/callback")
async def instagram_callback(
    code: Optional[str] = Query(None, description="Authorization code from Facebook"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    error: Optional[str] = Query(None, description="Error code if authorization failed"),
    error_reason: Optional[str] = Query(None, description="Error reason if authorization failed"),
    error_description: Optional[str] = Query(None, description="Error description if authorization failed"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Handle Instagram OAuth 2.0 callback.

    Facebook redirects here after user authorizes the app.

    Flow:
    1. Validate state parameter (CSRF protection)
    2. Exchange authorization code for short-lived token
    3. Exchange short-lived token for long-lived token (60 days)
    4. Get Facebook Pages
    5. Find Instagram Business Account for each page
    6. Get Instagram profile information
    7. Store encrypted tokens in database
    8. Redirect to frontend

    Query Parameters:
        code: Authorization code from Facebook
        state: State parameter for CSRF validation
        error: Error code if authorization failed
        error_reason: Error reason
        error_description: Human-readable error description

    Returns:
        Redirect to frontend with success/error parameters

    Raises:
        HTTPException 400: Invalid state, missing code, or OAuth error
        HTTPException 500: Server error during OAuth
    """
    try:
        # Handle OAuth errors
        if error:
            logger.warning(f"Instagram OAuth error: {error} - {error_description}")
            error_msg = error_description or error_reason or error

            # Try to get return_url from state
            stored_data = oauth_state_storage.get(state, {}) if state else {}
            return_url = stored_data.get("return_url")

            # Clean up state
            if state and state in oauth_state_storage:
                del oauth_state_storage[state]

            if return_url:
                error_url = f"{return_url}?error={error}&message={error_msg}&platform=instagram"
                return RedirectResponse(url=error_url)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instagram authorization failed: {error_msg}"
            )

        # Validate state parameter (CSRF protection)
        if not state or state not in oauth_state_storage:
            logger.warning(f"Invalid or expired OAuth state: {state[:10] if state else 'None'}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state. Please try again."
            )

        stored_data = oauth_state_storage[state]
        user_id = stored_data["user_id"]
        return_url = stored_data.get("return_url")

        # Clean up state (one-time use)
        del oauth_state_storage[state]

        # Validate authorization code is provided
        if not code:
            logger.error("Authorization code not provided")
            if return_url:
                error_url = f"{return_url}?error=no_code&platform=instagram"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is required"
            )

        # Step 1: Exchange authorization code for short-lived token
        short_lived_data = await exchange_code_for_token(code)

        if not short_lived_data:
            logger.error("Failed to exchange Instagram authorization code")
            if return_url:
                error_url = f"{return_url}?error=token_exchange_failed&platform=instagram"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to authenticate with Facebook/Instagram"
            )

        short_lived_token = short_lived_data["access_token"]

        # Step 2: Exchange short-lived token for long-lived token (60 days)
        long_lived_data = await exchange_for_long_lived_token(short_lived_token)

        if not long_lived_data:
            logger.error("Failed to exchange for long-lived Instagram token")
            if return_url:
                error_url = f"{return_url}?error=long_lived_token_failed&platform=instagram"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get long-lived token from Facebook"
            )

        access_token = long_lived_data["access_token"]
        expires_in = long_lived_data.get("expires_in", 5183944)  # Default: ~60 days

        # Step 3: Get Facebook Pages
        pages = await get_facebook_pages(access_token)

        if not pages:
            logger.error("Failed to get Facebook Pages")
            if return_url:
                error_url = f"{return_url}?error=no_pages&platform=instagram&message=No Facebook Pages found. Please create a Facebook Page and link your Instagram Business Account."
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Facebook Pages found. Please create a Facebook Page and link your Instagram Business Account."
            )

        # Step 4: Find Instagram Business Account
        instagram_account = None
        page_access_token = None

        for page in pages:
            page_id = page.get("id")
            page_token = page.get("access_token")

            if not page_id or not page_token:
                continue

            # Get Instagram account for this page
            ig_account = await get_instagram_account(page_id, page_token)

            if ig_account:
                instagram_account = ig_account
                page_access_token = page_token
                break

        if not instagram_account:
            logger.error("No Instagram Business Account found")
            if return_url:
                error_url = f"{return_url}?error=no_instagram&platform=instagram&message=No Instagram Business Account found. Please link your Instagram Business Account to a Facebook Page."
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Instagram Business Account found. Please link your Instagram Business Account to a Facebook Page."
            )

        instagram_user_id = instagram_account.get("id")

        # Step 5: Get Instagram profile information
        user_info = await get_instagram_user_info(instagram_user_id, page_access_token)

        if not user_info:
            logger.warning("Failed to get Instagram user info, using basic data")
            # Fallback to basic data
            user_info = {
                "id": instagram_user_id,
                "username": instagram_account.get("username", "unknown"),
                "name": instagram_account.get("name", "Instagram User")
            }

        # Step 6: Store connection in database
        manager = SocialConnectionManager(db)
        connection = manager.create_connection(
            user_id=user_id,
            platform="instagram",
            access_token=page_access_token,  # Store page access token (needed for publishing)
            refresh_token=None,  # Facebook/Instagram uses long-lived tokens
            expires_in=expires_in,
            scope=",".join(["instagram_basic", "instagram_content_publish", "pages_read_engagement"]),
            platform_user_id=user_info.get("id"),
            platform_username=user_info.get("username"),
            metadata={
                **user_info,
                "page_access_token": True,  # Flag that we're storing page token
                "instagram_account_id": instagram_user_id
            }
        )

        logger.info(f"Instagram OAuth connection created for user {user_id} (@{user_info.get('username')})")

        # Step 7: Redirect to frontend
        if return_url:
            success_url = f"{return_url}?success=true&platform=instagram&username={user_info.get('username', '')}"
            return RedirectResponse(url=success_url)

        return {
            "success": True,
            "message": "Instagram account connected successfully",
            "platform": "instagram",
            "username": user_info.get("username"),
            "oauth_version": "2.0",
            "token_expires_in_days": expires_in / 86400  # Convert seconds to days
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Instagram OAuth callback: {str(e)}")
        if 'return_url' in locals() and return_url:
            error_url = f"{return_url}?error=server_error&platform=instagram"
            return RedirectResponse(url=error_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during OAuth authentication"
        )


@router.get("/instagram/status")
async def instagram_status(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get Instagram connection status for the current user.

    Returns:
        {
            "configured": true,
            "connected": true,
            "username": "my_username",
            "user_id": "12345678901234567",
            "expires_at": "2024-12-31T23:59:59",
            "is_expired": false,
            "can_refresh": true,
            "last_used": "2024-01-15T10:30:00"
        }
    """
    try:
        # Check if Instagram OAuth is configured on the server
        config_status = get_instagram_config_status()

        if not config_status["configured"]:
            return {
                "configured": False,
                "connected": False,
                "error": "Instagram OAuth not configured on server"
            }

        # Get user's connection status
        manager = SocialConnectionManager(db)
        connection_status = manager.get_connection_status(user.id, "instagram")

        return {
            **config_status,
            **connection_status
        }

    except Exception as e:
        logger.error(f"Error getting Instagram status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving Instagram connection status"
        )


@router.delete("/instagram/disconnect")
async def instagram_disconnect(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Disconnect Instagram account for the current user.

    This marks the connection as inactive but preserves it for audit trail.
    Use DELETE /instagram/delete to permanently remove the connection.

    Returns:
        {
            "success": true,
            "message": "Instagram account disconnected successfully",
            "platform": "instagram"
        }

    Raises:
        HTTPException 404: No Instagram connection found
    """
    try:
        manager = SocialConnectionManager(db)
        success = manager.disconnect(user.id, "instagram")

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Instagram connection found for this user"
            )

        logger.info(f"Disconnected Instagram account for user {user.id}")

        return {
            "success": True,
            "message": "Instagram account disconnected successfully",
            "platform": "instagram"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting Instagram: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error disconnecting Instagram account"
        )


@router.delete("/instagram/delete")
async def instagram_delete(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Permanently delete Instagram connection for the current user.

    WARNING: This permanently removes the connection from the database.
    Consider using /instagram/disconnect instead to preserve audit trail.

    Returns:
        {
            "success": true,
            "message": "Instagram connection permanently deleted",
            "platform": "instagram"
        }

    Raises:
        HTTPException 404: No Instagram connection found
    """
    try:
        manager = SocialConnectionManager(db)
        success = manager.delete_connection(user.id, "instagram")

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Instagram connection found for this user"
            )

        logger.info(f"Permanently deleted Instagram connection for user {user.id}")

        return {
            "success": True,
            "message": "Instagram connection permanently deleted",
            "platform": "instagram"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting Instagram connection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting Instagram connection"
        )


@router.post("/instagram/refresh")
async def instagram_refresh_token(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Manually refresh Instagram access token.

    Instagram tokens are automatically refreshed when expired, but this
    endpoint allows manual refresh for testing or maintenance.

    Returns:
        {
            "success": true,
            "message": "Instagram token refreshed successfully",
            "expires_in_days": 60
        }

    Raises:
        HTTPException 404: No Instagram connection found
        HTTPException 400: Token refresh failed
    """
    try:
        manager = SocialConnectionManager(db)
        connection = manager.get_connection(user.id, "instagram", auto_refresh=False)

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Instagram connection found for this user"
            )

        # Attempt to refresh the token
        success = manager.refresh_connection(connection)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to refresh Instagram token"
            )

        # Calculate days until expiration
        expires_in_days = None
        if connection.expires_at:
            delta = connection.expires_at - datetime.utcnow()
            expires_in_days = delta.total_seconds() / 86400

        logger.info(f"Manually refreshed Instagram token for user {user.id}")

        return {
            "success": True,
            "message": "Instagram token refreshed successfully",
            "expires_in_days": round(expires_in_days, 1) if expires_in_days else None,
            "expires_at": connection.expires_at.isoformat() if connection.expires_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing Instagram token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error refreshing Instagram token"
        )


@router.get("/instagram/profile")
async def instagram_get_profile(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get Instagram profile information for the connected account.

    Returns fresh profile data from Instagram Graph API.

    Returns:
        {
            "id": "12345678901234567",
            "username": "my_username",
            "name": "Display Name",
            "profile_picture_url": "https://...",
            "biography": "My bio",
            "followers_count": 1000,
            "follows_count": 500,
            "media_count": 250
        }

    Raises:
        HTTPException 404: No Instagram connection found
        HTTPException 400: Failed to fetch profile
    """
    try:
        manager = SocialConnectionManager(db)
        connection = manager.get_connection(user.id, "instagram", auto_refresh=True)

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Instagram connection found for this user"
            )

        # Get decrypted access token
        access_token = manager.get_decrypted_token(connection)

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to decrypt access token"
            )

        # Get Instagram account ID from metadata
        instagram_account_id = connection.platform_metadata.get("instagram_account_id") if connection.platform_metadata else None

        if not instagram_account_id:
            instagram_account_id = connection.platform_user_id

        # Fetch fresh profile data
        profile = await get_instagram_user_info(instagram_account_id, access_token)

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch Instagram profile"
            )

        # Update stored metadata
        if connection.platform_metadata:
            connection.platform_metadata.update(profile)
        else:
            connection.platform_metadata = profile
        db.commit()

        logger.info(f"Fetched Instagram profile for user {user.id}")

        return profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Instagram profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching Instagram profile"
        )


# ============================================================================
# Debug Endpoints (Development Only)
# ============================================================================

@router.get("/instagram/debug/config")
async def instagram_debug_config():
    """
    Debug endpoint to view Instagram OAuth configuration.

    WARNING: Remove this endpoint in production!

    Returns:
        Configuration status without exposing secrets
    """
    return get_instagram_config_status()


@router.get("/instagram/debug/storage")
async def instagram_debug_storage(user: User = Depends(get_current_user_dependency)):
    """
    Debug endpoint to view OAuth state storage.

    WARNING: Remove this endpoint in production!

    Returns:
        Number of stored OAuth states and their ages
    """
    current_time = datetime.utcnow()
    storage_info = []

    for state, data in oauth_state_storage.items():
        age_seconds = (current_time - data['created_at']).total_seconds()
        storage_info.append({
            "state_prefix": state[:10] + "...",
            "user_id": data["user_id"],
            "age_seconds": age_seconds,
            "expires_in_seconds": 600 - age_seconds
        })

    return {
        "total_states": len(oauth_state_storage),
        "states": storage_info
    }
