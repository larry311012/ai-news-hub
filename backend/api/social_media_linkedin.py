"""
LinkedIn OAuth 2.0 Endpoints - Per-User Credentials

This module provides LinkedIn OAuth 2.0 endpoints for connecting user accounts
using per-user credentials. Each user provides their own LinkedIn app credentials.

Features:
- OAuth 2.0 authorization flow using user's own LinkedIn app
- Encrypted credential storage
- CSRF protection via state parameter
- User profile fetching
- Token validation

Usage in main.py:
```python
from api.social_media_linkedin import router as linkedin_router
app.include_router(linkedin_router, prefix="/api/oauth-setup", tags=["oauth-setup"])
```

OAuth Flow:
1. User provides LinkedIn Client ID and Client Secret via setup wizard
2. User clicks "Connect LinkedIn"
3. GET /oauth-setup/linkedin/connect -> Returns authorization URL
4. User authorizes on LinkedIn
5. LinkedIn redirects to /oauth-setup/linkedin/callback
6. Exchange code for access token using user's credentials
7. Store encrypted token in database
8. Redirect to frontend
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging
import secrets
import time

from database import get_db, User
from database_social_media import SocialMediaConnection
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.social_connection_manager import SocialConnectionManager
from utils.user_oauth_credential_manager import UserOAuthCredentialManager
from utils.linkedin_oauth import (
    get_authorization_url,
    exchange_code_for_token,
    get_user_info,
    validate_token,
    get_scopes
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Temporary storage for OAuth state
# In production, use Redis with TTL
# Key: state, Value: dict with user_id, return_url, and user credentials
oauth_state_storage = {}


# ============================================================================
# LinkedIn OAuth 2.0 Endpoints (Per-User Credentials)
# ============================================================================

@router.post("/linkedin/credentials")
async def save_linkedin_credentials(
    request: Request,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Save user's LinkedIn app credentials (Client ID, Client Secret, Redirect URI).

    This endpoint allows users to provide their own LinkedIn app credentials
    which will be encrypted and stored in the database.

    Request Body:
        {
            "client_id": "your_linkedin_client_id",
            "client_secret": "your_linkedin_client_secret",
            "redirect_uri": "http://localhost:3000/oauth-callback" (optional)
        }

    Returns:
        {
            "success": true,
            "message": "LinkedIn credentials saved successfully"
        }
    """
    try:
        # Parse request body
        body = await request.json()
        client_id = body.get("client_id", "").strip()
        client_secret = body.get("client_secret", "").strip()
        redirect_uri = body.get("redirect_uri", "").strip()

        # Validate inputs
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client ID and Client Secret are required"
            )

        # Basic format validation
        if len(client_id) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Client ID format"
            )

        if len(client_secret) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Client Secret format"
            )

        # Use credential manager to save encrypted credentials
        credential_manager = UserOAuthCredentialManager(
            db,
            user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        # Save credentials
        success = credential_manager.save_credentials(
            platform="linkedin",
            oauth_version="2.0",
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri or f"{request.url.scheme}://{request.url.netloc}/api/oauth-setup/linkedin/callback",
            scopes="openid,profile,email,w_member_social"
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save credentials"
            )

        logger.info(f"LinkedIn credentials saved successfully for user {user.id}")

        return {
            "success": True,
            "message": "LinkedIn credentials saved successfully",
            "redirect_uri": redirect_uri or f"{request.url.scheme}://{request.url.netloc}/api/oauth-setup/linkedin/callback"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving LinkedIn credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save credentials: {str(e)}"
        )


@router.get("/linkedin/connect")
async def linkedin_connect(
    request: Request,
    return_url: Optional[str] = Query(None, description="Frontend URL to redirect after OAuth"),
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Initiate LinkedIn OAuth 2.0 flow using user's own credentials.

    This endpoint generates an authorization URL using the user's own
    LinkedIn app credentials (Client ID/Secret) and redirects the user
    to LinkedIn to authorize the application.

    Flow:
    1. Retrieve user's LinkedIn credentials from database
    2. Generate random state for CSRF protection
    3. Store state with user context
    4. Generate authorization URL using user's credentials
    5. Return URL to frontend

    Query Parameters:
        return_url: Optional URL to redirect to after OAuth completion

    Returns:
        {
            "success": true,
            "authorization_url": "https://www.linkedin.com/oauth/v2/authorization?...",
            "platform": "linkedin",
            "oauth_version": "2.0"
        }

    Raises:
        HTTPException 400: User has not configured LinkedIn credentials
        HTTPException 500: Error generating authorization URL
    """
    # IMPORTANT: Log at the VERY START before any processing
    request_start_time = time.time()
    logger.info("=" * 80)
    logger.info(f"[LinkedIn OAuth] CONNECT REQUEST RECEIVED from user {user.id}")
    logger.info(f"[LinkedIn OAuth] Return URL: {return_url}")
    logger.info(f"[LinkedIn OAuth] Request IP: {request.client.host if request.client else 'unknown'}")
    logger.info(f"[LinkedIn OAuth] User Agent: {request.headers.get('user-agent', 'unknown')[:100]}")
    logger.info("=" * 80)

    try:
        # Step 1: Retrieve user's LinkedIn credentials from database
        logger.info(f"[LinkedIn OAuth] Step 1/5: Retrieving credentials from database for user {user.id}...")
        creds_start_time = time.time()

        credential_manager = UserOAuthCredentialManager(
            db,
            user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        credentials = credential_manager.get_credentials("linkedin")
        creds_elapsed = time.time() - creds_start_time

        logger.info(f"[LinkedIn OAuth] Step 1/5: Credentials retrieved in {creds_elapsed:.3f}s")

        if not credentials:
            logger.error(f"[LinkedIn OAuth] ERROR: No credentials found for user {user.id}")
            logger.error(f"[LinkedIn OAuth] User must complete Step 5 in setup wizard first")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LinkedIn credentials not configured. Please set up your LinkedIn app credentials first."
            )

        # Step 2: Extract and validate credentials
        logger.info(f"[LinkedIn OAuth] Step 2/5: Validating credentials...")
        client_id = credentials.get("client_id")
        client_secret = credentials.get("client_secret")
        redirect_uri = credentials.get("redirect_uri") or f"{request.url.scheme}://{request.url.netloc}/api/oauth-setup/linkedin/callback"

        if not client_id or not client_secret:
            logger.error(f"[LinkedIn OAuth] ERROR: Invalid credentials - missing client_id or client_secret")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid LinkedIn credentials. Please reconfigure your LinkedIn app."
            )

        # Log credential details for debugging (without exposing secrets)
        logger.info(f"[LinkedIn OAuth] Step 2/5: Credentials validated successfully")
        logger.info(f"[LinkedIn OAuth] Client ID: {client_id[:10]}...{client_id[-4:]}")
        logger.info(f"[LinkedIn OAuth] Redirect URI: {redirect_uri}")
        logger.info(f"[LinkedIn OAuth] Request scheme: {request.url.scheme}")
        logger.info(f"[LinkedIn OAuth] Request netloc: {request.url.netloc}")

        # Step 3: Generate random state for CSRF protection
        logger.info(f"[LinkedIn OAuth] Step 3/5: Generating CSRF state token...")
        state = secrets.token_urlsafe(32)

        # Store state with user context and credentials
        # Note: In production, use Redis with 10-minute TTL
        oauth_state_storage[state] = {
            "user_id": user.id,
            "return_url": return_url,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "created_at": datetime.utcnow()
        }

        logger.info(f"[LinkedIn OAuth] Step 3/5: State token generated: {state[:10]}...")
        logger.info(f"[LinkedIn OAuth] Step 3/5: Total OAuth states in storage: {len(oauth_state_storage)}")

        # Clean up old states (older than 10 minutes)
        current_time = datetime.utcnow()
        expired_states = [
            s for s, data in oauth_state_storage.items()
            if (current_time - data['created_at']).total_seconds() > 600
        ]
        for state_key in expired_states:
            del oauth_state_storage[state_key]
            logger.debug(f"[LinkedIn OAuth] Cleaned up expired OAuth state: {state_key[:10]}...")

        if expired_states:
            logger.info(f"[LinkedIn OAuth] Step 3/5: Cleaned up {len(expired_states)} expired states")

        # Step 4: Generate authorization URL using user's credentials
        logger.info(f"[LinkedIn OAuth] Step 4/5: Generating LinkedIn authorization URL...")
        auth_url_start_time = time.time()

        auth_url = get_authorization_url(
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            scopes=get_scopes()
        )

        auth_url_elapsed = time.time() - auth_url_start_time
        logger.info(f"[LinkedIn OAuth] Step 4/5: Authorization URL generated in {auth_url_elapsed:.3f}s")
        logger.info(f"[LinkedIn OAuth] Step 4/5: URL length: {len(auth_url)} characters")

        # IMPORTANT: Log a message to help users debug redirect URI mismatch
        logger.warning("=" * 80)
        logger.warning(f"[LinkedIn OAuth] IMPORTANT: Redirect URI Check")
        logger.warning(f"[LinkedIn OAuth] The redirect_uri being sent to LinkedIn: {redirect_uri}")
        logger.warning(f"[LinkedIn OAuth] This MUST EXACTLY match your LinkedIn app settings!")
        logger.warning(f"[LinkedIn OAuth] LinkedIn Developer Portal: https://www.linkedin.com/developers/apps")
        logger.warning(f"[LinkedIn OAuth] Go to: Your App -> Auth tab -> Authorized redirect URLs")
        logger.warning(f"[LinkedIn OAuth] Ensure this EXACT URL is added: {redirect_uri}")
        logger.warning("=" * 80)

        # Step 5: Return response
        total_elapsed = time.time() - request_start_time
        logger.info(f"[LinkedIn OAuth] Step 5/5: Preparing response...")
        logger.info(f"[LinkedIn OAuth] TOTAL REQUEST TIME: {total_elapsed:.3f}s")
        logger.info(f"[LinkedIn OAuth] - Credential retrieval: {creds_elapsed:.3f}s ({(creds_elapsed/total_elapsed*100):.1f}%)")
        logger.info(f"[LinkedIn OAuth] - URL generation: {auth_url_elapsed:.3f}s ({(auth_url_elapsed/total_elapsed*100):.1f}%)")
        logger.info(f"[LinkedIn OAuth] SUCCESS: Connect request completed for user {user.id}")
        logger.info("=" * 80)

        return {
            "success": True,
            "authorization_url": auth_url,
            "platform": "linkedin",
            "oauth_version": "2.0",
            "redirect_uri": redirect_uri,  # Return this so frontend can show it for debugging
            "debug_info": {
                "redirect_uri_in_use": redirect_uri,
                "message": "If you see a redirect_uri mismatch error, this URL must be added to your LinkedIn app settings",
                "request_time_ms": int(total_elapsed * 1000)
            }
        }

    except HTTPException as e:
        total_elapsed = time.time() - request_start_time
        logger.error(f"[LinkedIn OAuth] HTTP Exception after {total_elapsed:.3f}s: {e.status_code} - {e.detail}")
        logger.error("=" * 80)
        raise
    except Exception as e:
        total_elapsed = time.time() - request_start_time
        logger.error(f"[LinkedIn OAuth] FATAL ERROR after {total_elapsed:.3f}s: {str(e)}", exc_info=True)
        logger.error("=" * 80)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while initiating OAuth"
        )


@router.get("/linkedin/callback")
async def linkedin_callback(
    code: Optional[str] = Query(None, description="Authorization code from LinkedIn"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    error: Optional[str] = Query(None, description="Error code if authorization failed"),
    error_description: Optional[str] = Query(None, description="Error description if authorization failed"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Handle LinkedIn OAuth 2.0 callback.

    LinkedIn redirects here after user authorizes the app.

    Flow:
    1. Validate state parameter (CSRF protection)
    2. Retrieve user's credentials from state storage
    3. Exchange authorization code for access token using user's credentials
    4. Get user profile information
    5. Store encrypted tokens in database
    6. Redirect to frontend

    Query Parameters:
        code: Authorization code from LinkedIn
        state: State parameter for CSRF validation
        error: Error code if authorization failed
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
            logger.warning(f"[LinkedIn OAuth] OAuth error: {error} - {error_description}")
            error_msg = error_description or error

            # Try to get return_url from state
            stored_data = oauth_state_storage.get(state, {}) if state else {}
            return_url = stored_data.get("return_url")

            # Clean up state
            if state and state in oauth_state_storage:
                del oauth_state_storage[state]

            if return_url:
                error_url = f"{return_url}?error={error}&message={error_msg}&platform=linkedin"
                return RedirectResponse(url=error_url)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LinkedIn authorization failed: {error_msg}"
            )

        # Validate state parameter (CSRF protection)
        if not state or state not in oauth_state_storage:
            logger.warning(f"[LinkedIn OAuth] Invalid or expired OAuth state: {state[:10] if state else 'None'}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state. Please try again."
            )

        stored_data = oauth_state_storage[state]
        user_id = stored_data["user_id"]
        return_url = stored_data.get("return_url")
        client_id = stored_data["client_id"]
        client_secret = stored_data["client_secret"]
        redirect_uri = stored_data["redirect_uri"]

        # Log callback details
        logger.info(f"[LinkedIn OAuth] Callback received for user {user_id}")
        logger.info(f"[LinkedIn OAuth] Redirect URI used in callback: {redirect_uri}")
        logger.info(f"[LinkedIn OAuth] Authorization code present: {bool(code)}")

        # Clean up state (one-time use)
        del oauth_state_storage[state]

        # Validate authorization code is provided
        if not code:
            logger.error("[LinkedIn OAuth] Authorization code not provided")
            if return_url:
                error_url = f"{return_url}?error=no_code&platform=linkedin"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is required"
            )

        # Exchange authorization code for access token using user's credentials
        logger.info(f"[LinkedIn OAuth] Exchanging authorization code for access token")
        logger.info(f"[LinkedIn OAuth] Using redirect_uri: {redirect_uri}")

        token_data = await exchange_code_for_token(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri
        )

        if not token_data:
            logger.error("[LinkedIn OAuth] Failed to exchange authorization code")
            if return_url:
                error_url = f"{return_url}?error=token_exchange_failed&platform=linkedin"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to authenticate with LinkedIn"
            )

        logger.info(f"[LinkedIn OAuth] Successfully obtained access token for user {user_id}")

        access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 5184000)  # Default: 60 days
        scope = token_data.get("scope", "")

        # Get user profile information
        user_info = await get_user_info(access_token)

        if not user_info:
            logger.warning("[LinkedIn OAuth] Failed to get user info, using basic data")
            # Fallback to basic data
            user_info = {
                "sub": "unknown",
                "name": "LinkedIn User"
            }

        logger.info(f"[LinkedIn OAuth] Retrieved user info: {user_info.get('name')}")

        # Store connection in database
        manager = SocialConnectionManager(db)
        connection = manager.create_connection(
            user_id=user_id,
            platform="linkedin",
            access_token=access_token,
            refresh_token=token_data.get("refresh_token"),  # May be None
            expires_in=expires_in,
            scope=scope,
            platform_user_id=user_info.get("sub"),
            platform_username=user_info.get("name"),
            metadata=user_info
        )

        logger.info(f"[LinkedIn OAuth] Connection created for user {user_id} ({user_info.get('name')})")

        # Mark user's credentials as validated and used
        credential_manager = UserOAuthCredentialManager(db, user_id)
        cred = credential_manager.get_credentials("linkedin")
        if cred:
            from database_user_oauth_credentials import UserOAuthCredential
            db_cred = db.query(UserOAuthCredential).filter(
                UserOAuthCredential.user_id == user_id,
                UserOAuthCredential.platform == "linkedin"
            ).first()
            if db_cred:
                db_cred.is_validated = True
                db_cred.validation_status = "success"
                db_cred.last_validated_at = datetime.utcnow()
                db_cred.mark_used()
                db.commit()

        logger.info(f"[LinkedIn OAuth] Credentials marked as validated for user {user_id}")

        # Redirect to frontend
        if return_url:
            success_url = f"{return_url}?success=true&platform=linkedin&name={user_info.get('name', '')}"
            return RedirectResponse(url=success_url)

        return {
            "success": True,
            "message": "LinkedIn account connected successfully",
            "platform": "linkedin",
            "name": user_info.get("name"),
            "oauth_version": "2.0"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LinkedIn OAuth] Error in callback: {str(e)}", exc_info=True)
        if 'return_url' in locals() and return_url:
            error_url = f"{return_url}?error=server_error&platform=linkedin"
            return RedirectResponse(url=error_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during OAuth authentication"
        )


@router.get("/linkedin/status")
async def linkedin_status(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get LinkedIn connection status for the current user.

    Returns:
        {
            "configured": true,
            "connected": true,
            "name": "John Doe",
            "user_id": "abc123...",
            "expires_at": "2024-12-31T23:59:59",
            "is_expired": false,
            "last_used": "2024-01-15T10:30:00"
        }
    """
    try:
        # Check if user has LinkedIn credentials configured
        credential_manager = UserOAuthCredentialManager(db, user.id)
        credentials = credential_manager.get_credentials("linkedin")

        configured = credentials is not None

        # Get user's connection status
        manager = SocialConnectionManager(db)
        connection_status = manager.get_connection_status(user.id, "linkedin")

        return {
            "configured": configured,
            **connection_status
        }

    except Exception as e:
        logger.error(f"Error getting LinkedIn status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving LinkedIn connection status"
        )


@router.delete("/linkedin/disconnect")
async def linkedin_disconnect(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Disconnect LinkedIn account for the current user.

    This marks the connection as inactive but preserves it for audit trail.

    Returns:
        {
            "success": true,
            "message": "LinkedIn account disconnected successfully",
            "platform": "linkedin"
        }

    Raises:
        HTTPException 404: No LinkedIn connection found
    """
    try:
        manager = SocialConnectionManager(db)
        success = manager.disconnect(user.id, "linkedin")

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No LinkedIn connection found for this user"
            )

        logger.info(f"Disconnected LinkedIn account for user {user.id}")

        return {
            "success": True,
            "message": "LinkedIn account disconnected successfully",
            "platform": "linkedin"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting LinkedIn: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error disconnecting LinkedIn account"
        )


@router.delete("/linkedin/delete")
async def linkedin_delete(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Permanently delete LinkedIn connection for the current user.

    WARNING: This permanently removes the connection from the database.
    Consider using /linkedin/disconnect instead to preserve audit trail.

    Returns:
        {
            "success": true,
            "message": "LinkedIn connection permanently deleted",
            "platform": "linkedin"
        }

    Raises:
        HTTPException 404: No LinkedIn connection found
    """
    try:
        manager = SocialConnectionManager(db)
        success = manager.delete_connection(user.id, "linkedin")

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No LinkedIn connection found for this user"
            )

        logger.info(f"Permanently deleted LinkedIn connection for user {user.id}")

        return {
            "success": True,
            "message": "LinkedIn connection permanently deleted",
            "platform": "linkedin"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting LinkedIn connection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting LinkedIn connection"
        )


@router.get("/linkedin/profile")
async def linkedin_get_profile(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get LinkedIn profile information for the connected account.

    Returns fresh profile data from LinkedIn API.

    Returns:
        {
            "sub": "abc123...",
            "name": "John Doe",
            "given_name": "John",
            "family_name": "Doe",
            "picture": "https://...",
            "email": "user@example.com"
        }

    Raises:
        HTTPException 404: No LinkedIn connection found
        HTTPException 400: Failed to fetch profile
    """
    try:
        manager = SocialConnectionManager(db)
        connection = manager.get_connection(user.id, "linkedin", auto_refresh=True)

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No LinkedIn connection found for this user"
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
                detail="Failed to fetch LinkedIn profile"
            )

        # Update stored metadata
        connection.platform_metadata = profile
        db.commit()

        logger.info(f"Fetched LinkedIn profile for user {user.id}")

        return profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching LinkedIn profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching LinkedIn profile"
        )


# ============================================================================
# Debug Endpoints (Development Only)
# ============================================================================

@router.get("/linkedin/debug/storage")
async def linkedin_debug_storage(user: User = Depends(get_current_user_dependency)):
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
