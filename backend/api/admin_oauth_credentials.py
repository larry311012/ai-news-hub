"""
Admin OAuth Credentials API

This module provides admin-only endpoints for managing OAuth platform credentials
through a web UI instead of editing .env files.

Endpoints:
- GET /api/admin/oauth-credentials - List all platforms
- GET /api/admin/oauth-credentials/{platform} - Get single platform
- POST /api/admin/oauth-credentials/{platform} - Create/update credentials
- DELETE /api/admin/oauth-credentials/{platform} - Delete credentials
- POST /api/admin/oauth-credentials/{platform}/test - Test connection
- GET /api/oauth-credentials/status - Public status endpoint (no auth)

Security:
- All admin endpoints require authentication AND admin privileges
- Credentials are encrypted at rest using AES-256
- API responses only return masked credentials
- Audit trail tracks who created/updated credentials
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from database import get_db, User
from database_oauth_credentials import OAuthPlatformCredential
from utils.oauth_credential_manager import OAuthCredentialManager
from middleware.admin_auth import require_admin, get_admin_user_id

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class OAuthCredentialCreate(BaseModel):
    """Request model for creating/updating OAuth credentials"""

    oauth_version: str = Field(..., description="OAuth version (1.0a or 2.0)")

    # OAuth 1.0a fields (Twitter)
    api_key: Optional[str] = Field(None, description="OAuth 1.0a API Key (Consumer Key)")
    api_secret: Optional[str] = Field(None, description="OAuth 1.0a API Secret (Consumer Secret)")
    callback_url: Optional[str] = Field(None, description="OAuth 1.0a callback URL")

    # OAuth 2.0 fields (LinkedIn, Threads)
    client_id: Optional[str] = Field(None, description="OAuth 2.0 Client ID")
    client_secret: Optional[str] = Field(None, description="OAuth 2.0 Client Secret")
    redirect_uri: Optional[str] = Field(None, description="OAuth 2.0 redirect URI")
    scopes: Optional[List[str]] = Field(None, description="OAuth 2.0 scopes")

    is_active: bool = Field(True, description="Whether credentials are active")

    class Config:
        schema_extra = {
            "example": {
                "oauth_version": "1.0a",
                "api_key": "abc123xyz789...",
                "api_secret": "secret123...",
                "callback_url": "http://localhost:8000/api/social-media/twitter-oauth1/callback",
            }
        }


class OAuthCredentialResponse(BaseModel):
    """Response model for OAuth credentials (with masked sensitive data)"""

    platform: str
    oauth_version: str
    is_configured: bool
    is_active: bool
    last_tested_at: Optional[datetime]
    test_status: Optional[str]
    test_error_message: Optional[str]

    # Masked credentials
    masked_credentials: Dict[str, Any]

    # Metadata
    updated_at: Optional[datetime]
    updated_by_email: Optional[str]
    source: Optional[str]  # "database" or "env"

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "platform": "twitter",
                "oauth_version": "1.0a",
                "is_configured": True,
                "is_active": True,
                "last_tested_at": "2025-10-17T21:00:00Z",
                "test_status": "success",
                "test_error_message": None,
                "masked_credentials": {
                    "api_key": "abc123••••••••",
                    "api_secret": "••••••••••••",
                    "callback_url": "http://localhost:8000/api/social-media/twitter-oauth1/callback",
                },
                "updated_at": "2025-10-17T20:00:00Z",
                "updated_by_email": "admin@example.com",
                "source": "database",
            }
        }


class TestConnectionResponse(BaseModel):
    """Response model for connection testing"""

    success: bool
    message: str
    platform: str
    tested_at: datetime

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Twitter credentials validated successfully",
                "platform": "twitter",
                "tested_at": "2025-10-17T21:30:00Z",
            }
        }


class PublicStatusResponse(BaseModel):
    """Response model for public status endpoint"""

    twitter: Dict[str, Any]
    linkedin: Dict[str, Any]
    threads: Dict[str, Any]

    class Config:
        schema_extra = {
            "example": {
                "twitter": {"configured": True, "oauth_version": "1.0a"},
                "linkedin": {"configured": False, "oauth_version": "2.0"},
                "threads": {"configured": False, "oauth_version": "2.0"},
            }
        }


# ============================================================================
# Admin Endpoints (Protected)
# ============================================================================


@router.get(
    "/admin/oauth-credentials",
    response_model=List[OAuthCredentialResponse],
    summary="List all OAuth platforms",
    description="Get configuration status for all supported OAuth platforms (Admin only)",
)
async def list_oauth_credentials(
    admin_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """
    List all OAuth platform credentials with masked sensitive data.

    Returns configuration status for Twitter, LinkedIn, and Threads.
    Only shows masked credentials for security.

    Requires: Admin privileges
    """
    try:
        manager = OAuthCredentialManager(db)
        platforms_status = manager.get_all_platforms_status()

        results = []

        for platform, status_info in platforms_status.items():
            # Get database record if exists
            db_cred = (
                db.query(OAuthPlatformCredential)
                .filter(OAuthPlatformCredential.platform == platform)
                .first()
            )

            # Get masked credentials
            masked_creds = (
                manager.get_masked_credentials(platform) if status_info["configured"] else {}
            )

            # Get updated_by user email
            updated_by_email = None
            if db_cred and db_cred.updated_by:
                updated_user = db.query(User).filter(User.id == db_cred.updated_by).first()
                updated_by_email = updated_user.email if updated_user else None

            results.append(
                {
                    "platform": platform,
                    "oauth_version": status_info["oauth_version"],
                    "is_configured": status_info["configured"],
                    "is_active": status_info["is_active"],
                    "last_tested_at": db_cred.last_tested_at if db_cred else None,
                    "test_status": status_info["test_status"],
                    "test_error_message": db_cred.test_error_message if db_cred else None,
                    "masked_credentials": masked_creds.get("masked_credentials", masked_creds)
                    if masked_creds
                    else {},
                    "updated_at": db_cred.updated_at if db_cred else None,
                    "updated_by_email": updated_by_email,
                    "source": status_info["source"],
                }
            )

        logger.info(f"Admin {admin_user.email} listed OAuth credentials")
        return results

    except Exception as e:
        logger.error(f"Error listing OAuth credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OAuth credentials",
        )


@router.get(
    "/admin/oauth-credentials/{platform}",
    response_model=OAuthCredentialResponse,
    summary="Get OAuth credentials for a platform",
    description="Get configuration details for a specific platform (Admin only)",
)
async def get_oauth_credential(
    platform: str, admin_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """
    Get OAuth credentials for a specific platform.

    Returns masked credentials and configuration status.

    Requires: Admin privileges
    """
    try:
        manager = OAuthCredentialManager(db)
        platforms_status = manager.get_all_platforms_status()

        if platform not in platforms_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Platform '{platform}' not supported. Supported platforms: twitter, linkedin, threads",
            )

        status_info = platforms_status[platform]

        # Get database record if exists
        db_cred = (
            db.query(OAuthPlatformCredential)
            .filter(OAuthPlatformCredential.platform == platform)
            .first()
        )

        # Get masked credentials
        masked_creds = manager.get_masked_credentials(platform) if status_info["configured"] else {}

        # Get updated_by user email
        updated_by_email = None
        if db_cred and db_cred.updated_by:
            updated_user = db.query(User).filter(User.id == db_cred.updated_by).first()
            updated_by_email = updated_user.email if updated_user else None

        result = {
            "platform": platform,
            "oauth_version": status_info["oauth_version"],
            "is_configured": status_info["configured"],
            "is_active": status_info["is_active"],
            "last_tested_at": db_cred.last_tested_at if db_cred else None,
            "test_status": status_info["test_status"],
            "test_error_message": db_cred.test_error_message if db_cred else None,
            "masked_credentials": masked_creds if masked_creds else {},
            "updated_at": db_cred.updated_at if db_cred else None,
            "updated_by_email": updated_by_email,
            "source": status_info["source"],
        }

        logger.info(f"Admin {admin_user.email} retrieved {platform} credentials")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving {platform} credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve credentials for {platform}",
        )


@router.post(
    "/admin/oauth-credentials/{platform}",
    summary="Create or update OAuth credentials",
    description="Save OAuth credentials for a platform (Admin only)",
)
async def create_or_update_oauth_credential(
    platform: str,
    credential_data: OAuthCredentialCreate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Create or update OAuth credentials for a platform.

    Encrypts credentials before storing in database.
    Database credentials take precedence over .env credentials.

    Requires: Admin privileges
    """
    try:
        manager = OAuthCredentialManager(db)

        # Validate platform
        if platform not in manager.SUPPORTED_PLATFORMS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform: {platform}. Supported: twitter, linkedin, threads",
            )

        # Save credentials
        saved_cred = manager.save_credentials(
            platform=platform,
            oauth_version=credential_data.oauth_version,
            updated_by_user_id=admin_user.id,
            api_key=credential_data.api_key,
            api_secret=credential_data.api_secret,
            client_id=credential_data.client_id,
            client_secret=credential_data.client_secret,
            callback_url=credential_data.callback_url,
            redirect_uri=credential_data.redirect_uri,
            scopes=credential_data.scopes,
            is_active=credential_data.is_active,
        )

        logger.info(f"Admin {admin_user.email} updated {platform} OAuth credentials")

        return {
            "success": True,
            "message": f"{saved_cred.get_platform_name()} OAuth credentials saved successfully",
            "platform": platform,
            "oauth_version": saved_cred.oauth_version,
        }

    except ValueError as e:
        logger.warning(f"Validation error updating {platform} credentials: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving {platform} credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save credentials for {platform}",
        )


@router.delete(
    "/admin/oauth-credentials/{platform}",
    summary="Delete OAuth credentials",
    description="Remove OAuth credentials for a platform (Admin only)",
)
async def delete_oauth_credential(
    platform: str, admin_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """
    Delete OAuth credentials for a platform.

    After deletion, the system will fall back to .env credentials if available.

    Requires: Admin privileges
    """
    try:
        manager = OAuthCredentialManager(db)

        # Validate platform
        if platform not in manager.SUPPORTED_PLATFORMS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported platform: {platform}"
            )

        # Delete credentials
        deleted = manager.delete_credentials(platform, admin_user.id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"No credentials found for {platform}"
            )

        logger.info(f"Admin {admin_user.email} deleted {platform} OAuth credentials")

        return {
            "success": True,
            "message": f"{platform.title()} OAuth credentials removed successfully",
            "platform": platform,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting {platform} credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete credentials for {platform}",
        )


@router.post(
    "/admin/oauth-credentials/{platform}/test",
    response_model=TestConnectionResponse,
    summary="Test OAuth connection",
    description="Test OAuth credentials by validating format and attempting a test connection (Admin only)",
)
async def test_oauth_connection(
    platform: str, admin_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """
    Test OAuth connection for a platform.

    Validates credential format and tests connectivity where possible.

    Requires: Admin privileges
    """
    try:
        manager = OAuthCredentialManager(db)

        # Validate platform
        if platform not in manager.SUPPORTED_PLATFORMS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported platform: {platform}"
            )

        # Test connection
        success, message = await manager.test_connection(platform)

        logger.info(f"Admin {admin_user.email} tested {platform} connection: {success}")

        return {
            "success": success,
            "message": message,
            "platform": platform,
            "tested_at": datetime.utcnow(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing {platform} connection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test connection for {platform}",
        )


# ============================================================================
# Public Endpoints (No Authentication Required)
# ============================================================================


@router.get(
    "/oauth-credentials/status",
    response_model=PublicStatusResponse,
    summary="Get public OAuth status",
    description="Get configuration status for all platforms (no authentication required)",
)
async def get_public_oauth_status(db: Session = Depends(get_db)):
    """
    Get public OAuth configuration status.

    Returns which platforms are configured without exposing credentials.
    This endpoint does NOT require authentication.

    Used by the frontend to show which social media connections are available.
    """
    try:
        manager = OAuthCredentialManager(db)
        platforms_status = manager.get_all_platforms_status()

        # Return only non-sensitive information
        result = {}
        for platform, status_info in platforms_status.items():
            result[platform] = {
                "configured": status_info["configured"],
                "oauth_version": status_info["oauth_version"],
            }

        return result

    except Exception as e:
        logger.error(f"Error getting public OAuth status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OAuth status",
        )
