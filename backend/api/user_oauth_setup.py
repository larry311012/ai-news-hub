"""
Per-User OAuth Setup API

This module provides endpoints for users to set up their own OAuth credentials
(Twitter API Key/Secret, LinkedIn Client ID/Secret, etc.) instead of relying on
centralized admin credentials.

Endpoints:
- POST /api/oauth-setup/{platform}/credentials - Save user's API credentials
- GET /api/oauth-setup/{platform}/credentials - Get user's credential status (masked)
- DELETE /api/oauth-setup/{platform}/credentials - Remove user's credentials
- POST /api/oauth-setup/{platform}/test - Test credential validity
- GET /api/oauth-setup/{platform}/callback-url - Get callback URL for user's app

Security:
- All endpoints require user authentication
- Credentials are encrypted at rest using AES-256
- API responses only return masked credentials
- Rate limiting prevents brute force attacks
- Audit trail tracks all credential operations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from database import get_db, User
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.user_oauth_credential_manager import UserOAuthCredentialManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class SaveCredentialsRequest(BaseModel):
    """Request model for saving user's OAuth credentials"""

    # OAuth 1.0a fields (Twitter)
    api_key: Optional[str] = Field(None, description="OAuth 1.0a API Key (Consumer Key)")
    api_secret: Optional[str] = Field(None, description="OAuth 1.0a API Secret (Consumer Secret)")
    callback_url: Optional[str] = Field(None, description="OAuth 1.0a callback URL")

    # OAuth 2.0 fields (LinkedIn, Threads)
    client_id: Optional[str] = Field(None, description="OAuth 2.0 Client ID")
    client_secret: Optional[str] = Field(None, description="OAuth 2.0 Client Secret")
    redirect_uri: Optional[str] = Field(None, description="OAuth 2.0 redirect URI")
    scopes: Optional[list] = Field(None, description="OAuth 2.0 scopes")

    @field_validator('api_key', 'api_secret', 'client_id', 'client_secret')
    @classmethod
    def validate_no_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Trim whitespace from credentials"""
        if v:
            return v.strip()
        return v

    class Config:
        schema_extra = {
            "example": {
                "api_key": "abc123xyz789...",
                "api_secret": "secret123...",
                "callback_url": "http://localhost:8000/api/oauth-setup/twitter/callback"
            }
        }


class CredentialStatusResponse(BaseModel):
    """Response model for credential status"""
    configured: bool
    platform: str
    oauth_version: str
    is_validated: bool
    validation_status: Optional[str]
    last_validated_at: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    usage_count: Optional[int]
    masked_credentials: Dict[str, Any]

    class Config:
        schema_extra = {
            "example": {
                "configured": True,
                "platform": "twitter",
                "oauth_version": "1.0a",
                "is_validated": True,
                "validation_status": "success",
                "last_validated_at": "2025-10-18T10:00:00Z",
                "created_at": "2025-10-18T09:00:00Z",
                "updated_at": "2025-10-18T09:00:00Z",
                "usage_count": 5,
                "masked_credentials": {
                    "api_key": "abc123••••••••",
                    "api_secret": "••••••••••••",
                    "callback_url": "http://localhost:8000/api/oauth-setup/twitter/callback"
                }
            }
        }


class TestCredentialsResponse(BaseModel):
    """Response model for credential testing"""
    success: bool
    message: str
    platform: str
    tested_at: str

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Twitter credentials validated successfully",
                "platform": "twitter",
                "tested_at": "2025-10-18T10:30:00Z"
            }
        }


class CallbackUrlResponse(BaseModel):
    """Response model for callback URL"""
    platform: str
    oauth_version: str
    callback_url: str
    instructions: str

    class Config:
        schema_extra = {
            "example": {
                "platform": "twitter",
                "oauth_version": "1.0a",
                "callback_url": "http://localhost:8000/api/oauth-setup/twitter/callback",
                "instructions": "Use this URL as the Callback URL in your Twitter Developer App settings"
            }
        }


# ============================================================================
# Helper Functions
# ============================================================================

def get_user_manager(
    request: Request,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
) -> UserOAuthCredentialManager:
    """Get credential manager for current user"""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return UserOAuthCredentialManager(db, user.id, ip_address, user_agent)


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "/oauth-setup/{platform}/credentials",
    summary="Save OAuth credentials",
    description="Save your own OAuth credentials for connecting to social media platforms"
)
async def save_oauth_credentials(
    platform: str,
    credentials: SaveCredentialsRequest,
    manager: UserOAuthCredentialManager = Depends(get_user_manager)
):
    """
    Save user's OAuth credentials.

    Users provide their own Twitter API Key + Secret (or LinkedIn/Threads credentials)
    which are encrypted and stored securely. When the user connects their account,
    the system uses THEIR credentials instead of centralized admin credentials.

    Args:
        platform: Platform name (twitter, linkedin, threads)
        credentials: OAuth credentials (API key/secret or client ID/secret)
        manager: Credential manager dependency

    Returns:
        Success response with platform info

    Raises:
        HTTPException: If validation fails or credentials are invalid
    """
    try:
        platform = platform.lower()

        # Validate platform
        if platform not in manager.SUPPORTED_PLATFORMS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform: {platform}. Supported: twitter, linkedin, threads"
            )

        platform_info = manager.SUPPORTED_PLATFORMS[platform]

        # Save credentials
        cred = manager.save_credentials(
            platform=platform,
            api_key=credentials.api_key,
            api_secret=credentials.api_secret,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            callback_url=credentials.callback_url,
            redirect_uri=credentials.redirect_uri,
            scopes=credentials.scopes
        )

        logger.info(f"User {manager.user_id} saved {platform} credentials")

        return {
            "success": True,
            "message": f"{platform_info['name']} credentials saved successfully",
            "platform": platform,
            "oauth_version": cred.oauth_version,
            "next_step": f"Test your credentials by calling POST /api/oauth-setup/{platform}/test"
        }

    except ValueError as e:
        logger.warning(f"Validation error saving credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving credentials"
        )


@router.get(
    "/oauth-setup/{platform}/credentials",
    response_model=CredentialStatusResponse,
    summary="Get credential status",
    description="Get your OAuth credential status with masked values"
)
async def get_oauth_credential_status(
    platform: str,
    manager: UserOAuthCredentialManager = Depends(get_user_manager)
):
    """
    Get user's OAuth credential status.

    Returns masked credentials for security (e.g., "abc123••••••••").
    Shows validation status and usage statistics.

    Args:
        platform: Platform name (twitter, linkedin, threads)
        manager: Credential manager dependency

    Returns:
        Credential status with masked values

    Raises:
        HTTPException: If platform not supported
    """
    try:
        platform = platform.lower()

        # Validate platform
        if platform not in manager.SUPPORTED_PLATFORMS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Platform '{platform}' not supported. Supported platforms: twitter, linkedin, threads"
            )

        status_info = manager.get_credential_status(platform)

        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve credential status"
            )

        return status_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting credential status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving credential status"
        )


@router.delete(
    "/oauth-setup/{platform}/credentials",
    summary="Delete OAuth credentials",
    description="Remove your OAuth credentials for a platform"
)
async def delete_oauth_credentials(
    platform: str,
    manager: UserOAuthCredentialManager = Depends(get_user_manager)
):
    """
    Delete user's OAuth credentials.

    Permanently removes stored credentials. You will need to set up
    credentials again before connecting to this platform.

    Args:
        platform: Platform name (twitter, linkedin, threads)
        manager: Credential manager dependency

    Returns:
        Success response

    Raises:
        HTTPException: If credentials not found
    """
    try:
        platform = platform.lower()

        # Validate platform
        if platform not in manager.SUPPORTED_PLATFORMS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform: {platform}"
            )

        deleted = manager.delete_credentials(platform)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No credentials found for {platform}"
            )

        # Also disconnect/delete the OAuth connection for this platform
        # This ensures the platform shows as disconnected in the UI
        try:
            from sqlalchemy import text
            from database import get_db as get_database_session

            db = next(get_database_session())
            try:
                # Delete from social_media_connections table
                db.execute(
                    text("DELETE FROM social_media_connections WHERE user_id = :user_id AND platform = :platform"),
                    {"user_id": manager.user_id, "platform": platform}
                )
                db.commit()
                logger.info(f"Disconnected {platform} OAuth connection for user {manager.user_id}")
            finally:
                db.close()
        except Exception as conn_error:
            # Log but don't fail the whole operation if connection deletion fails
            logger.warning(f"Failed to delete OAuth connection for {platform}: {str(conn_error)}")

        logger.info(f"User {manager.user_id} deleted {platform} credentials")

        return {
            "success": True,
            "message": f"{platform.title()} credentials removed successfully",
            "platform": platform
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting credentials"
        )


@router.post(
    "/oauth-setup/{platform}/test",
    response_model=TestCredentialsResponse,
    summary="Test OAuth credentials",
    description="Test if your OAuth credentials are valid"
)
async def test_oauth_credentials(
    platform: str,
    manager: UserOAuthCredentialManager = Depends(get_user_manager)
):
    """
    Test user's OAuth credentials.

    Validates credential format and tests OAuth signature generation
    (for Twitter) or format validation (for LinkedIn/Threads).

    Args:
        platform: Platform name (twitter, linkedin, threads)
        manager: Credential manager dependency

    Returns:
        Test result with success status and message

    Raises:
        HTTPException: If credentials not found or test fails
    """
    try:
        platform = platform.lower()

        # Validate platform
        if platform not in manager.SUPPORTED_PLATFORMS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform: {platform}"
            )

        # Test credentials
        success, message = await manager.test_credentials(platform)

        logger.info(f"User {manager.user_id} tested {platform} credentials: {success}")

        return {
            "success": success,
            "message": message,
            "platform": platform,
            "tested_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while testing credentials: {str(e)}"
        )


@router.get(
    "/oauth-setup/{platform}/test-credentials",
    response_model=TestCredentialsResponse,
    summary="Test OAuth credentials (GET version)",
    description="Test if your OAuth credentials can be decrypted and validated (GET endpoint for frontend compatibility)"
)
async def test_oauth_credentials_get(
    platform: str,
    manager: UserOAuthCredentialManager = Depends(get_user_manager)
):
    """
    Test user's OAuth credentials (GET version).

    This is the same as POST /oauth-setup/{platform}/test but using GET method
    for easier frontend integration. Tests credential decryption and OAuth signature
    generation (for Twitter) or format validation (for LinkedIn/Threads).

    Args:
        platform: Platform name (twitter, linkedin, threads)
        manager: Credential manager dependency

    Returns:
        Test result with success status and message

    Raises:
        HTTPException: If credentials not found or test fails
    """
    try:
        platform = platform.lower()

        # Validate platform
        if platform not in manager.SUPPORTED_PLATFORMS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform: {platform}"
            )

        # Test credentials
        success, message = await manager.test_credentials(platform)

        logger.info(f"User {manager.user_id} tested {platform} credentials (GET): {success}")

        return {
            "success": success,
            "message": message,
            "platform": platform,
            "tested_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing credentials (GET): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while testing credentials: {str(e)}"
        )

@router.get(
    "/oauth-setup/{platform}/callback-url",
    response_model=CallbackUrlResponse,
    summary="Get callback URL",
    description="Get the callback URL to use in your developer app settings"
)
async def get_callback_url(platform: str, request: Request):
    """
    Get the callback URL for user's OAuth app.

    This endpoint tells users what callback URL to use when setting up
    their Twitter/LinkedIn/Threads developer app.

    Args:
        platform: Platform name (twitter, linkedin, threads)
        request: FastAPI request object

    Returns:
        Callback URL and setup instructions

    Raises:
        HTTPException: If platform not supported
    """
    try:
        platform = platform.lower()

        # Supported platforms
        platforms = {
            "twitter": {
                "oauth_version": "1.0a",
                "callback_url": f"{request.url.scheme}://{request.url.netloc}/api/oauth-setup/twitter/callback",
                "instructions": "Use this URL as the 'Callback URL' in your Twitter Developer App settings under 'Authentication settings'"
            },
            "linkedin": {
                "oauth_version": "2.0",
                "callback_url": f"{request.url.scheme}://{request.url.netloc}/api/oauth-setup/linkedin/callback",
                "instructions": "Use this URL as the 'Redirect URL' in your LinkedIn App settings under 'Auth' tab"
            },
            "threads": {
                "oauth_version": "2.0",
                "callback_url": f"{request.url.scheme}://{request.url.netloc}/api/oauth-setup/threads/callback",
                "instructions": "Use this URL as the 'Valid OAuth Redirect URIs' in your Threads App settings"
            }
        }

        if platform not in platforms:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Platform '{platform}' not supported. Supported platforms: twitter, linkedin, threads"
            )

        return {
            "platform": platform,
            **platforms[platform]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting callback URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving callback URL"
        )


# ============================================================================
# OAuth Callback Endpoints (Per-User Flow)
# ============================================================================

# COMMENTED OUT: This placeholder route conflicts with specific implementations
# (e.g., social_media_linkedin.py). Since LinkedIn OAuth callback is now fully
# implemented in a separate router, this generic placeholder is no longer needed
# and was preventing the specific route from being matched.
#
# If you need to add placeholders for other platforms in the future, consider:
# 1. Using a different path pattern (e.g., /oauth-setup/{platform}/callback-placeholder)
# 2. Registering platform-specific routers BEFORE this generic router
# 3. Excluding implemented platforms from this route (e.g., if platform != "linkedin")
#
# @router.get("/oauth-setup/{platform}/callback")
# async def oauth_callback_placeholder(platform: str):
#     """
#     Placeholder for OAuth callback endpoint.
#
#     This endpoint will be implemented in the next phase to handle
#     OAuth callbacks using per-user credentials.
#
#     For now, it returns a helpful message directing users to the
#     existing centralized OAuth flow.
#     """
#     return {
#         "message": f"Per-user {platform} OAuth callback not yet implemented",
#         "status": "coming_soon",
#         "platform": platform,
#         "alternative": f"Please use the centralized OAuth flow at /api/social-media/{platform}-oauth1/connect for now"
#     }
