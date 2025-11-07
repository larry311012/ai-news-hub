"""
Setup Guide API Endpoints

This module provides comprehensive API endpoints for guiding users through
social media account setup (Twitter, LinkedIn, Instagram, Threads).

Features:
- Setup progress tracking
- Credential validation (without saving)
- Platform configuration helpers
- Environment variable checks
- Test connection endpoints
- Setup analytics
- Error recovery

Security:
- Rate limiting on validation endpoints
- Never expose actual secrets
- Authenticated users only
- Request logging for audit
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import os
import secrets

from database import get_db, User
from database_setup_guide import (
    SetupProgress, SetupValidation, SetupMetrics, PlatformConfiguration
)
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.rate_limiter import RateLimiter
from utils.social_connection_manager import SocialConnectionManager

# Import OAuth utility functions
from utils.social_oauth import (
    get_linkedin_auth_url,
    get_twitter_auth_url,
    get_threads_auth_url,
)
from utils.instagram_oauth import (
    get_authorization_url as get_instagram_auth_url,
    is_instagram_configured,
    get_instagram_config_status
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================================
# Pydantic Models
# ============================================================================

class SetupStatusResponse(BaseModel):
    """Response model for setup status"""
    twitter: Dict[str, Any]
    linkedin: Dict[str, Any]
    instagram: Dict[str, Any]
    threads: Dict[str, Any]


class ValidationRequest(BaseModel):
    """Request model for credential validation"""
    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1)
    redirect_uri: Optional[str] = None


class ValidationResponse(BaseModel):
    """Response model for validation results"""
    valid: bool
    message: str
    warnings: Optional[List[str]] = None
    details: Optional[Dict[str, Any]] = None


class PlatformConfigResponse(BaseModel):
    """Response model for platform configuration"""
    platform: str
    redirect_uri: str
    oauth_version: str
    required_permissions: List[str]
    developer_portal_url: str
    documentation_url: str
    setup_steps: List[Dict[str, Any]]


class EnvCheckResponse(BaseModel):
    """Response model for environment variable check"""
    twitter: Dict[str, str]
    linkedin: Dict[str, str]
    instagram: Dict[str, str]
    threads: Dict[str, str]


class StandardResponse(BaseModel):
    """Standard API response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# ============================================================================
# Setup Status Tracking
# ============================================================================

@router.get("/setup/status", response_model=SetupStatusResponse)
async def get_setup_status(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive setup status for all platforms.

    Returns current progress, connected accounts, and errors for each platform.

    Returns:
        {
            "twitter": {
                "status": "not_started" | "in_progress" | "completed" | "error",
                "current_step": 2,
                "total_steps": 5,
                "last_updated": "2025-10-23T10:00:00Z",
                "error_message": null,
                "connected_as": "@username"
            },
            "linkedin": { ... },
            "instagram": { ... },
            "threads": { ... }
        }
    """
    try:
        platforms = ["twitter", "linkedin", "instagram", "threads"]
        status_data = {}
        manager = SocialConnectionManager(db)

        for platform in platforms:
            # Check if connection exists (setup completed)
            connection_status = manager.get_connection_status(user.id, platform)

            # Get setup progress (if in progress)
            progress = db.query(SetupProgress).filter(
                SetupProgress.user_id == user.id,
                SetupProgress.platform == platform
            ).first()

            if connection_status["connected"]:
                # Setup completed - return connection info
                status_data[platform] = {
                    "status": "completed",
                    "current_step": progress.total_steps if progress else 5,
                    "total_steps": progress.total_steps if progress else 5,
                    "last_updated": connection_status.get("last_used"),
                    "error_message": None,
                    "connected_as": connection_status.get("username"),
                    "completed_at": progress.completed_at.isoformat() if progress and progress.completed_at else None
                }
            elif progress:
                # Setup in progress
                status_data[platform] = {
                    "status": progress.status,
                    "current_step": progress.current_step,
                    "total_steps": progress.total_steps,
                    "last_updated": progress.last_activity_at.isoformat(),
                    "error_message": progress.error_log,
                    "connected_as": None,
                    "started_at": progress.started_at.isoformat() if progress.started_at else None
                }
            else:
                # Not started
                status_data[platform] = {
                    "status": "not_started",
                    "current_step": 0,
                    "total_steps": 5,
                    "last_updated": None,
                    "error_message": None,
                    "connected_as": None
                }

        return SetupStatusResponse(**status_data)

    except Exception as e:
        logger.error(f"Error getting setup status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve setup status"
        )


@router.post("/setup/progress/{platform}")
async def update_setup_progress(
    platform: str,
    current_step: int,
    step_status: str = "in_progress",
    error_message: Optional[str] = None,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Update setup progress for a platform.

    Used by frontend to track user progress through setup wizard.

    Args:
        platform: Platform name (twitter, linkedin, instagram, threads)
        current_step: Current step number
        step_status: Status (in_progress, completed, error)
        error_message: Optional error message

    Returns:
        Updated progress object
    """
    try:
        if platform not in ["twitter", "linkedin", "instagram", "threads"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid platform"
            )

        # Get or create progress record
        progress = db.query(SetupProgress).filter(
            SetupProgress.user_id == user.id,
            SetupProgress.platform == platform
        ).first()

        if not progress:
            # Create new progress record
            progress = SetupProgress(
                user_id=user.id,
                platform=platform,
                status="in_progress",
                current_step=current_step,
                total_steps=5,  # Default, can be customized per platform
                started_at=datetime.utcnow(),
                completed_steps=[]
            )
            db.add(progress)
        else:
            # Update existing progress
            progress.current_step = current_step
            progress.status = step_status
            progress.last_activity_at = datetime.utcnow()

            if error_message:
                progress.error_log = error_message
                progress.error_count += 1

            # Add to completed steps if not already there
            if step_status == "completed" and current_step not in progress.completed_steps:
                completed = progress.completed_steps or []
                completed.append(current_step)
                progress.completed_steps = completed

            # Check if all steps completed
            if current_step == progress.total_steps and step_status == "completed":
                progress.status = "completed"
                progress.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(progress)

        return {
            "success": True,
            "progress": {
                "platform": progress.platform,
                "status": progress.status,
                "current_step": progress.current_step,
                "total_steps": progress.total_steps,
                "completed_steps": progress.completed_steps,
                "error_message": progress.error_log
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating setup progress: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update progress"
        )


# ============================================================================
# Credential Validation Endpoints
# ============================================================================

@router.post("/setup/validate/{platform}", response_model=ValidationResponse)
async def validate_credentials(
    platform: str,
    request_data: ValidationRequest,
    request: Request,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Validate platform credentials without saving them.

    This endpoint allows users to test their API credentials before
    connecting their account. Rate limited to prevent brute force.

    Args:
        platform: Platform name (twitter, linkedin, instagram, threads)
        request_data: Credentials to validate

    Returns:
        Validation result with warnings and suggestions

    Rate Limit:
        10 requests per minute per user
    """
    try:
        # Validate platform
        if platform not in ["twitter", "linkedin", "instagram", "threads"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid platform. Must be: twitter, linkedin, instagram, or threads"
            )

        # Rate limiting: 10 validation attempts per minute
        rate_limit_key = f"setup_validate_{user.id}_{platform}"
        try:
            RateLimiter.check_rate_limit(str(user.id), f"setup_validate_{platform}", db, max_attempts=10, window_minutes=1)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many validation attempts. Please wait before trying again."
            )

        warnings = []
        details = {}

        # Basic validation
        if not request_data.client_id or len(request_data.client_id) < 10:
            return ValidationResponse(
                valid=False,
                message="Client ID appears invalid or too short",
                warnings=["Client ID should be at least 10 characters"]
            )

        if not request_data.client_secret or len(request_data.client_secret) < 10:
            return ValidationResponse(
                valid=False,
                message="Client Secret appears invalid or too short",
                warnings=["Client Secret should be at least 10 characters"]
            )

        # Platform-specific validation
        if platform == "twitter":
            # Twitter uses API Key/Secret
            if ":" in request_data.client_id:
                warnings.append("Twitter API Key should not contain colons")

        elif platform == "instagram":
            # Instagram uses numeric App ID
            if not request_data.client_id.isdigit():
                warnings.append("Instagram App ID should be numeric")

        # Validate redirect URI format
        if request_data.redirect_uri:
            if not request_data.redirect_uri.startswith(("http://", "https://")):
                warnings.append("Redirect URI should start with http:// or https://")

            expected_uri = get_expected_redirect_uri(platform)
            if request_data.redirect_uri != expected_uri:
                warnings.append(f"Redirect URI doesn't match server configuration. Expected: {expected_uri}")

        # Log validation attempt
        validation = SetupValidation(
            user_id=user.id,
            platform=platform,
            validation_type="credentials",
            is_valid=len(warnings) == 0,
            warnings=warnings if warnings else None,
            request_data={
                "client_id_length": len(request_data.client_id),
                "has_secret": bool(request_data.client_secret),
                "has_redirect_uri": bool(request_data.redirect_uri)
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        db.add(validation)
        db.commit()

        # Return validation results
        if warnings:
            return ValidationResponse(
                valid=False,
                message="Credentials have potential issues",
                warnings=warnings,
                details=details
            )
        else:
            return ValidationResponse(
                valid=True,
                message="Credentials appear valid. Click 'Test Connection' to verify with the platform.",
                warnings=None,
                details=details
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating credentials for {platform}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during validation"
        )


# ============================================================================
# Configuration Helper Endpoints
# ============================================================================

@router.get("/setup/config/{platform}", response_model=PlatformConfigResponse)
async def get_platform_config(
    platform: str,
    user: User = Depends(get_current_user_dependency)
):
    """
    Get platform configuration details for setup guide.

    Returns OAuth URLs, required permissions, documentation links,
    and step-by-step setup instructions.

    Args:
        platform: Platform name (twitter, linkedin, instagram, threads)

    Returns:
        Platform configuration details
    """
    try:
        if platform not in ["twitter", "linkedin", "instagram", "threads"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid platform"
            )

        # Build configuration based on platform
        config = {
            "twitter": {
                "platform": "twitter",
                "redirect_uri": os.getenv("TWITTER_CALLBACK_URL", "http://localhost:8000/api/social-media/twitter/callback"),
                "oauth_version": "2.0",
                "required_permissions": [
                    "tweet.read",
                    "tweet.write",
                    "users.read",
                    "offline.access"
                ],
                "developer_portal_url": "https://developer.twitter.com/en/portal/dashboard",
                "documentation_url": "https://developer.twitter.com/en/docs/authentication/oauth-2-0",
                "setup_steps": [
                    {
                        "step": 1,
                        "title": "Create Twitter Developer Account",
                        "description": "Sign up for a Twitter Developer account if you don't have one",
                        "url": "https://developer.twitter.com/en/portal/petition/essential/basic-info"
                    },
                    {
                        "step": 2,
                        "title": "Create a New App",
                        "description": "Create a new app in the Twitter Developer Portal",
                        "url": "https://developer.twitter.com/en/portal/apps/new"
                    },
                    {
                        "step": 3,
                        "title": "Configure OAuth 2.0",
                        "description": "Enable OAuth 2.0 and set redirect URI in app settings",
                        "url": None
                    },
                    {
                        "step": 4,
                        "title": "Get API Credentials",
                        "description": "Copy Client ID and Client Secret from app settings",
                        "url": None
                    },
                    {
                        "step": 5,
                        "title": "Test Connection",
                        "description": "Test your credentials and connect your account",
                        "url": None
                    }
                ]
            },
            "linkedin": {
                "platform": "linkedin",
                "redirect_uri": os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/api/social-media/linkedin/callback"),
                "oauth_version": "2.0",
                "required_permissions": [
                    "openid",
                    "profile",
                    "email",
                    "w_member_social"
                ],
                "developer_portal_url": "https://www.linkedin.com/developers/apps",
                "documentation_url": "https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication",
                "setup_steps": [
                    {
                        "step": 1,
                        "title": "Create LinkedIn Developer App",
                        "description": "Create a new app in LinkedIn Developer Portal",
                        "url": "https://www.linkedin.com/developers/apps/new"
                    },
                    {
                        "step": 2,
                        "title": "Request API Access",
                        "description": "Request access to 'Sign In with LinkedIn' and 'Share on LinkedIn' products",
                        "url": None
                    },
                    {
                        "step": 3,
                        "title": "Configure OAuth 2.0",
                        "description": "Add redirect URL in Auth tab",
                        "url": None
                    },
                    {
                        "step": 4,
                        "title": "Get API Credentials",
                        "description": "Copy Client ID and Client Secret from Auth tab",
                        "url": None
                    },
                    {
                        "step": 5,
                        "title": "Test Connection",
                        "description": "Test your credentials and connect your account",
                        "url": None
                    }
                ]
            },
            "instagram": {
                "platform": "instagram",
                "redirect_uri": os.getenv("INSTAGRAM_CALLBACK_URL", "http://localhost:8000/api/social-media/instagram/callback"),
                "oauth_version": "2.0",
                "required_permissions": [
                    "instagram_basic",
                    "instagram_content_publish",
                    "pages_read_engagement"
                ],
                "developer_portal_url": "https://developers.facebook.com/apps",
                "documentation_url": "https://developers.facebook.com/docs/instagram-api",
                "setup_steps": [
                    {
                        "step": 1,
                        "title": "Create Facebook Developer Account",
                        "description": "Sign up for Facebook Developer account",
                        "url": "https://developers.facebook.com/apps"
                    },
                    {
                        "step": 2,
                        "title": "Create Facebook App",
                        "description": "Create a new app and add Instagram product",
                        "url": "https://developers.facebook.com/apps/create"
                    },
                    {
                        "step": 3,
                        "title": "Convert to Business Account",
                        "description": "Convert your Instagram account to a Business account and link to Facebook Page",
                        "url": "https://help.instagram.com/502981923235522"
                    },
                    {
                        "step": 4,
                        "title": "Configure OAuth Settings",
                        "description": "Add OAuth redirect URI in Facebook App settings",
                        "url": None
                    },
                    {
                        "step": 5,
                        "title": "Get App Credentials",
                        "description": "Copy App ID and App Secret from app dashboard",
                        "url": None
                    },
                    {
                        "step": 6,
                        "title": "Test Connection",
                        "description": "Test your credentials and connect your Instagram Business account",
                        "url": None
                    }
                ]
            },
            "threads": {
                "platform": "threads",
                "redirect_uri": os.getenv("THREADS_REDIRECT_URI", "http://localhost:8000/api/social-media/threads/callback"),
                "oauth_version": "2.0",
                "required_permissions": [
                    "threads_basic",
                    "threads_content_publish"
                ],
                "developer_portal_url": "https://developers.facebook.com/apps",
                "documentation_url": "https://developers.facebook.com/docs/threads",
                "setup_steps": [
                    {
                        "step": 1,
                        "title": "Create Facebook Developer Account",
                        "description": "Sign up for Facebook Developer account",
                        "url": "https://developers.facebook.com/apps"
                    },
                    {
                        "step": 2,
                        "title": "Create Facebook App",
                        "description": "Create a new app and add Threads product",
                        "url": "https://developers.facebook.com/apps/create"
                    },
                    {
                        "step": 3,
                        "title": "Configure OAuth Settings",
                        "description": "Add OAuth redirect URI in app settings",
                        "url": None
                    },
                    {
                        "step": 4,
                        "title": "Get App Credentials",
                        "description": "Copy App ID and App Secret from app dashboard",
                        "url": None
                    },
                    {
                        "step": 5,
                        "title": "Test Connection",
                        "description": "Test your credentials and connect your Threads account",
                        "url": None
                    }
                ]
            }
        }

        return PlatformConfigResponse(**config[platform])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting platform config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve platform configuration"
        )


@router.get("/setup/env-check", response_model=EnvCheckResponse)
async def check_environment_variables(
    user: User = Depends(get_current_user_dependency)
):
    """
    Check which environment variables are configured on the server.

    Returns "set" or "missing" for each required variable, without
    exposing actual values for security.

    Returns:
        {
            "twitter": {
                "TWITTER_API_KEY": "set",
                "TWITTER_API_SECRET": "missing",
                "TWITTER_CALLBACK_URL": "set"
            },
            "linkedin": { ... },
            "instagram": { ... },
            "threads": { ... }
        }
    """
    try:
        def check_env_var(var_name: str) -> str:
            """Check if environment variable is set"""
            value = os.getenv(var_name)
            if value and len(value) > 5:  # Avoid empty or placeholder values
                return "set"
            return "missing"

        return EnvCheckResponse(
            twitter={
                "TWITTER_API_KEY": check_env_var("TWITTER_API_KEY"),
                "TWITTER_API_SECRET": check_env_var("TWITTER_API_SECRET"),
                "TWITTER_CALLBACK_URL": check_env_var("TWITTER_CALLBACK_URL")
            },
            linkedin={
                "LINKEDIN_CLIENT_ID": check_env_var("LINKEDIN_CLIENT_ID"),
                "LINKEDIN_CLIENT_SECRET": check_env_var("LINKEDIN_CLIENT_SECRET"),
                "LINKEDIN_REDIRECT_URI": check_env_var("LINKEDIN_REDIRECT_URI")
            },
            instagram={
                "INSTAGRAM_APP_ID": check_env_var("INSTAGRAM_APP_ID"),
                "INSTAGRAM_APP_SECRET": check_env_var("INSTAGRAM_APP_SECRET"),
                "INSTAGRAM_CALLBACK_URL": check_env_var("INSTAGRAM_CALLBACK_URL")
            },
            threads={
                "THREADS_CLIENT_ID": check_env_var("THREADS_CLIENT_ID"),
                "THREADS_CLIENT_SECRET": check_env_var("THREADS_CLIENT_SECRET"),
                "THREADS_REDIRECT_URI": check_env_var("THREADS_REDIRECT_URI")
            }
        )

    except Exception as e:
        logger.error(f"Error checking environment variables: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check environment configuration"
        )


# ============================================================================
# Test Connection Endpoints
# ============================================================================

@router.post("/setup/test-connection/{platform}")
async def test_connection(
    platform: str,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Test OAuth connection by initiating a temporary OAuth flow.

    This doesn't save tokens long-term, just verifies credentials work.

    Args:
        platform: Platform name (twitter, linkedin, instagram, threads)

    Returns:
        Test authorization URL and instructions
    """
    try:
        if platform not in ["twitter", "linkedin", "instagram", "threads"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid platform"
            )

        # Generate test state
        test_state = f"test_{secrets.token_urlsafe(16)}"

        # Get authorization URL based on platform
        try:
            if platform == "twitter":
                # Check if configured
                if not os.getenv("TWITTER_API_KEY") or not os.getenv("TWITTER_API_SECRET"):
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Twitter OAuth is not configured on this server"
                    )
                auth_url = get_twitter_auth_url(test_state, "test_challenge")

            elif platform == "linkedin":
                if not os.getenv("LINKEDIN_CLIENT_ID") or not os.getenv("LINKEDIN_CLIENT_SECRET"):
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="LinkedIn OAuth is not configured on this server"
                    )
                auth_url = get_linkedin_auth_url(test_state)

            elif platform == "instagram":
                if not is_instagram_configured():
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Instagram OAuth is not configured on this server"
                    )
                auth_url = get_instagram_auth_url(test_state)

            elif platform == "threads":
                if not os.getenv("THREADS_CLIENT_ID") or not os.getenv("THREADS_CLIENT_SECRET"):
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Threads OAuth is not configured on this server"
                    )
                auth_url = get_threads_auth_url(test_state)

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{platform.capitalize()} OAuth is not properly configured: {str(e)}"
            )

        return {
            "success": True,
            "platform": platform,
            "message": "Test connection initiated",
            "authorization_url": auth_url,
            "instructions": "Click the authorization URL to test your OAuth configuration. You'll be redirected back to confirm the connection works."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing connection for {platform}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate test connection"
        )


# ============================================================================
# Error Recovery Endpoints
# ============================================================================

@router.post("/setup/reset/{platform}", response_model=StandardResponse)
async def reset_setup_progress(
    platform: str,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Reset setup progress for a platform.

    Allows users to start over if they encounter errors or want to
    reconfigure their connection.

    Args:
        platform: Platform name (twitter, linkedin, instagram, threads)

    Returns:
        Success response
    """
    try:
        if platform not in ["twitter", "linkedin", "instagram", "threads"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid platform"
            )

        # Find and reset progress
        progress = db.query(SetupProgress).filter(
            SetupProgress.user_id == user.id,
            SetupProgress.platform == platform
        ).first()

        if progress:
            # Reset to initial state
            progress.status = "not_started"
            progress.current_step = 0
            progress.completed_steps = []
            progress.error_log = None
            progress.error_count = 0
            progress.validation_results = None
            progress.started_at = None
            progress.completed_at = None
            progress.last_activity_at = datetime.utcnow()

            db.commit()

            logger.info(f"Reset setup progress for {platform} for user {user.id}")

        return StandardResponse(
            success=True,
            message=f"{platform.capitalize()} setup progress has been reset"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting setup progress: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset setup progress"
        )


# ============================================================================
# Setup Analytics Endpoints
# ============================================================================

@router.get("/setup/analytics/{platform}")
async def get_setup_analytics(
    platform: str,
    days: int = 30,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get setup analytics for a platform.

    Returns completion rates, average time, common errors, and drop-off points.
    Admin-only endpoint for improving setup experience.

    Args:
        platform: Platform name (twitter, linkedin, instagram, threads)
        days: Number of days to look back (default 30)

    Returns:
        Analytics data
    """
    try:
        # Check if user is admin
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        if platform not in ["twitter", "linkedin", "instagram", "threads"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid platform"
            )

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Get completion stats
        total_started = db.query(SetupProgress).filter(
            SetupProgress.platform == platform,
            SetupProgress.created_at >= start_date
        ).count()

        total_completed = db.query(SetupProgress).filter(
            SetupProgress.platform == platform,
            SetupProgress.status == "completed",
            SetupProgress.created_at >= start_date
        ).count()

        total_errors = db.query(SetupProgress).filter(
            SetupProgress.platform == platform,
            SetupProgress.status == "error",
            SetupProgress.created_at >= start_date
        ).count()

        # Calculate average completion time
        completed_setups = db.query(SetupProgress).filter(
            SetupProgress.platform == platform,
            SetupProgress.status == "completed",
            SetupProgress.created_at >= start_date,
            SetupProgress.started_at.isnot(None),
            SetupProgress.completed_at.isnot(None)
        ).all()

        completion_times = []
        for setup in completed_setups:
            duration = (setup.completed_at - setup.started_at).total_seconds()
            completion_times.append(duration)

        avg_time = sum(completion_times) / len(completion_times) if completion_times else 0

        # Get common errors
        error_setups = db.query(SetupProgress).filter(
            SetupProgress.platform == platform,
            SetupProgress.error_log.isnot(None),
            SetupProgress.created_at >= start_date
        ).all()

        error_counts = {}
        for setup in error_setups:
            error = setup.error_log[:100]  # Truncate for grouping
            error_counts[error] = error_counts.get(error, 0) + 1

        common_errors = [
            {"error": error, "count": count}
            for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return {
            "platform": platform,
            "period_days": days,
            "total_started": total_started,
            "total_completed": total_completed,
            "total_errors": total_errors,
            "completion_rate": round(total_completed / total_started * 100, 2) if total_started > 0 else 0,
            "avg_completion_time_seconds": round(avg_time, 2),
            "avg_completion_time_minutes": round(avg_time / 60, 2),
            "common_errors": common_errors
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting setup analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics"
        )


# ============================================================================
# Helper Functions
# ============================================================================

def get_expected_redirect_uri(platform: str) -> str:
    """Get the expected redirect URI for a platform"""
    uris = {
        "twitter": os.getenv("TWITTER_CALLBACK_URL", "http://localhost:8000/api/social-media/twitter/callback"),
        "linkedin": os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/api/social-media/linkedin/callback"),
        "instagram": os.getenv("INSTAGRAM_CALLBACK_URL", "http://localhost:8000/api/social-media/instagram/callback"),
        "threads": os.getenv("THREADS_REDIRECT_URI", "http://localhost:8000/api/social-media/threads/callback")
    }
    return uris.get(platform, "")
