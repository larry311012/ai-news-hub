"""
OAuth utilities for Google and GitHub OAuth integration
"""
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import os
import logging
from datetime import datetime

from database import User
from utils.auth import create_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth configuration
oauth = OAuth()

# ============================================================================
# Google OAuth Configuration
# ============================================================================
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:8001/api/auth/oauth/google/callback"
)

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    logger.info("Google OAuth configured successfully")
else:
    logger.warning("Google OAuth not configured - missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET")


# ============================================================================
# GitHub OAuth Configuration
# ============================================================================
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv(
    "GITHUB_REDIRECT_URI", "http://localhost:8001/api/auth/oauth/github/callback"
)

if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:
    oauth.register(
        name="github",
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
        authorize_url="https://github.com/login/oauth/authorize",
        access_token_url="https://github.com/login/oauth/access_token",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "read:user user:email"},
    )
    logger.info("GitHub OAuth configured successfully")
else:
    logger.warning("GitHub OAuth not configured - missing GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET")


# ============================================================================
# Google OAuth Functions
# ============================================================================


def get_google_auth_url(state: str) -> str:
    """
    Generate Google OAuth authorization URL.

    Args:
        state: Random state parameter for CSRF protection

    Returns:
        Authorization URL string
    """
    if not GOOGLE_CLIENT_ID:
        raise ValueError("Google OAuth not configured")

    # Construct authorization URL
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"state={state}"
    )

    logger.info("Generated Google OAuth authorization URL")
    return auth_url


async def get_google_user_info(code: str) -> Optional[Dict[str, Any]]:
    """
    Exchange authorization code for user information.

    Args:
        code: Authorization code from OAuth callback

    Returns:
        Dictionary with user info (sub, email, name, picture) or None on error
    """
    try:
        import httpx

        # Exchange code for token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            tokens = token_response.json()

            # Get user info
            userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}

            userinfo_response = await client.get(userinfo_url, headers=headers)
            userinfo_response.raise_for_status()
            user_info = userinfo_response.json()

            logger.info(f"Retrieved Google user info for: {user_info.get('email')}")
            return user_info

    except Exception as e:
        logger.error(f"Error getting Google user info: {str(e)}")
        return None


# ============================================================================
# GitHub OAuth Functions
# ============================================================================


def get_github_auth_url(state: str) -> str:
    """
    Generate GitHub OAuth authorization URL.

    Args:
        state: Random state parameter for CSRF protection

    Returns:
        Authorization URL string
    """
    if not GITHUB_CLIENT_ID:
        raise ValueError("GitHub OAuth not configured")

    # Construct authorization URL
    auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={GITHUB_CLIENT_ID}&"
        f"redirect_uri={GITHUB_REDIRECT_URI}&"
        f"scope=read:user%20user:email&"
        f"state={state}"
    )

    logger.info("Generated GitHub OAuth authorization URL")
    return auth_url


async def get_github_user_info(code: str) -> Optional[Dict[str, Any]]:
    """
    Exchange authorization code for user information from GitHub.

    Args:
        code: Authorization code from OAuth callback

    Returns:
        Dictionary with user info (id, email, name, avatar_url) or None on error
    """
    try:
        import httpx

        # Exchange code for token
        token_url = "https://github.com/login/oauth/access_token"
        token_data = {
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": GITHUB_REDIRECT_URI,
        }

        async with httpx.AsyncClient() as client:
            # GitHub returns URL-encoded response, request JSON
            headers = {"Accept": "application/json"}
            token_response = await client.post(token_url, data=token_data, headers=headers)
            token_response.raise_for_status()
            tokens = token_response.json()

            access_token = tokens.get("access_token")
            if not access_token:
                logger.error("No access token received from GitHub")
                return None

            # Get user info
            userinfo_url = "https://api.github.com/user"
            auth_headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            }

            userinfo_response = await client.get(userinfo_url, headers=auth_headers)
            userinfo_response.raise_for_status()
            user_info = userinfo_response.json()

            # Get primary email if not public
            email = user_info.get("email")
            if not email:
                emails_url = "https://api.github.com/user/emails"
                emails_response = await client.get(emails_url, headers=auth_headers)
                emails_response.raise_for_status()
                emails = emails_response.json()

                # Find primary verified email
                for email_obj in emails:
                    if email_obj.get("primary") and email_obj.get("verified"):
                        email = email_obj.get("email")
                        break

                # Fallback to first verified email
                if not email:
                    for email_obj in emails:
                        if email_obj.get("verified"):
                            email = email_obj.get("email")
                            break

                # Add email to user_info
                user_info["email"] = email

            logger.info(f"Retrieved GitHub user info for: {user_info.get('email')}")
            return user_info

    except Exception as e:
        logger.error(f"Error getting GitHub user info: {str(e)}")
        return None


# ============================================================================
# Common OAuth Functions
# ============================================================================


def create_or_update_oauth_user(
    db: Session, provider: str, oauth_id: str, email: str, name: str, picture: Optional[str] = None
) -> User:
    """
    Create or update user from OAuth information.

    If user with oauth_id exists, update their info.
    If user with email exists, link OAuth account.
    Otherwise, create new user.

    Args:
        db: Database session
        provider: OAuth provider name (e.g., 'google', 'github')
        oauth_id: Provider's user ID
        email: User's email address
        name: User's full name
        picture: Optional profile picture URL

    Returns:
        User object (newly created or updated)
    """
    # Check if user exists with this OAuth ID
    user = db.query(User).filter(User.oauth_provider == provider, User.oauth_id == oauth_id).first()

    if user:
        # Update existing OAuth user
        user.email = email.lower()
        user.full_name = name
        user.oauth_profile_picture = picture
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        logger.info(f"Updated existing OAuth user: user_id={user.id}, provider={provider}")
        return user

    # Check if user exists with this email
    user = db.query(User).filter(User.email == email.lower()).first()

    if user:
        # Link OAuth account to existing user
        user.oauth_provider = provider
        user.oauth_id = oauth_id
        user.oauth_profile_picture = picture
        user.is_verified = True  # Auto-verify via OAuth
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        logger.info(
            f"Linked OAuth account to existing user: user_id={user.id}, provider={provider}"
        )
        return user

    # Create new user
    user = User(
        email=email.lower(),
        password_hash=None,  # No password for OAuth users
        full_name=name,
        oauth_provider=provider,
        oauth_id=oauth_id,
        oauth_profile_picture=picture,
        is_active=True,
        is_verified=True,  # Auto-verify via OAuth
        is_guest=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"Created new OAuth user: user_id={user.id}, provider={provider}, email={email}")
    return user


def unlink_oauth_account(user: User, db: Session) -> bool:
    """
    Unlink OAuth account from user.
    User must have a password set before unlinking.

    Args:
        user: User object
        db: Database session

    Returns:
        True if successfully unlinked, False if user needs password first
    """
    if not user.password_hash:
        logger.warning(f"Cannot unlink OAuth for user_id={user.id} - no password set")
        return False

    user.oauth_provider = None
    user.oauth_id = None
    user.oauth_profile_picture = None
    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    logger.info(f"Unlinked OAuth account for user_id={user.id}")
    return True
