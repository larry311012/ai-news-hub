"""
Social Media API Endpoints

This module provides REST API endpoints for managing social media platform
connections (LinkedIn, Twitter, Threads) and publishing posts.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import secrets
import logging

from database import get_db, User, Post
from database_social_media import SocialMediaConnection, SocialMediaPost
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.social_oauth import (
    get_linkedin_auth_url,
    get_twitter_auth_url,
    get_threads_auth_url,
    exchange_linkedin_code,
    exchange_twitter_code,
    exchange_threads_code,
    exchange_threads_long_lived_token,
    get_linkedin_user_info,
    get_twitter_user_info,
    get_threads_user_info,
    generate_pkce_pair,
)
from utils.social_connection_manager import SocialConnectionManager

# Import publisher modules
from src.publishers import LinkedInPublisher, TwitterPublisher, ThreadsPublisher
from src.publishers.exceptions import (
    AuthenticationException,
    RateLimitException,
    PublishingException,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# OAuth state storage (in production, use Redis or database)
oauth_states = {}
# PKCE storage for Twitter (in production, use Redis or database)
pkce_verifiers = {}


# ============================================================================
# Pydantic Models
# ============================================================================


class ConnectionResponse(BaseModel):
    """Response model for connection information"""

    id: int
    platform: str
    platform_username: Optional[str]
    platform_user_id: Optional[str]
    is_active: bool
    expires_at: Optional[datetime]
    is_expired: bool
    can_refresh: bool
    last_used_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ConnectionStatusResponse(BaseModel):
    """Response model for connection status check"""

    connected: bool
    platform: str
    username: Optional[str] = None
    user_id: Optional[str] = None
    expires_at: Optional[str] = None
    is_expired: bool = False
    can_refresh: bool = False
    last_used: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PublishRequest(BaseModel):
    """Request model for publishing posts"""

    post_id: int
    platforms: List[str]  # ["linkedin", "twitter", "threads"]


class PublishResponse(BaseModel):
    """Response model for publish results"""

    success: bool
    results: Dict[str, Dict[str, Any]]
    errors: Optional[Dict[str, str]] = None


class StandardResponse(BaseModel):
    """Standard API response"""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# ============================================================================
# LinkedIn OAuth Endpoints
# ============================================================================


@router.get("/linkedin/connect")
async def linkedin_connect(
    request: Request,
    return_url: Optional[str] = Query(None, description="Frontend URL to redirect after OAuth"),
    user: User = Depends(get_current_user_dependency),
):
    """
    Initiate LinkedIn OAuth flow.

    Returns authorization URL to redirect user to LinkedIn consent screen.
    """
    try:
        # Generate secure state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        oauth_states[state] = {
            "created_at": datetime.utcnow(),
            "user_id": user.id,
            "platform": "linkedin",
            "return_url": return_url,
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
        auth_url = get_linkedin_auth_url(state)

        logger.info(f"Generated LinkedIn OAuth URL for user {user.id}")

        return {"success": True, "authorization_url": auth_url, "platform": "linkedin"}

    except ValueError as e:
        logger.error(f"LinkedIn OAuth not configured: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LinkedIn OAuth is not configured on this server",
        )
    except Exception as e:
        logger.error(f"Error generating LinkedIn OAuth URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while initiating OAuth",
        )


@router.get("/linkedin/callback")
async def linkedin_callback(
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Handle LinkedIn OAuth callback.

    Exchanges authorization code for access token and creates connection.
    """
    try:
        # Validate state parameter
        if state not in oauth_states:
            logger.warning("Invalid OAuth state parameter")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter. Please try again.",
            )

        # Get state data
        state_data = oauth_states[state]
        user_id = state_data["user_id"]
        return_url = state_data.get("return_url")
        del oauth_states[state]

        # Exchange code for tokens
        tokens = await exchange_linkedin_code(code)
        if not tokens:
            logger.error("Failed to exchange LinkedIn code")
            if return_url:
                error_url = f"{return_url}?error=oauth_failed&platform=linkedin"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to authenticate with LinkedIn",
            )

        # Get user info
        access_token = tokens["access_token"]
        user_info = await get_linkedin_user_info(access_token)

        if not user_info:
            logger.error("Failed to get LinkedIn user info")
            if return_url:
                error_url = f"{return_url}?error=incomplete_data&platform=linkedin"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information from LinkedIn",
            )

        # Create connection
        manager = SocialConnectionManager(db)
        connection = manager.create_connection(
            user_id=user_id,
            platform="linkedin",
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_in=tokens.get("expires_in"),
            scope=tokens.get("scope"),
            platform_user_id=user_info.get("sub"),
            platform_username=user_info.get("name"),
            metadata=user_info,
        )

        logger.info(f"LinkedIn connection created for user {user_id}")

        # Redirect to frontend
        if return_url:
            success_url = (
                f"{return_url}?success=true&platform=linkedin&username={user_info.get('name', '')}"
            )
            return RedirectResponse(url=success_url)

        return {
            "success": True,
            "message": "LinkedIn account connected successfully",
            "platform": "linkedin",
            "username": user_info.get("name"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in LinkedIn OAuth callback: {str(e)}")
        if "return_url" in locals() and return_url:
            error_url = f"{return_url}?error=server_error&platform=linkedin"
            return RedirectResponse(url=error_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during OAuth authentication",
        )


# ============================================================================
# Twitter OAuth Endpoints (with PKCE)
# ============================================================================


@router.get("/twitter/connect")
async def twitter_connect(
    request: Request,
    return_url: Optional[str] = Query(None, description="Frontend URL to redirect after OAuth"),
    user: User = Depends(get_current_user_dependency),
):
    """
    Initiate Twitter OAuth flow with PKCE.

    Returns authorization URL to redirect user to Twitter consent screen.
    """
    try:
        # Generate PKCE pair
        code_verifier, code_challenge = generate_pkce_pair()

        # Generate secure state parameter
        state = secrets.token_urlsafe(32)
        oauth_states[state] = {
            "created_at": datetime.utcnow(),
            "user_id": user.id,
            "platform": "twitter",
            "return_url": return_url,
        }

        # Store code_verifier for token exchange
        pkce_verifiers[state] = code_verifier

        # Clean up old states
        current_time = datetime.utcnow()
        expired_states = [
            s
            for s, data in oauth_states.items()
            if (current_time - data["created_at"]).total_seconds() > 600
        ]
        for s in expired_states:
            del oauth_states[s]
            if s in pkce_verifiers:
                del pkce_verifiers[s]

        # Get authorization URL with PKCE
        auth_url = get_twitter_auth_url(state, code_challenge)

        logger.info(f"Generated Twitter OAuth URL with PKCE for user {user.id}")

        return {"success": True, "authorization_url": auth_url, "platform": "twitter"}

    except ValueError as e:
        logger.error(f"Twitter OAuth not configured: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Twitter OAuth is not configured on this server",
        )
    except Exception as e:
        logger.error(f"Error generating Twitter OAuth URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while initiating OAuth",
        )


@router.get("/twitter/callback")
async def twitter_callback(
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Handle Twitter OAuth callback with PKCE.

    Exchanges authorization code for access token and creates connection.
    """
    try:
        # Validate state parameter
        if state not in oauth_states:
            logger.warning("Invalid OAuth state parameter")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter. Please try again.",
            )

        # Get state data and code_verifier
        state_data = oauth_states[state]
        user_id = state_data["user_id"]
        return_url = state_data.get("return_url")
        code_verifier = pkce_verifiers.get(state)

        # Clean up
        del oauth_states[state]
        if state in pkce_verifiers:
            del pkce_verifiers[state]

        if not code_verifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PKCE verifier not found. Please try again.",
            )

        # Exchange code for tokens with PKCE
        tokens = await exchange_twitter_code(code, code_verifier)
        if not tokens:
            logger.error("Failed to exchange Twitter code")
            if return_url:
                error_url = f"{return_url}?error=oauth_failed&platform=twitter"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to authenticate with Twitter",
            )

        # Get user info
        access_token = tokens["access_token"]
        user_info = await get_twitter_user_info(access_token)

        if not user_info:
            logger.error("Failed to get Twitter user info")
            if return_url:
                error_url = f"{return_url}?error=incomplete_data&platform=twitter"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information from Twitter",
            )

        # Create connection
        manager = SocialConnectionManager(db)
        connection = manager.create_connection(
            user_id=user_id,
            platform="twitter",
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_in=tokens.get("expires_in"),
            scope=tokens.get("scope"),
            platform_user_id=user_info.get("id"),
            platform_username=user_info.get("username"),
            metadata=user_info,
        )

        logger.info(f"Twitter connection created for user {user_id}")

        # Redirect to frontend
        if return_url:
            success_url = f"{return_url}?success=true&platform=twitter&username={user_info.get('username', '')}"
            return RedirectResponse(url=success_url)

        return {
            "success": True,
            "message": "Twitter account connected successfully",
            "platform": "twitter",
            "username": user_info.get("username"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Twitter OAuth callback: {str(e)}")
        if "return_url" in locals() and return_url:
            error_url = f"{return_url}?error=server_error&platform=twitter"
            return RedirectResponse(url=error_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during OAuth authentication",
        )


# ============================================================================
# Threads OAuth Endpoints
# ============================================================================


@router.get("/threads/connect")
async def threads_connect(
    request: Request,
    return_url: Optional[str] = Query(None, description="Frontend URL to redirect after OAuth"),
    user: User = Depends(get_current_user_dependency),
):
    """
    Initiate Threads OAuth flow.

    Returns authorization URL to redirect user to Threads consent screen.
    """
    try:
        # Generate secure state parameter
        state = secrets.token_urlsafe(32)
        oauth_states[state] = {
            "created_at": datetime.utcnow(),
            "user_id": user.id,
            "platform": "threads",
            "return_url": return_url,
        }

        # Clean up old states
        current_time = datetime.utcnow()
        expired_states = [
            s
            for s, data in oauth_states.items()
            if (current_time - data["created_at"]).total_seconds() > 600
        ]
        for s in expired_states:
            del oauth_states[s]

        # Get authorization URL
        auth_url = get_threads_auth_url(state)

        logger.info(f"Generated Threads OAuth URL for user {user.id}")

        return {"success": True, "authorization_url": auth_url, "platform": "threads"}

    except ValueError as e:
        logger.error(f"Threads OAuth not configured: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Threads OAuth is not configured on this server",
        )
    except Exception as e:
        logger.error(f"Error generating Threads OAuth URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while initiating OAuth",
        )


@router.get("/threads/callback")
async def threads_callback(
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Handle Threads OAuth callback.

    Exchanges authorization code for long-lived access token and creates connection.
    """
    try:
        # Validate state parameter
        if state not in oauth_states:
            logger.warning("Invalid OAuth state parameter")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter. Please try again.",
            )

        # Get state data
        state_data = oauth_states[state]
        user_id = state_data["user_id"]
        return_url = state_data.get("return_url")
        del oauth_states[state]

        # Exchange code for short-lived token
        tokens = await exchange_threads_code(code)
        if not tokens:
            logger.error("Failed to exchange Threads code")
            if return_url:
                error_url = f"{return_url}?error=oauth_failed&platform=threads"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to authenticate with Threads",
            )

        # Exchange for long-lived token
        short_lived_token = tokens["access_token"]
        long_lived_tokens = await exchange_threads_long_lived_token(short_lived_token)

        if not long_lived_tokens:
            logger.error("Failed to exchange Threads long-lived token")
            if return_url:
                error_url = f"{return_url}?error=token_exchange_failed&platform=threads"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain long-lived token from Threads",
            )

        # Get user info
        access_token = long_lived_tokens["access_token"]
        user_info = await get_threads_user_info(access_token)

        if not user_info:
            logger.error("Failed to get Threads user info")
            if return_url:
                error_url = f"{return_url}?error=incomplete_data&platform=threads"
                return RedirectResponse(url=error_url)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information from Threads",
            )

        # Create connection
        manager = SocialConnectionManager(db)
        connection = manager.create_connection(
            user_id=user_id,
            platform="threads",
            access_token=long_lived_tokens["access_token"],
            refresh_token=None,  # Threads uses token refresh via access token
            expires_in=long_lived_tokens.get("expires_in"),
            scope=None,
            platform_user_id=user_info.get("id"),
            platform_username=user_info.get("username"),
            metadata=user_info,
        )

        logger.info(f"Threads connection created for user {user_id}")

        # Redirect to frontend
        if return_url:
            success_url = f"{return_url}?success=true&platform=threads&username={user_info.get('username', '')}"
            return RedirectResponse(url=success_url)

        return {
            "success": True,
            "message": "Threads account connected successfully",
            "platform": "threads",
            "username": user_info.get("username"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Threads OAuth callback: {str(e)}")
        if "return_url" in locals() and return_url:
            error_url = f"{return_url}?error=server_error&platform=threads"
            return RedirectResponse(url=error_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during OAuth authentication",
        )


# ============================================================================
# Connection Management Endpoints
# ============================================================================


@router.get("/connections", response_model=List[ConnectionResponse])
async def get_connections(
    user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Get all social media connections for the current user.

    Returns list of connected platforms with their status.
    """
    try:
        manager = SocialConnectionManager(db)
        connections = manager.get_all_connections(user.id, active_only=True)

        # Convert to response format
        response = []
        for conn in connections:
            from utils.social_oauth import is_token_expired

            response.append(
                ConnectionResponse(
                    id=conn.id,
                    platform=conn.platform,
                    platform_username=conn.platform_username,
                    platform_user_id=conn.platform_user_id,
                    is_active=conn.is_active,
                    expires_at=conn.expires_at,
                    is_expired=is_token_expired(conn.expires_at),
                    can_refresh=conn.encrypted_refresh_token is not None,
                    last_used_at=conn.last_used_at,
                    error_message=conn.error_message,
                    created_at=conn.created_at,
                )
            )

        return response

    except Exception as e:
        logger.error(f"Error getting connections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve connections",
        )


@router.get("/{platform}/status", response_model=ConnectionStatusResponse)
async def get_connection_status(
    platform: str, user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Get detailed status of a specific platform connection.

    Args:
        platform: Platform name (linkedin, twitter, threads)

    Returns:
        Connection status details
    """
    try:
        if platform not in ["linkedin", "twitter", "threads"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid platform. Must be: linkedin, twitter, or threads",
            )

        manager = SocialConnectionManager(db)
        status_info = manager.get_connection_status(user.id, platform)

        return ConnectionStatusResponse(**status_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting connection status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve connection status",
        )


@router.delete("/{platform}/disconnect", response_model=StandardResponse)
async def disconnect_platform(
    platform: str, user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Disconnect a social media platform.

    Args:
        platform: Platform name (linkedin, twitter, threads)

    Returns:
        Success response
    """
    try:
        if platform not in ["linkedin", "twitter", "threads"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid platform. Must be: linkedin, twitter, or threads",
            )

        manager = SocialConnectionManager(db)
        success = manager.disconnect(user.id, platform)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"No {platform} connection found"
            )

        return StandardResponse(
            success=True, message=f"{platform.capitalize()} account disconnected successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting platform: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect platform",
        )


@router.post("/{platform}/refresh", response_model=StandardResponse)
async def refresh_platform_token(
    platform: str, user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Manually refresh a platform's OAuth token.

    Args:
        platform: Platform name (linkedin, twitter, threads)

    Returns:
        Success response
    """
    try:
        if platform not in ["linkedin", "twitter", "threads"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid platform. Must be: linkedin, twitter, or threads",
            )

        manager = SocialConnectionManager(db)
        connection = manager.get_connection(user.id, platform, auto_refresh=False)

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"No {platform} connection found"
            )

        success = manager.refresh_connection(connection)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to refresh {platform} token. You may need to reconnect.",
            )

        return StandardResponse(
            success=True, message=f"{platform.capitalize()} token refreshed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to refresh token"
        )


# ============================================================================
# Publishing Endpoint (Integration with Posts API)
# ============================================================================


@router.post("/publish", response_model=PublishResponse)
async def publish_to_platforms(
    request: PublishRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Publish a post to selected social media platforms.

    This endpoint integrates with the existing /api/posts system to publish
    generated content to connected social media accounts.

    Args:
        request: Post ID and list of platforms to publish to

    Returns:
        Publishing results for each platform
    """
    try:
        # Get the post
        post = db.query(Post).filter(Post.id == request.post_id, Post.user_id == user.id).first()

        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        # Validate platforms
        valid_platforms = ["linkedin", "twitter", "threads"]
        invalid = [p for p in request.platforms if p not in valid_platforms]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid platforms: {', '.join(invalid)}",
            )

        manager = SocialConnectionManager(db)
        results = {}
        errors = {}

        # Publish to each platform
        for platform in request.platforms:
            try:
                # Get connection with auto-refresh
                connection = manager.get_connection(user.id, platform, auto_refresh=True)

                if not connection:
                    errors[
                        platform
                    ] = f"No {platform} connection found. Please connect your account first."
                    continue

                # Get decrypted access token
                access_token = manager.get_decrypted_token(connection)
                if not access_token:
                    errors[platform] = f"Failed to decrypt {platform} token"
                    continue

                # Get content for platform
                content = None
                publisher = None

                if platform == "linkedin":
                    content = post.linkedin_content
                    publisher = LinkedInPublisher()
                elif platform == "twitter":
                    content = post.twitter_content
                    publisher = TwitterPublisher()
                elif platform == "threads":
                    content = post.threads_content
                    publisher = ThreadsPublisher()

                if not content:
                    errors[platform] = f"No content generated for {platform}"
                    continue

                # Publish to platform (ACTUAL PUBLISHING)
                try:
                    result = await publisher.publish(content, access_token)

                    # Create social media post record
                    social_post = SocialMediaPost(
                        post_id=post.id,
                        user_id=user.id,
                        connection_id=connection.id,
                        platform=platform,
                        content=content,
                        status="published",
                        platform_post_id=result.get("platform_post_id"),
                        platform_url=result.get("platform_url"),
                        published_at=datetime.utcnow(),
                    )
                    db.add(social_post)

                    results[platform] = {
                        "success": True,
                        "platform": platform,
                        "message": f"Published to {platform}",
                        "platform_url": result.get("platform_url"),
                    }

                    logger.info(f"Published post {post.id} to {platform} for user {user.id}")

                except (
                    AuthenticationException,
                    RateLimitException,
                    PublishingException,
                ) as publish_error:
                    logger.error(f"Error publishing to {platform}: {str(publish_error)}")
                    errors[platform] = str(publish_error)

                    # Create failed social media post record
                    social_post = SocialMediaPost(
                        post_id=post.id,
                        user_id=user.id,
                        connection_id=connection.id,
                        platform=platform,
                        content=content,
                        status="failed",
                        error_message=str(publish_error),
                        created_at=datetime.utcnow(),
                    )
                    db.add(social_post)

            except Exception as e:
                logger.error(f"Error preparing to publish to {platform}: {str(e)}")
                errors[platform] = str(e)

        # Update post status
        if results and not errors:
            post.status = "published"
            post.published_at = datetime.utcnow()
        elif errors and not results:
            post.status = "failed"
            post.error_message = "; ".join([f"{k}: {v}" for k, v in errors.items()])
        else:
            post.status = "partially_published"

        db.commit()

        return PublishResponse(
            success=bool(results), results=results, errors=errors if errors else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing post: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to publish post"
        )
