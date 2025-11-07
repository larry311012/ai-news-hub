"""
Twitter OAuth 1.0a - Consolidated Implementation

This module provides a consolidated Twitter OAuth 1.0a implementation that
extends the OAuth1Base class, eliminating code duplication.

Key Features:
- Extends OAuth1Base for signature generation and OAuth flow
- Supports both admin and per-user credentials
- Database-backed credential management
- Backward compatible with existing code
- Single source of truth for Twitter OAuth

Usage:
    from utils.twitter_oauth_consolidated import TwitterOAuth1

    # Initialize
    twitter = TwitterOAuth1()

    # Check if configured
    if twitter.is_configured():
        # Get request token
        token_data = await twitter.get_request_token_with_config()

        # Get authorization URL
        auth_url = twitter.get_authorization_url_with_config(token_data['oauth_token'])

        # Exchange for access token
        access_data = await twitter.get_access_token_with_config(
            oauth_token, oauth_token_secret, oauth_verifier
        )
"""

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from utils.oauth_base import OAuth1Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TwitterOAuth1(OAuth1Base):
    """
    Twitter OAuth 1.0a implementation extending OAuth1Base.

    This class provides Twitter-specific configuration and credential management
    while reusing all OAuth 1.0a logic from the base class.
    """

    def __init__(self, db: Optional[Session] = None, user_id: Optional[int] = None):
        """
        Initialize Twitter OAuth 1.0a.

        Args:
            db: Database session (optional, for credential lookup)
            user_id: User ID (optional, for per-user credentials)
        """
        super().__init__(platform_name="twitter")
        self.db = db
        self.user_id = user_id
        self._config_cache = None

    def get_platform_config(self) -> Dict[str, Any]:
        """
        Get Twitter OAuth 1.0a configuration.

        Returns:
            Dictionary with Twitter OAuth endpoints and settings
        """
        return {
            "request_token_url": "https://api.twitter.com/oauth/request_token",
            "authorization_url": "https://api.twitter.com/oauth/authorize",
            "access_token_url": "https://api.twitter.com/oauth/access_token",
            "verify_credentials_url": "https://api.twitter.com/1.1/account/verify_credentials.json",
            "api_base_url": "https://api.twitter.com/1.1"
        }

    def _is_placeholder_credential(self, value: Optional[str]) -> bool:
        """
        Check if a credential value is a placeholder (not real).

        Args:
            value: Credential value to check

        Returns:
            True if value is a placeholder, False if it's likely real
        """
        if not value:
            return True

        placeholders = [
            "your-", "your_", "placeholder", "example", "test-", "demo-",
            "xxx", "yyy", "zzz", "replace-me", "change-me", "add-your", "insert-"
        ]

        value_lower = value.lower()
        return any(placeholder in value_lower for placeholder in placeholders)

    def get_credentials(self) -> Dict[str, Any]:
        """
        Get Twitter OAuth credentials with fallback logic.

        Priority:
        1. User's own credentials (if user_id and db provided)
        2. Admin centralized credentials (from database)
        3. Environment variables (as fallback)

        Returns:
            Dictionary with:
            - api_key: OAuth consumer key
            - api_secret: OAuth consumer secret
            - callback_url: OAuth callback URL
            - source: "user", "admin", or "environment"
            - is_valid: Whether credentials are valid (not placeholders)
            - error: Error message if invalid
        """
        # Return cached config if available
        if self._config_cache:
            return self._config_cache

        # Try user credentials first (if user_id provided)
        if self.db and self.user_id:
            try:
                from utils.user_oauth_credential_manager import UserOAuthCredentialManager
                user_manager = UserOAuthCredentialManager(self.db, self.user_id)
                user_creds = user_manager.get_credentials("twitter")

                if user_creds and user_creds.get("api_key") and user_creds.get("api_secret"):
                    api_key = user_creds["api_key"]
                    api_secret = user_creds["api_secret"]

                    if not self._is_placeholder_credential(api_key) and not self._is_placeholder_credential(api_secret):
                        logger.info(f"Using user {self.user_id}'s own Twitter credentials")
                        self._config_cache = {
                            "api_key": api_key,
                            "api_secret": api_secret,
                            "callback_url": user_creds.get("callback_url", self._get_default_callback_url()),
                            "source": "user",
                            "is_valid": True
                        }
                        return self._config_cache
            except Exception as e:
                logger.debug(f"Could not get user credentials: {e}")

        # Try admin credentials from database
        if self.db:
            try:
                from utils.oauth_credential_manager import OAuthCredentialManager
                admin_manager = OAuthCredentialManager(self.db)
                admin_creds = admin_manager.get_credentials("twitter")

                if admin_creds and admin_creds.get("api_key") and admin_creds.get("api_secret"):
                    api_key = admin_creds["api_key"]
                    api_secret = admin_creds["api_secret"]

                    if not self._is_placeholder_credential(api_key) and not self._is_placeholder_credential(api_secret):
                        logger.info("Using admin Twitter credentials from database")
                        self._config_cache = {
                            "api_key": api_key,
                            "api_secret": api_secret,
                            "callback_url": admin_creds.get("callback_url", self._get_default_callback_url()),
                            "source": "admin",
                            "is_valid": True
                        }
                        return self._config_cache
            except Exception as e:
                logger.debug(f"Could not get admin credentials from database: {e}")

        # Fall back to environment variables
        api_key = os.getenv("TWITTER_API_KEY")
        api_secret = os.getenv("TWITTER_API_SECRET")
        callback_url = os.getenv("TWITTER_CALLBACK_URL", self._get_default_callback_url())

        # Validate environment credentials
        if self._is_placeholder_credential(api_key) or self._is_placeholder_credential(api_secret):
            logger.warning(
                "Twitter OAuth credentials appear to be placeholders. "
                "Please configure real credentials in database or environment."
            )
            return {
                "api_key": api_key,
                "api_secret": api_secret,
                "callback_url": callback_url,
                "source": "environment",
                "is_valid": False,
                "error": "Credentials are placeholder values - please configure real Twitter API credentials"
            }

        logger.info("Using Twitter credentials from environment variables")
        self._config_cache = {
            "api_key": api_key,
            "api_secret": api_secret,
            "callback_url": callback_url,
            "source": "environment",
            "is_valid": True
        }
        return self._config_cache

    def _get_default_callback_url(self) -> str:
        """Get default callback URL."""
        return os.getenv("TWITTER_CALLBACK_URL", "http://localhost:8000/api/social-media/twitter/callback")

    def is_configured(self) -> bool:
        """
        Check if Twitter OAuth 1.0a is configured with valid credentials.

        Returns:
            True if valid credentials are available, False otherwise
        """
        creds = self.get_credentials()
        return creds.get("is_valid", False)

    # ========================================================================
    # Convenience Methods (backward compatibility)
    # ========================================================================

    async def get_request_token_with_config(self) -> Optional[Dict[str, str]]:
        """
        Get request token using configured credentials.

        Convenience method that automatically uses configured credentials.

        Returns:
            Dictionary with oauth_token and oauth_token_secret, or None
        """
        creds = self.get_credentials()

        if not creds.get("is_valid"):
            raise ValueError(creds.get("error", "Twitter OAuth not configured"))

        config = self.get_platform_config()

        return await self.get_request_token(
            request_token_url=config["request_token_url"],
            consumer_key=creds["api_key"],
            consumer_secret=creds["api_secret"],
            callback_url=creds["callback_url"]
        )

    def get_authorization_url_with_config(self, oauth_token: str) -> str:
        """
        Get authorization URL using configured endpoints.

        Args:
            oauth_token: Request token from get_request_token_with_config()

        Returns:
            Authorization URL string
        """
        config = self.get_platform_config()
        return self.get_authorization_url(
            authorization_url=config["authorization_url"],
            oauth_token=oauth_token
        )

    async def get_access_token_with_config(
        self,
        oauth_token: str,
        oauth_token_secret: str,
        oauth_verifier: str
    ) -> Optional[Dict[str, str]]:
        """
        Get access token using configured credentials.

        Args:
            oauth_token: Request token from callback
            oauth_token_secret: Request token secret from get_request_token_with_config()
            oauth_verifier: OAuth verifier from callback

        Returns:
            Dictionary with oauth_token, oauth_token_secret, user_id, screen_name
        """
        creds = self.get_credentials()

        if not creds.get("is_valid"):
            raise ValueError(creds.get("error", "Twitter OAuth not configured"))

        config = self.get_platform_config()

        return await self.get_access_token(
            access_token_url=config["access_token_url"],
            consumer_key=creds["api_key"],
            consumer_secret=creds["api_secret"],
            oauth_token=oauth_token,
            oauth_token_secret=oauth_token_secret,
            oauth_verifier=oauth_verifier
        )

    async def get_user_info_with_config(
        self,
        access_token: str,
        access_token_secret: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get Twitter user info using configured credentials.

        Args:
            access_token: OAuth access token
            access_token_secret: OAuth access token secret

        Returns:
            Dictionary with user information
        """
        creds = self.get_credentials()

        if not creds.get("is_valid"):
            raise ValueError(creds.get("error", "Twitter OAuth not configured"))

        config = self.get_platform_config()

        # Use make_authenticated_request to get user info
        response = await self.make_authenticated_request(
            method="GET",
            url=config["verify_credentials_url"],
            consumer_key=creds["api_key"],
            consumer_secret=creds["api_secret"],
            access_token=access_token,
            access_token_secret=access_token_secret,
            params={"skip_status": "true", "include_email": "false"}
        )

        if response:
            # Normalize to match expected format
            return {
                "id": response.get("id_str"),
                "username": response.get("screen_name"),
                "name": response.get("name"),
                "profile_image_url": response.get("profile_image_url_https"),
                "followers_count": response.get("followers_count"),
                "following_count": response.get("friends_count"),
                "tweet_count": response.get("statuses_count"),
                "verified": response.get("verified"),
                "description": response.get("description"),
                "location": response.get("location"),
                "created_at": response.get("created_at"),
                "raw_data": response
            }

        return None

    async def validate_credentials_with_config(
        self,
        access_token: str,
        access_token_secret: str
    ) -> bool:
        """
        Validate Twitter OAuth credentials by making a test API call.

        Args:
            access_token: OAuth access token
            access_token_secret: OAuth access token secret

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            user_info = await self.get_user_info_with_config(access_token, access_token_secret)
            return user_info is not None
        except Exception as e:
            logger.error(f"Error validating credentials: {str(e)}")
            return False

    def get_config_status(self) -> Dict[str, Any]:
        """
        Get OAuth configuration status with detailed information.

        Returns:
            Dictionary with configuration details and validation status
        """
        creds = self.get_credentials()

        return {
            "configured": creds.get("is_valid", False),
            "api_key_set": bool(creds.get("api_key")),
            "api_secret_set": bool(creds.get("api_secret")),
            "callback_url": creds.get("callback_url"),
            "oauth_version": "1.0a",
            "source": creds.get("source", "unknown"),
            "is_valid": creds.get("is_valid", False),
            "error": creds.get("error") if not creds.get("is_valid") else None,
            "help": None if creds.get("is_valid") else (
                "To configure Twitter OAuth:\n"
                "1. Visit https://developer.twitter.com/en/portal/dashboard\n"
                "2. Create an app and enable OAuth 1.0a\n"
                "3. Copy API Key and API Secret\n"
                "4. Add to database: POST /api/admin/oauth-credentials/twitter\n"
                "   OR update .env file with TWITTER_API_KEY and TWITTER_API_SECRET\n"
                "5. Restart the server"
            )
        }


# ============================================================================
# Backward Compatibility Functions
# ============================================================================
# These functions provide backward compatibility with existing code

def get_twitter_oauth_instance(db: Optional[Session] = None, user_id: Optional[int] = None) -> TwitterOAuth1:
    """
    Get a TwitterOAuth1 instance.

    Args:
        db: Database session (optional)
        user_id: User ID (optional, for per-user credentials)

    Returns:
        TwitterOAuth1 instance
    """
    return TwitterOAuth1(db=db, user_id=user_id)


def is_oauth1_configured_compat(db: Optional[Session] = None, user_id: Optional[int] = None) -> bool:
    """
    Check if Twitter OAuth 1.0a is configured (backward compatibility).

    Args:
        db: Database session (optional)
        user_id: User ID (optional)

    Returns:
        True if configured, False otherwise
    """
    twitter = TwitterOAuth1(db=db, user_id=user_id)
    return twitter.is_configured()


def get_oauth_config_status_compat(db: Optional[Session] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get OAuth configuration status (backward compatibility).

    Args:
        db: Database session (optional)
        user_id: User ID (optional)

    Returns:
        Configuration status dictionary
    """
    twitter = TwitterOAuth1(db=db, user_id=user_id)
    return twitter.get_config_status()
