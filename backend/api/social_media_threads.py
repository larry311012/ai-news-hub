"""
Threads OAuth 2.0 Endpoints - Centralized Authentication

This module provides Threads OAuth 2.0 endpoints for connecting user accounts
to the Threads platform (Meta). Uses the Instagram Graph API infrastructure.

Features:
- OAuth 2.0 authorization flow
- Long-lived token management (60-day tokens)
- Automatic token refresh
- Encrypted token storage
- CSRF protection via state parameter

Usage in main.py:
```python
from api.social_media_threads import router as threads_router
app.include_router(threads_router, prefix="/api/social-media", tags=["social-media"])
```

OAuth Flow:
1. User clicks "Connect Threads"
2. GET /threads/connect -> Returns authorization URL
3. User authorizes on Threads
4. Threads redirects to /threads/callback
5. Exchange code for short-lived token
6. Exchange short-lived for long-lived token (60 days)
7. Store encrypted token in database
8. Token auto-refreshes before expiry
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
from utils.threads_oauth import (
    get_authorization_url,
    exchange_code_for_token,
    exchange_for_long_lived_token,
    refresh_access_token,
    get_user_info,
    is_threads_configured,
    get_threads_config_status
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
# Threads OAuth 2.0 Endpoints
# ============================================================================

@router.get("/threads/connect")
async def threads_connect(
    request: Request,
    return_url: Optional[str] = Query(None, description="Frontend URL to redirect after OAuth"),
    user: User = Depends(get_current_user_dependency)
):
    """
    Initiate Threads OAuth 2.0 flow.

    This endpoint generates an authorization URL and redirects the user
    to Threads to authorize the application.

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
            "authorization_url": "https://threads.net/oauth/authorize?...",
            "platform": "threads",
            "oauth_version": "2.0"
        }

    Raises:
        HTTPException 503: Threads OAuth not configured
        HTTPException 500: Error generating authorization URL
    """
    try:
        # Check if Threads OAuth is configured
        if not is_threads_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Threads OAuth is not configured on this server. Please set THREADS_CLIENT_ID and THREADS_CLIENT_SECRET."
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

        logger.info(f"Generated Threads OAuth authorization URL for user {user.id}")

        return {
            "success": True,
            "authorization_url": auth_url,
            "platform": "threads",
            "oauth_version": "2.0"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating Threads OAuth URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while initiating OAuth"
        )


@router.get("/threads/callback")
async def threads_callback(
    code: Optional[str] = Query(None, description="Authorization code from Threads"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    error: Optional[str] = Query(None, description="Error code if authorization failed"),
    error_reason: Optional[str] = Query(None, description="Error reason if authorization failed"),
    error_description: Optional[str] = Query(None, description="Error description if authorization failed"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Handle Threads OAuth 2.0 callback.

    Threads redirects here after user authorizes the app.

    Flow:
    1. Validate state parameter (CSRF protection)
    2. Exchange authorization code for short-lived token
    3. Exchange short-lived token for long-lived token (60 days)
    4. Get user profile information
    5. Store encrypted tokens in database
    6. Redirect to frontend

    Query Parameters:
        code: Authorization code from Threads
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
            logger.warning(f"Threads OAuth error: {error} - {error_description}")
            error_msg = error_description or error_reason or error

            # Try to get return_url from state
            stored_data = oauth_state_storage.get(state, {}) if state else {}
            return_url = stored_data.get("return_url")

            # Clean up state
            if state and state in oauth_state_storage:
                del oauth_state_storage[state]

            if return_url:
                error_url = f"{return_url}?error={error}&message={error_msg}&platform=threads"
                return RedirectResponse(url=error_url)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Threads authorization failed: {error_msg}"
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
                error_url = f"{return_url}?error=no_code&platform=threads"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is required"
            )

        # Step 1: Exchange authorization code for short-lived token
        short_lived_data = await exchange_code_for_token(code)

        if not short_lived_data:
            logger.error("Failed to exchange Threads authorization code")
            if return_url:
                error_url = f"{return_url}?error=token_exchange_failed&platform=threads"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to authenticate with Threads"
            )

        short_lived_token = short_lived_data["access_token"]
        threads_user_id = short_lived_data.get("user_id")

        # Step 2: Exchange short-lived token for long-lived token (60 days)
        long_lived_data = await exchange_for_long_lived_token(short_lived_token)

        if not long_lived_data:
            logger.error("Failed to exchange for long-lived Threads token")
            if return_url:
                error_url = f"{return_url}?error=long_lived_token_failed&platform=threads"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get long-lived token from Threads"
            )

        access_token = long_lived_data["access_token"]
        expires_in = long_lived_data.get("expires_in", 5183944)  # Default: ~60 days

        # Step 3: Get user profile information
        user_info = await get_user_info(access_token)

        if not user_info:
            logger.warning("Failed to get Threads user info, using basic data")
            # Fallback to basic data from token response
            user_info = {
                "id": threads_user_id,
                "username": "unknown",
                "name": "Threads User"
            }

        # Step 4: Store connection in database
        manager = SocialConnectionManager(db)
        connection = manager.create_connection(
            user_id=user_id,
            platform="threads",
            access_token=access_token,
            refresh_token=None,  # Threads doesn't use refresh tokens; we refresh using access token
            expires_in=expires_in,
            scope=",".join(["threads_basic", "threads_content_publish"]),
            platform_user_id=user_info.get("id"),
            platform_username=user_info.get("username"),
            metadata=user_info
        )

        logger.info(f"Threads OAuth connection created for user {user_id} (@{user_info.get('username')})")

        # Step 5: Redirect to frontend
        if return_url:
            success_url = f"{return_url}?success=true&platform=threads&username={user_info.get('username', '')}"
            return RedirectResponse(url=success_url)

        return {
            "success": True,
            "message": "Threads account connected successfully",
            "platform": "threads",
            "username": user_info.get("username"),
            "oauth_version": "2.0",
            "token_expires_in_days": expires_in / 86400  # Convert seconds to days
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Threads OAuth callback: {str(e)}")
        if 'return_url' in locals() and return_url:
            error_url = f"{return_url}?error=server_error&platform=threads"
            return RedirectResponse(url=error_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during OAuth authentication"
        )


@router.get("/threads/status")
async def threads_status(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get Threads connection status for the current user.

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
        # Check if Threads OAuth is configured on the server
        config_status = get_threads_config_status()

        if not config_status["configured"]:
            return {
                "configured": False,
                "connected": False,
                "error": "Threads OAuth not configured on server"
            }

        # Get user's connection status
        manager = SocialConnectionManager(db)
        connection_status = manager.get_connection_status(user.id, "threads")

        return {
            **config_status,
            **connection_status
        }

    except Exception as e:
        logger.error(f"Error getting Threads status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving Threads connection status"
        )


@router.delete("/threads/disconnect")
async def threads_disconnect(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Disconnect Threads account for the current user.

    This marks the connection as inactive but preserves it for audit trail.
    Use DELETE /threads/delete to permanently remove the connection.

    Returns:
        {
            "success": true,
            "message": "Threads account disconnected successfully",
            "platform": "threads"
        }

    Raises:
        HTTPException 404: No Threads connection found
    """
    try:
        manager = SocialConnectionManager(db)
        success = manager.disconnect(user.id, "threads")

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Threads connection found for this user"
            )

        logger.info(f"Disconnected Threads account for user {user.id}")

        return {
            "success": True,
            "message": "Threads account disconnected successfully",
            "platform": "threads"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting Threads: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error disconnecting Threads account"
        )


@router.delete("/threads/delete")
async def threads_delete(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Permanently delete Threads connection for the current user.

    WARNING: This permanently removes the connection from the database.
    Consider using /threads/disconnect instead to preserve audit trail.

    Returns:
        {
            "success": true,
            "message": "Threads connection permanently deleted",
            "platform": "threads"
        }

    Raises:
        HTTPException 404: No Threads connection found
    """
    try:
        manager = SocialConnectionManager(db)
        success = manager.delete_connection(user.id, "threads")

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Threads connection found for this user"
            )

        logger.info(f"Permanently deleted Threads connection for user {user.id}")

        return {
            "success": True,
            "message": "Threads connection permanently deleted",
            "platform": "threads"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting Threads connection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting Threads connection"
        )


@router.post("/threads/refresh")
async def threads_refresh_token(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Manually refresh Threads access token.

    Threads tokens are automatically refreshed when expired, but this
    endpoint allows manual refresh for testing or maintenance.

    Returns:
        {
            "success": true,
            "message": "Threads token refreshed successfully",
            "expires_in_days": 60
        }

    Raises:
        HTTPException 404: No Threads connection found
        HTTPException 400: Token refresh failed
    """
    try:
        manager = SocialConnectionManager(db)
        connection = manager.get_connection(user.id, "threads", auto_refresh=False)

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Threads connection found for this user"
            )

        # Attempt to refresh the token
        success = manager.refresh_connection(connection)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to refresh Threads token"
            )

        # Calculate days until expiration
        expires_in_days = None
        if connection.expires_at:
            delta = connection.expires_at - datetime.utcnow()
            expires_in_days = delta.total_seconds() / 86400

        logger.info(f"Manually refreshed Threads token for user {user.id}")

        return {
            "success": True,
            "message": "Threads token refreshed successfully",
            "expires_in_days": round(expires_in_days, 1) if expires_in_days else None,
            "expires_at": connection.expires_at.isoformat() if connection.expires_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing Threads token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error refreshing Threads token"
        )


@router.get("/threads/profile")
async def threads_get_profile(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get Threads profile information for the connected account.

    Returns fresh profile data from Threads API.

    Returns:
        {
            "id": "12345678901234567",
            "username": "my_username",
            "name": "Display Name",
            "threads_profile_picture_url": "https://...",
            "threads_biography": "My bio"
        }

    Raises:
        HTTPException 404: No Threads connection found
        HTTPException 400: Failed to fetch profile
    """
    try:
        manager = SocialConnectionManager(db)
        connection = manager.get_connection(user.id, "threads", auto_refresh=True)

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Threads connection found for this user"
            )

        # Get decrypted access token
        access_token = manager.get_decrypted_token(connection)

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to decrypt access token"
            )

        # Fetch fresh profile data
        profile = await get_user_info(access_token)

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch Threads profile"
            )

        # Update stored metadata
        connection.platform_metadata = profile
        db.commit()

        logger.info(f"Fetched Threads profile for user {user.id}")

        return profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Threads profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching Threads profile"
        )


# ============================================================================
# Debug Endpoints (Development Only)
# ============================================================================

@router.get("/threads/debug/config")
async def threads_debug_config():
    """
    Debug endpoint to view Threads OAuth configuration.

    WARNING: Remove this endpoint in production!

    Returns:
        Configuration status without exposing secrets
    """
    return get_threads_config_status()


@router.get("/threads/debug/storage")
async def threads_debug_storage(user: User = Depends(get_current_user_dependency)):
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
