"""
OAuth authentication endpoints (Phase 3) - Google and GitHub
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import secrets
import logging
import urllib.parse

from database import get_db, User
from utils.oauth import (
    get_google_auth_url,
    get_google_user_info,
    get_github_auth_url,
    get_github_user_info,
    create_or_update_oauth_user,
    unlink_oauth_account,
)
from utils.auth import create_session, get_current_user_dependency, verify_password, hash_password
from api.auth import LoginResponse, UserResponse, StandardResponse

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth state storage (in production, use Redis or database)
oauth_states = {}


class LinkOAuthRequest(BaseModel):
    """Request model for linking OAuth to existing account"""

    password: str


class SetPasswordRequest(BaseModel):
    """Request model for setting password on OAuth account"""

    password: str

    def validate_password(self) -> str:
        """Validate password meets minimum requirements"""
        if len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return self.password


# ============================================================================
# Google OAuth Endpoints
# ============================================================================


@router.get("/google")
async def google_oauth_login(
    request: Request,
    return_url: Optional[str] = Query(None, description="Frontend URL to redirect after OAuth"),
):
    """
    Initiate Google OAuth flow.

    Query Parameters:
        return_url: Optional frontend URL to redirect to after successful OAuth

    Returns:
        JSON with authorization_url to redirect user to Google OAuth consent screen
    """
    try:
        # Generate secure state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        oauth_states[state] = {
            "created_at": datetime.utcnow(),
            "ip": request.client.host if request.client else None,
            "return_url": return_url,  # Store return URL for callback
        }

        # Clean up old states (older than 10 minutes)
        current_time = datetime.utcnow()
        expired_states = [
            s
            for s, data in oauth_states.items()
            if (current_time - data["created_at"]).total_seconds() > 600
        ]
        for s in expired_states:
            del oauth_states[s]

        # Get authorization URL
        auth_url = get_google_auth_url(state)

        logger.info(f"Generated Google OAuth URL, state={state[:10]}...")

        return {"success": True, "authorization_url": auth_url, "provider": "google"}

    except ValueError as e:
        logger.error(f"Google OAuth not configured: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured on this server",
        )
    except Exception as e:
        logger.error(f"Error generating Google OAuth URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while initiating OAuth",
        )


@router.get("/google/callback")
async def google_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Handle Google OAuth callback.

    Creates new user or logs in existing user via OAuth.
    Supports redirecting to frontend after successful authentication.

    Args:
        code: Authorization code from Google
        state: State parameter for CSRF validation
        request: FastAPI request object
        db: Database session

    Returns:
        Redirect to frontend with token or LoginResponse JSON
    """
    try:
        # Validate state parameter
        if state not in oauth_states:
            logger.warning(f"Invalid OAuth state parameter")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter. Please try again.",
            )

        # Get state data and remove used state
        state_data = oauth_states[state]
        return_url = state_data.get("return_url")
        del oauth_states[state]

        # Exchange code for user info
        user_info = await get_google_user_info(code)

        if not user_info:
            logger.error("Failed to get user info from Google")
            if return_url:
                error_url = f"{return_url}?error=oauth_failed&provider=google"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to authenticate with Google"
            )

        # Extract user information
        oauth_id = user_info.get("id") or user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name", email)
        picture = user_info.get("picture")

        if not oauth_id or not email:
            logger.error(f"Missing required user info from Google: {user_info}")
            if return_url:
                error_url = f"{return_url}?error=incomplete_data&provider=google"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incomplete user information from Google",
            )

        # Create or update user
        user = create_or_update_oauth_user(
            db=db, provider="google", oauth_id=oauth_id, email=email, name=name, picture=picture
        )

        # Get user agent and IP for session tracking
        user_agent = request.headers.get("user-agent") if request else None
        ip_address = request.client.host if request and request.client else None

        # Create session (30 days for OAuth) - returns tuple now
        token, expires_at = create_session(
            user_id=user.id, db=db, expires_days=30, user_agent=user_agent, ip_address=ip_address
        )

        logger.info(f"OAuth login successful: user_id={user.id}, provider=google")

        # If return_url provided, redirect to frontend with token
        if return_url:
            redirect_url = f"{return_url}?token={token}&expires_at={expires_at.isoformat()}"
            return RedirectResponse(url=redirect_url)

        # Otherwise return JSON response
        return LoginResponse(
            success=True,
            token=token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                bio=user.bio,
                created_at=user.created_at,
                is_verified=user.is_verified,
            ),
            expires_at=expires_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in OAuth callback: {str(e)}")
        if "return_url" in locals() and return_url:
            error_url = f"{return_url}?error=server_error&provider=google"
            return RedirectResponse(url=error_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during OAuth authentication",
        )


# ============================================================================
# GitHub OAuth Endpoints
# ============================================================================


@router.get("/github")
async def github_oauth_login(
    request: Request,
    return_url: Optional[str] = Query(None, description="Frontend URL to redirect after OAuth"),
):
    """
    Initiate GitHub OAuth flow.

    Query Parameters:
        return_url: Optional frontend URL to redirect to after successful OAuth

    Returns:
        JSON with authorization_url to redirect user to GitHub OAuth consent screen
    """
    try:
        # Generate secure state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        oauth_states[state] = {
            "created_at": datetime.utcnow(),
            "ip": request.client.host if request.client else None,
            "return_url": return_url,  # Store return URL for callback
        }

        # Clean up old states (older than 10 minutes)
        current_time = datetime.utcnow()
        expired_states = [
            s
            for s, data in oauth_states.items()
            if (current_time - data["created_at"]).total_seconds() > 600
        ]
        for s in expired_states:
            del oauth_states[s]

        # Get authorization URL
        auth_url = get_github_auth_url(state)

        logger.info(f"Generated GitHub OAuth URL, state={state[:10]}...")

        return {"success": True, "authorization_url": auth_url, "provider": "github"}

    except ValueError as e:
        logger.error(f"GitHub OAuth not configured: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured on this server",
        )
    except Exception as e:
        logger.error(f"Error generating GitHub OAuth URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while initiating OAuth",
        )


@router.get("/github/callback")
async def github_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Handle GitHub OAuth callback.

    Creates new user or logs in existing user via OAuth.
    Supports redirecting to frontend after successful authentication.

    Args:
        code: Authorization code from GitHub
        state: State parameter for CSRF validation
        request: FastAPI request object
        db: Database session

    Returns:
        Redirect to frontend with token or LoginResponse JSON
    """
    try:
        # Validate state parameter
        if state not in oauth_states:
            logger.warning(f"Invalid OAuth state parameter")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter. Please try again.",
            )

        # Get state data and remove used state
        state_data = oauth_states[state]
        return_url = state_data.get("return_url")
        del oauth_states[state]

        # Exchange code for user info
        user_info = await get_github_user_info(code)

        if not user_info:
            logger.error("Failed to get user info from GitHub")
            if return_url:
                error_url = f"{return_url}?error=oauth_failed&provider=github"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to authenticate with GitHub"
            )

        # Extract user information
        oauth_id = str(user_info.get("id"))  # GitHub uses numeric IDs
        email = user_info.get("email")
        name = user_info.get("name") or user_info.get("login")  # Fallback to username
        picture = user_info.get("avatar_url")

        if not oauth_id or not email:
            logger.error(f"Missing required user info from GitHub: {user_info}")
            if return_url:
                error_url = f"{return_url}?error=incomplete_data&provider=github"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incomplete user information from GitHub. Please ensure your GitHub email is verified and public.",
            )

        # Create or update user
        user = create_or_update_oauth_user(
            db=db, provider="github", oauth_id=oauth_id, email=email, name=name, picture=picture
        )

        # Get user agent and IP for session tracking
        user_agent = request.headers.get("user-agent") if request else None
        ip_address = request.client.host if request and request.client else None

        # Create session (30 days for OAuth) - returns tuple now
        token, expires_at = create_session(
            user_id=user.id, db=db, expires_days=30, user_agent=user_agent, ip_address=ip_address
        )

        logger.info(f"OAuth login successful: user_id={user.id}, provider=github")

        # If return_url provided, redirect to frontend with token
        if return_url:
            redirect_url = f"{return_url}?token={token}&expires_at={expires_at.isoformat()}"
            return RedirectResponse(url=redirect_url)

        # Otherwise return JSON response
        return LoginResponse(
            success=True,
            token=token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                bio=user.bio,
                created_at=user.created_at,
                is_verified=user.is_verified,
            ),
            expires_at=expires_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in GitHub OAuth callback: {str(e)}")
        if "return_url" in locals() and return_url:
            error_url = f"{return_url}?error=server_error&provider=github"
            return RedirectResponse(url=error_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during OAuth authentication",
        )


# ============================================================================
# OAuth Management Endpoints
# ============================================================================


@router.post("/link", response_model=StandardResponse)
async def link_oauth_account(
    request: LinkOAuthRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Link OAuth account to existing password-based account.

    This endpoint allows users who signed up with email/password
    to link their Google or GitHub account for easier login.

    Args:
        request: Password for verification
        user: Current authenticated user
        db: Database session

    Returns:
        Success response

    Note:
        Actual linking happens in the OAuth callback when email matches existing account.
    """
    try:
        # Verify password
        if not user.password_hash or not verify_password(request.password, user.password_hash):
            logger.warning(f"OAuth link failed - incorrect password for user_id={user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password"
            )

        # Check if already linked
        if user.oauth_provider:
            return StandardResponse(
                success=True, message=f"Your account is already linked to {user.oauth_provider}"
            )

        return StandardResponse(
            success=True,
            message="Password verified. Please complete OAuth flow to link your account.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking OAuth account for user_id={user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while linking OAuth account",
        )


@router.delete("/unlink", response_model=StandardResponse)
async def unlink_oauth_account_endpoint(
    user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Unlink OAuth account from user.

    User must have a password set before unlinking OAuth.

    Args:
        user: Current authenticated user
        db: Database session

    Returns:
        Success response

    Raises:
        HTTPException: If user doesn't have password set
    """
    try:
        if not user.oauth_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No OAuth account is linked"
            )

        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must set a password before unlinking your OAuth account",
            )

        success = unlink_oauth_account(user, db)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to unlink OAuth account. Please ensure you have a password set.",
            )

        return StandardResponse(success=True, message="OAuth account unlinked successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unlinking OAuth for user_id={user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while unlinking OAuth account",
        )


@router.post("/set-password", response_model=StandardResponse)
async def set_password_for_oauth_user(
    request: SetPasswordRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Set password for OAuth-only user.

    This allows OAuth users to add password authentication
    so they can unlink OAuth if desired.

    Args:
        request: New password
        user: Current authenticated user
        db: Database session

    Returns:
        Success response
    """
    try:
        # Validate password
        try:
            request.validate_password()
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # Check if user already has password
        if user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account already has a password. Use change-password endpoint instead.",
            )

        # Set password
        user.password_hash = hash_password(request.password)
        user.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Password set for OAuth user: user_id={user.id}")

        return StandardResponse(
            success=True,
            message="Password set successfully. You can now unlink your OAuth account if desired.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting password for user_id={user.id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while setting password",
        )


@router.get("/status", response_model=dict)
async def oauth_status(user: User = Depends(get_current_user_dependency)):
    """
    Get OAuth status for current user.

    Returns information about linked OAuth accounts.

    Args:
        user: Current authenticated user

    Returns:
        OAuth status information
    """
    return {
        "success": True,
        "oauth_linked": user.oauth_provider is not None,
        "oauth_provider": user.oauth_provider,
        "has_password": user.password_hash is not None,
        "profile_picture": user.oauth_profile_picture,
        "can_unlink": user.oauth_provider is not None and user.password_hash is not None,
    }
