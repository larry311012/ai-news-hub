"""
OAuth Credential Manager

This module provides secure CRUD operations for OAuth platform credentials,
including encryption/decryption, credential retrieval with fallback to .env,
and connection testing.

Usage:
    from utils.oauth_credential_manager import OAuthCredentialManager

    # Initialize with database session
    manager = OAuthCredentialManager(db)

    # Get credentials (database first, then .env fallback)
    twitter_creds = manager.get_credentials('twitter')

    # Save new credentials
    manager.save_credentials(
        platform='twitter',
        oauth_version='1.0a',
        api_key='abc123...',
        api_secret='xyz789...',
        callback_url='http://localhost:8000/api/social-media/twitter-oauth1/callback',
        updated_by_user_id=1
    )

    # Test connection
    success, message = await manager.test_connection('twitter')
"""

import os
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from database_oauth_credentials import OAuthPlatformCredential
from utils.encryption import encrypt_value, decrypt_value

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OAuthCredentialManager:
    """
    Manager class for OAuth platform credentials.

    Handles CRUD operations, encryption/decryption, and fallback logic
    to .env files for backward compatibility.
    """

    # Supported platforms and their OAuth versions
    SUPPORTED_PLATFORMS = {
        "twitter": {"oauth_version": "1.0a", "name": "Twitter (X)"},
        "linkedin": {"oauth_version": "2.0", "name": "LinkedIn"},
        "threads": {"oauth_version": "2.0", "name": "Threads"},
    }

    def __init__(self, db: Session):
        """
        Initialize credential manager.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_credentials(self, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get OAuth credentials for a platform.

        Priority:
        1. Database credentials (if configured and active)
        2. Environment variables (.env file)

        Args:
            platform: Platform name (twitter, linkedin, threads)

        Returns:
            Dictionary with decrypted credentials:
            {
                "platform": "twitter",
                "oauth_version": "1.0a",
                "api_key": "abc123...",
                "api_secret": "xyz789...",
                "callback_url": "http://...",
                "source": "database" or "env"
            }

            None if credentials not found
        """
        platform = platform.lower()

        # Try database first
        db_creds = self._get_from_database(platform)
        if db_creds:
            logger.info(f"Using database credentials for {platform}")
            return db_creds

        # Fallback to environment variables
        env_creds = self._get_from_env(platform)
        if env_creds:
            logger.info(f"Using environment credentials for {platform}")
            return env_creds

        logger.warning(f"No credentials found for platform: {platform}")
        return None

    def _get_from_database(self, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get credentials from database.

        Args:
            platform: Platform name

        Returns:
            Decrypted credentials or None
        """
        try:
            cred = (
                self.db.query(OAuthPlatformCredential)
                .filter(
                    OAuthPlatformCredential.platform == platform,
                    OAuthPlatformCredential.is_active == True,
                )
                .first()
            )

            if not cred or not cred.is_configured():
                return None

            # Decrypt credentials based on OAuth version
            result = {
                "platform": cred.platform,
                "oauth_version": cred.oauth_version,
                "source": "database",
            }

            if cred.oauth_version == "1.0a":
                # OAuth 1.0a (Twitter)
                result["api_key"] = (
                    decrypt_value(cred.encrypted_api_key) if cred.encrypted_api_key else None
                )
                result["api_secret"] = (
                    decrypt_value(cred.encrypted_api_secret) if cred.encrypted_api_secret else None
                )
                result["callback_url"] = cred.callback_url

            elif cred.oauth_version == "2.0":
                # OAuth 2.0 (LinkedIn, Threads)
                result["client_id"] = (
                    decrypt_value(cred.encrypted_client_id) if cred.encrypted_client_id else None
                )
                result["client_secret"] = (
                    decrypt_value(cred.encrypted_client_secret)
                    if cred.encrypted_client_secret
                    else None
                )
                result["redirect_uri"] = cred.redirect_uri
                result["scopes"] = cred.scopes.split(",") if cred.scopes else []

            # Validate that decryption worked
            if cred.oauth_version == "1.0a":
                if not result.get("api_key") or not result.get("api_secret"):
                    logger.error(f"Failed to decrypt credentials for {platform}")
                    return None
            elif cred.oauth_version == "2.0":
                if not result.get("client_id") or not result.get("client_secret"):
                    logger.error(f"Failed to decrypt credentials for {platform}")
                    return None

            return result

        except Exception as e:
            logger.error(f"Error retrieving credentials from database for {platform}: {str(e)}")
            return None

    def _get_from_env(self, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get credentials from environment variables (.env file).

        Args:
            platform: Platform name

        Returns:
            Credentials from environment or None
        """
        try:
            if platform == "twitter":
                api_key = os.getenv("TWITTER_API_KEY")
                api_secret = os.getenv("TWITTER_API_SECRET")
                callback_url = os.getenv(
                    "TWITTER_CALLBACK_URL",
                    "http://localhost:8000/api/social-media/twitter-oauth1/callback",
                )

                if api_key and api_secret:
                    return {
                        "platform": "twitter",
                        "oauth_version": "1.0a",
                        "api_key": api_key,
                        "api_secret": api_secret,
                        "callback_url": callback_url,
                        "source": "env",
                    }

            elif platform == "linkedin":
                client_id = os.getenv("LINKEDIN_CLIENT_ID")
                client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
                redirect_uri = os.getenv(
                    "LINKEDIN_REDIRECT_URI",
                    "http://localhost:8000/api/social-media/linkedin/callback",
                )

                if client_id and client_secret:
                    return {
                        "platform": "linkedin",
                        "oauth_version": "2.0",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": redirect_uri,
                        "scopes": ["openid", "profile", "email", "w_member_social"],
                        "source": "env",
                    }

            elif platform == "threads":
                client_id = os.getenv("THREADS_APP_ID")
                client_secret = os.getenv("THREADS_APP_SECRET")
                redirect_uri = os.getenv(
                    "THREADS_REDIRECT_URI",
                    "http://localhost:8000/api/social-media/threads/callback",
                )

                if client_id and client_secret:
                    return {
                        "platform": "threads",
                        "oauth_version": "2.0",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": redirect_uri,
                        "scopes": ["threads_basic", "threads_content_publish"],
                        "source": "env",
                    }

            return None

        except Exception as e:
            logger.error(f"Error reading environment credentials for {platform}: {str(e)}")
            return None

    def save_credentials(
        self,
        platform: str,
        oauth_version: str,
        updated_by_user_id: int,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        callback_url: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        scopes: Optional[list] = None,
        is_active: bool = True,
    ) -> OAuthPlatformCredential:
        """
        Save or update OAuth credentials for a platform.

        Args:
            platform: Platform name (twitter, linkedin, threads)
            oauth_version: OAuth version (1.0a or 2.0)
            updated_by_user_id: User ID of admin performing update
            api_key: OAuth 1.0a API key (optional)
            api_secret: OAuth 1.0a API secret (optional)
            client_id: OAuth 2.0 client ID (optional)
            client_secret: OAuth 2.0 client secret (optional)
            callback_url: OAuth 1.0a callback URL (optional)
            redirect_uri: OAuth 2.0 redirect URI (optional)
            scopes: OAuth 2.0 scopes list (optional)
            is_active: Whether credentials are active (default: True)

        Returns:
            OAuthPlatformCredential object

        Raises:
            ValueError: If required credentials are missing
        """
        platform = platform.lower()

        # Validate platform
        if platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}")

        # Validate credentials based on OAuth version
        if oauth_version == "1.0a":
            if not api_key or not api_secret:
                raise ValueError("OAuth 1.0a requires api_key and api_secret")
        elif oauth_version == "2.0":
            if not client_id or not client_secret:
                raise ValueError("OAuth 2.0 requires client_id and client_secret")
        else:
            raise ValueError(f"Invalid oauth_version: {oauth_version}")

        try:
            # Check if credentials already exist
            cred = (
                self.db.query(OAuthPlatformCredential)
                .filter(OAuthPlatformCredential.platform == platform)
                .first()
            )

            if cred:
                # Update existing credentials
                cred.oauth_version = oauth_version
                cred.updated_by = updated_by_user_id
                cred.updated_at = datetime.utcnow()
                cred.is_active = is_active

                # FIX: Set created_by if it's NULL (for old records migrated before this field existed)
                if cred.created_by is None:
                    cred.created_by = updated_by_user_id

                # Clear test status on update
                cred.test_status = "not_tested"
                cred.last_tested_at = None
                cred.test_error_message = None

                logger.info(f"Updating existing credentials for {platform}")
            else:
                # Create new credentials
                cred = OAuthPlatformCredential(
                    platform=platform,
                    oauth_version=oauth_version,
                    created_by=updated_by_user_id,
                    updated_by=updated_by_user_id,
                    is_active=is_active,
                    test_status="not_tested",
                )
                self.db.add(cred)
                logger.info(f"Creating new credentials for {platform}")

            # Encrypt and store credentials
            if oauth_version == "1.0a":
                cred.encrypted_api_key = encrypt_value(api_key) if api_key else None
                cred.encrypted_api_secret = encrypt_value(api_secret) if api_secret else None
                cred.callback_url = callback_url

                # Clear OAuth 2.0 fields
                cred.encrypted_client_id = None
                cred.encrypted_client_secret = None
                cred.redirect_uri = None
                cred.scopes = None

            elif oauth_version == "2.0":
                cred.encrypted_client_id = encrypt_value(client_id) if client_id else None
                cred.encrypted_client_secret = (
                    encrypt_value(client_secret) if client_secret else None
                )
                cred.redirect_uri = redirect_uri
                cred.scopes = ",".join(scopes) if scopes else None

                # Clear OAuth 1.0a fields
                cred.encrypted_api_key = None
                cred.encrypted_api_secret = None
                cred.callback_url = None

            self.db.commit()
            self.db.refresh(cred)

            logger.info(f"Successfully saved credentials for {platform}")
            return cred

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving credentials for {platform}: {str(e)}")
            raise

    def delete_credentials(self, platform: str, deleted_by_user_id: int) -> bool:
        """
        Delete OAuth credentials for a platform.

        Args:
            platform: Platform name
            deleted_by_user_id: User ID of admin performing deletion

        Returns:
            True if deleted, False if not found
        """
        try:
            cred = (
                self.db.query(OAuthPlatformCredential)
                .filter(OAuthPlatformCredential.platform == platform)
                .first()
            )

            if not cred:
                logger.warning(f"Credentials not found for platform: {platform}")
                return False

            self.db.delete(cred)
            self.db.commit()

            logger.info(f"Deleted credentials for {platform} by user {deleted_by_user_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting credentials for {platform}: {str(e)}")
            raise

    def get_all_platforms_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get configuration status for all supported platforms.

        Returns:
            Dictionary mapping platform names to their status:
            {
                "twitter": {
                    "configured": true,
                    "oauth_version": "1.0a",
                    "source": "database",
                    "is_active": true,
                    "last_tested_at": "2025-10-17T21:00:00Z",
                    "test_status": "success"
                },
                ...
            }
        """
        result = {}

        for platform, info in self.SUPPORTED_PLATFORMS.items():
            creds = self.get_credentials(platform)

            if creds:
                # Get additional info from database if available
                db_cred = (
                    self.db.query(OAuthPlatformCredential)
                    .filter(OAuthPlatformCredential.platform == platform)
                    .first()
                )

                result[platform] = {
                    "configured": True,
                    "oauth_version": creds["oauth_version"],
                    "source": creds["source"],
                    "is_active": db_cred.is_active if db_cred else True,
                    "last_tested_at": db_cred.last_tested_at.isoformat()
                    if db_cred and db_cred.last_tested_at
                    else None,
                    "test_status": db_cred.test_status if db_cred else None,
                }
            else:
                result[platform] = {
                    "configured": False,
                    "oauth_version": info["oauth_version"],
                    "source": None,
                    "is_active": False,
                    "last_tested_at": None,
                    "test_status": None,
                }

        return result

    def mask_credential(self, value: str, show_chars: int = 6) -> str:
        """
        Mask a credential for display (e.g., "abc123••••••••").

        Args:
            value: Credential value to mask
            show_chars: Number of characters to show at start

        Returns:
            Masked credential string
        """
        if not value:
            return ""

        if len(value) <= show_chars:
            return value[:2] + "••••"

        return value[:show_chars] + "••••••••"

    def get_masked_credentials(self, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get masked credentials for display in admin UI.

        Args:
            platform: Platform name

        Returns:
            Dictionary with masked credentials or None
        """
        creds = self.get_credentials(platform)
        if not creds:
            return None

        result = {
            "platform": creds["platform"],
            "oauth_version": creds["oauth_version"],
            "source": creds["source"],
        }

        if creds["oauth_version"] == "1.0a":
            result["api_key"] = self.mask_credential(creds.get("api_key", ""))
            result["api_secret"] = "••••••••••••"
            result["callback_url"] = creds.get("callback_url")
        elif creds["oauth_version"] == "2.0":
            result["client_id"] = self.mask_credential(creds.get("client_id", ""))
            result["client_secret"] = "••••••••••••"
            result["redirect_uri"] = creds.get("redirect_uri")
            result["scopes"] = creds.get("scopes", [])

        return result

    async def test_connection(self, platform: str) -> Tuple[bool, str]:
        """
        Test OAuth connection for a platform.

        Args:
            platform: Platform name

        Returns:
            Tuple of (success: bool, message: str)
        """
        creds = self.get_credentials(platform)
        if not creds:
            return False, f"No credentials configured for {platform}"

        try:
            if platform == "twitter":
                return await self._test_twitter_connection(creds)
            elif platform == "linkedin":
                return await self._test_linkedin_connection(creds)
            elif platform == "threads":
                return await self._test_threads_connection(creds)
            else:
                return False, f"Connection testing not implemented for {platform}"

        except Exception as e:
            error_msg = f"Connection test failed: {str(e)}"
            logger.error(f"Error testing {platform} connection: {str(e)}")

            # Update test status in database
            self._update_test_status(platform, "failed", error_msg)
            return False, error_msg

    async def _test_twitter_connection(self, creds: Dict[str, Any]) -> Tuple[bool, str]:
        """Test Twitter OAuth 1.0a connection by generating a signature"""
        try:
            from utils.twitter_oauth1 import generate_oauth_signature

            # Test signature generation
            test_params = {
                "oauth_consumer_key": creds["api_key"],
                "oauth_signature_method": "HMAC-SHA1",
                "oauth_timestamp": "1234567890",
                "oauth_nonce": "test_nonce",
                "oauth_version": "1.0",
            }

            signature = generate_oauth_signature(
                method="GET",
                url="https://api.twitter.com/1.1/account/verify_credentials.json",
                params=test_params,
                consumer_secret=creds["api_secret"],
                token_secret="",
            )

            if signature:
                self._update_test_status("twitter", "success", None)
                return True, "Twitter credentials validated successfully"
            else:
                self._update_test_status("twitter", "failed", "Signature generation failed")
                return False, "Failed to generate OAuth signature"

        except Exception as e:
            error_msg = f"Twitter connection test failed: {str(e)}"
            self._update_test_status("twitter", "failed", error_msg)
            return False, error_msg

    async def _test_linkedin_connection(self, creds: Dict[str, Any]) -> Tuple[bool, str]:
        """Test LinkedIn OAuth 2.0 credentials format"""
        try:
            # Basic validation - client_id and client_secret should be present and non-empty
            if not creds.get("client_id") or not creds.get("client_secret"):
                self._update_test_status("linkedin", "failed", "Missing client_id or client_secret")
                return False, "Invalid LinkedIn credentials format"

            # Additional format checks
            client_id = creds["client_id"]
            if len(client_id) < 10:  # LinkedIn client IDs are typically longer
                self._update_test_status("linkedin", "failed", "Client ID too short")
                return False, "LinkedIn client ID appears invalid"

            self._update_test_status("linkedin", "success", None)
            return True, "LinkedIn credentials format validated"

        except Exception as e:
            error_msg = f"LinkedIn connection test failed: {str(e)}"
            self._update_test_status("linkedin", "failed", error_msg)
            return False, error_msg

    async def _test_threads_connection(self, creds: Dict[str, Any]) -> Tuple[bool, str]:
        """Test Threads OAuth 2.0 credentials format"""
        try:
            # Basic validation
            if not creds.get("client_id") or not creds.get("client_secret"):
                self._update_test_status("threads", "failed", "Missing client_id or client_secret")
                return False, "Invalid Threads credentials format"

            # Threads uses numeric app IDs
            client_id = creds["client_id"]
            if not client_id.isdigit():
                self._update_test_status("threads", "failed", "App ID should be numeric")
                return False, "Threads app ID should be numeric"

            self._update_test_status("threads", "success", None)
            return True, "Threads credentials format validated"

        except Exception as e:
            error_msg = f"Threads connection test failed: {str(e)}"
            self._update_test_status("threads", "failed", error_msg)
            return False, error_msg

    def _update_test_status(self, platform: str, status: str, error_message: Optional[str]):
        """Update test status in database"""
        try:
            cred = (
                self.db.query(OAuthPlatformCredential)
                .filter(OAuthPlatformCredential.platform == platform)
                .first()
            )

            if cred:
                cred.test_status = status
                cred.last_tested_at = datetime.utcnow()
                cred.test_error_message = error_message
                self.db.commit()
        except Exception as e:
            logger.error(f"Error updating test status for {platform}: {str(e)}")
            self.db.rollback()
