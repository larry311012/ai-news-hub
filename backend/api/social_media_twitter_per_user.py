"""
Twitter OAuth 1.0a - Per-User Credentials Flow (Task 1.6 - iOS Support Added)

This module provides Twitter OAuth endpoints that support BOTH:
1. Per-user credentials (user provides their own API key/secret)
2. Centralized admin credentials (fallback)
3. iOS mobile app OAuth redirects (ainewshub://oauth-callback)

The flow automatically detects which credentials to use:
- If user has set up their own credentials -> use theirs
- If user hasn't set up credentials -> use admin's (if available)
- If neither exists -> show setup wizard

iOS Support:
- Auto-detects iOS app via X-App-Version header
- Uses custom URL scheme: ainewshub://oauth-callback?platform=twitter
- Returns OAuth tokens via deep link for iOS app
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Header
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging

from database import get_db, User
from database_social_media import SocialMediaConnection
from database_user_oauth_credentials import UserOAuthCredential
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.social_connection_manager import SocialConnectionManager
from utils.twitter_oauth1_per_user import (
    get_user_or_admin_credentials,
    get_request_token_with_user_creds,
    get_access_token_with_user_creds,
    get_user_info_with_user_creds,
    check_user_has_credentials
)
from utils.ios_oauth_handler import (
    iOSOAuthHandler,
    build_oauth_success_redirect,
    build_oauth_error_redirect
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Temporary storage for request token secrets
# In production, use Redis with TTL
request_token_storage = {}


@router.get("/twitter/connect")
async def twitter_connect_with_per_user_creds(
    request: Request,
    return_url: Optional[str] = Query(None, description="Frontend URL to redirect after OAuth"),
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    app_version: Optional[str] = Header(None, alias="X-App-Version")
):
    """
    Initiate Twitter OAuth 1.0a flow with per-user credential support.

    **iOS Support:** Automatically detects iOS app via X-App-Version header
    and uses custom URL scheme for OAuth callback.

    Flow:
    1. Check if user has their own credentials
    2. If yes: Use user's credentials
    3. If no: Try admin credentials
    4. If neither: Return error with setup instructions
    5. Detect iOS client and use appropriate redirect URL

    Returns:
        {
            "success": true,
            "authorization_url": "https://api.twitter.com/oauth/authorize?oauth_token=...",
            "platform": "twitter",
            "oauth_version": "1.0a",
            "credentials_source": "user" or "admin",
            "is_mobile": true/false  # NEW
        }
    """
    try:
        # Detect iOS client
        is_mobile = iOSOAuthHandler.detect_ios_client(user_agent, app_version)
        logger.info(f"Twitter OAuth connect request from {'iOS' if is_mobile else 'web'} client for user {user.id}")

        # Get credentials (user's first, then admin's)
        credentials = get_user_or_admin_credentials(db, user.id)

        if not credentials:
            # Check if credentials exist but couldn't be decrypted
            cred_record = db.query(UserOAuthCredential).filter(
                UserOAuthCredential.user_id == user.id,
                UserOAuthCredential.platform == "twitter",
                UserOAuthCredential.is_active == True
            ).first()

            if cred_record and cred_record.encrypted_api_key and cred_record.encrypted_api_secret:
                # Credentials exist in database but decryption failed
                logger.error(f"Failed to decrypt Twitter credentials for user {user.id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": "decryption_failed",
                        "message": "Could not decrypt your saved credentials. The encryption key may have changed.",
                        "action": "re_enter_credentials",
                        "instructions": [
                            "Your API keys are saved but cannot be decrypted.",
                            "This usually happens when the server's encryption key changed.",
                            "Solution: Go back to Step 5 and re-enter your Twitter API keys.",
                            "Your previous keys are no longer accessible."
                        ],
                        "setup_url": "/setup-twitter.html#step-5"
                    }
                )
            else:
                # No credentials available - user needs to set up
                raise HTTPException(
                    status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                    detail={
                        "error": "no_credentials",
                        "message": "No Twitter OAuth credentials configured. Please set up your credentials first.",
                        "setup_url": "/api/oauth-setup/twitter/credentials",
                        "instructions": [
                            "1. Create a Twitter Developer App at https://developer.twitter.com/",
                            "2. Get your API Key and API Secret",
                            "3. Set callback URL to: http://localhost:8000/api/social-media/twitter/callback",
                            "4. Save credentials via POST /api/oauth-setup/twitter/credentials"
                        ]
                    }
                )

        # Step 1: Get request token
        request_token_data = await get_request_token_with_user_creds(credentials)

        if not request_token_data:
            logger.error(f"Failed to obtain request token for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate Twitter OAuth. Please try again."
            )

        oauth_token = request_token_data["oauth_token"]
        oauth_token_secret = request_token_data["oauth_token_secret"]

        # Step 2: Store request token secret and context (including client type)
        request_token_storage[oauth_token] = {
            "oauth_token_secret": oauth_token_secret,
            "user_id": user.id,
            "return_url": return_url,
            "credentials_source": credentials["source"],
            "credentials": credentials,  # Store credentials for callback
            "is_mobile": is_mobile,  # NEW: Track if iOS client
            "user_agent": user_agent,
            "app_version": app_version,
            "created_at": datetime.utcnow()
        }

        # Clean up old tokens
        current_time = datetime.utcnow()
        expired_tokens = [
            token for token, data in request_token_storage.items()
            if (current_time - data['created_at']).total_seconds() > 600
        ]
        for token in expired_tokens:
            del request_token_storage[token]

        # Step 3: Generate authorization URL
        auth_url = f"https://api.twitter.com/oauth/authorize?oauth_token={oauth_token}"

        logger.info(f"Generated Twitter OAuth URL for user {user.id} (source: {credentials['source']}, client: {'iOS' if is_mobile else 'web'})")

        return {
            "success": True,
            "authorization_url": auth_url,
            "platform": "twitter",
            "oauth_version": "1.0a",
            "credentials_source": credentials["source"],
            "is_mobile": is_mobile  # NEW: Let frontend know if mobile
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating Twitter OAuth URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while initiating OAuth"
        )


@router.get("/twitter/callback")
async def twitter_callback_with_per_user_creds(
    oauth_token: str = Query(..., description="OAuth token from Twitter"),
    oauth_verifier: str = Query(..., description="OAuth verifier from Twitter"),
    denied: Optional[str] = Query(None, description="Present if user denied access"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Handle Twitter OAuth callback with per-user credentials.

    **iOS Support:** Detects iOS client from stored request data and
    redirects to custom URL scheme instead of web page.

    Flow:
    1. Retrieve stored request token secret and credentials
    2. Exchange for access token using stored credentials
    3. Get user info
    4. Store connection
    5. Redirect to frontend (web) or iOS app (mobile)
    """
    try:
        # Handle user denial
        if denied:
            logger.warning(f"User denied Twitter authorization: {denied}")
            stored_data = request_token_storage.get(oauth_token, {})
            return_url = stored_data.get("return_url")
            is_mobile = stored_data.get("is_mobile", False)
            user_agent = stored_data.get("user_agent")
            app_version = stored_data.get("app_version")

            if oauth_token in request_token_storage:
                del request_token_storage[oauth_token]

            # Build appropriate error redirect
            redirect_url = build_oauth_error_redirect(
                platform="twitter",
                error="user_denied",
                error_description="User denied Twitter authorization",
                user_agent=user_agent,
                app_version=app_version
            )

            return RedirectResponse(url=redirect_url)

        # Retrieve stored data
        if oauth_token not in request_token_storage:
            logger.warning(f"Request token not found: {oauth_token[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth token. Please try again."
            )

        stored_data = request_token_storage[oauth_token]
        oauth_token_secret = stored_data["oauth_token_secret"]
        user_id = stored_data["user_id"]
        return_url = stored_data.get("return_url")
        credentials = stored_data["credentials"]
        is_mobile = stored_data.get("is_mobile", False)
        user_agent = stored_data.get("user_agent")
        app_version = stored_data.get("app_version")

        # Clean up
        del request_token_storage[oauth_token]

        # Exchange for access token
        access_token_data = await get_access_token_with_user_creds(
            credentials=credentials,
            oauth_token=oauth_token,
            oauth_token_secret=oauth_token_secret,
            oauth_verifier=oauth_verifier
        )

        if not access_token_data:
            logger.error(f"Failed to exchange request token for access token (user {user_id})")

            # Build appropriate error redirect
            redirect_url = build_oauth_error_redirect(
                platform="twitter",
                error="oauth_failed",
                error_description="Failed to authenticate with Twitter",
                user_agent=user_agent,
                app_version=app_version
            )

            return RedirectResponse(url=redirect_url)

        access_token = access_token_data["oauth_token"]
        access_token_secret = access_token_data["oauth_token_secret"]
        twitter_user_id = access_token_data["user_id"]
        twitter_username = access_token_data["screen_name"]

        # Get detailed user info
        user_info = await get_user_info_with_user_creds(
            credentials=credentials,
            access_token=access_token,
            access_token_secret=access_token_secret
        )

        if not user_info:
            logger.warning(f"Failed to get Twitter user info for user {user_id}, using basic data")
            user_info = {
                "id": twitter_user_id,
                "username": twitter_username,
                "name": twitter_username
            }

        # Store connection
        manager = SocialConnectionManager(db)
        connection = manager.create_connection(
            user_id=user_id,
            platform="twitter",
            access_token=access_token,
            refresh_token=access_token_secret,  # Store token secret in refresh_token field
            expires_in=None,  # OAuth 1.0a tokens don't expire
            scope=None,
            platform_user_id=user_info.get("id"),
            platform_username=user_info.get("username"),
            metadata={
                **user_info,
                "credentials_source": credentials["source"],  # Track which credentials were used
                "client_type": "ios" if is_mobile else "web"  # NEW: Track client type
            }
        )

        logger.info(f"Twitter OAuth connection created for user {user_id} (@{user_info.get('username')}, source: {credentials['source']}, client: {'iOS' if is_mobile else 'web'})")

        # Build appropriate success redirect
        # For iOS, we don't include sensitive token in URL (already stored in DB)
        # iOS app will know connection succeeded and can fetch connection status via API
        redirect_url = build_oauth_success_redirect(
            platform="twitter",
            access_token="success",  # Don't expose actual token in URL
            user_agent=user_agent,
            app_version=app_version,
            username=user_info.get("username", ""),
            oauth_version="1.0a",
            source=credentials["source"]
        )

        return RedirectResponse(url=redirect_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Twitter OAuth callback: {str(e)}")

        # Try to build error redirect if we have stored data
        stored_data = request_token_storage.get(oauth_token, {}) if 'oauth_token' in locals() else {}
        user_agent = stored_data.get("user_agent")
        app_version = stored_data.get("app_version")

        redirect_url = build_oauth_error_redirect(
            platform="twitter",
            error="server_error",
            error_description="An error occurred during OAuth authentication",
            user_agent=user_agent,
            app_version=app_version
        )

        return RedirectResponse(url=redirect_url)


@router.get("/twitter/status")
async def twitter_status_with_per_user_creds(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get Twitter OAuth configuration status for current user.

    Returns:
        {
            "configured": true/false,
            "credentials_source": "user" | "admin" | null,
            "has_user_credentials": true/false,
            "has_admin_credentials": true/false,
            "oauth_version": "1.0a",
            "setup_url": "/api/oauth-setup/twitter/credentials",
            "ios_supported": true  # NEW
        }
    """
    try:
        has_creds, source = check_user_has_credentials(db, user.id)

        # Check specifically for user credentials
        from utils.user_oauth_credential_manager import UserOAuthCredentialManager
        user_manager = UserOAuthCredentialManager(db, user.id)
        user_status = user_manager.get_credential_status("twitter")

        # Check admin credentials
        from utils.oauth_credential_manager import OAuthCredentialManager
        admin_manager = OAuthCredentialManager(db)
        admin_platforms = admin_manager.get_all_platforms_status()
        has_admin = admin_platforms.get("twitter", {}).get("configured", False)

        return {
            "configured": has_creds,
            "credentials_source": source,
            "has_user_credentials": user_status.get("configured", False) if user_status else False,
            "has_admin_credentials": has_admin,
            "user_credentials_validated": user_status.get("is_validated", False) if user_status else False,
            "oauth_version": "1.0a",
            "setup_url": "/api/oauth-setup/twitter/credentials",
            "recommendation": "user" if not user_status or not user_status.get("configured") else None,
            "ios_supported": True,  # NEW: Indicate iOS support
            "ios_redirect_scheme": "ainewshub://oauth-callback"  # NEW: iOS custom URL scheme
        }

    except Exception as e:
        logger.error(f"Error getting Twitter status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get Twitter configuration status"
        )
