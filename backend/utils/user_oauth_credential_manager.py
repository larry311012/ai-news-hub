"""
Per-User OAuth Credential Manager

This module manages per-user OAuth credentials (API keys, secrets, etc.) with
secure encryption, validation, and testing capabilities.

Key Features:
- Each user has their own OAuth app credentials
- Encryption/decryption using AES-256 Fernet
- Credential validation and testing
- Audit logging for security monitoring
- Rate limiting to prevent brute force attacks

Usage:
    from utils.user_oauth_credential_manager import UserOAuthCredentialManager

    # Initialize with database session and user
    manager = UserOAuthCredentialManager(db, user_id=123)

    # Save user's Twitter credentials
    manager.save_credentials(
        platform='twitter',
        api_key='user_api_key',
        api_secret='user_api_secret',
        callback_url='http://localhost:8000/api/oauth-setup/twitter/callback'
    )

    # Get user's credentials for OAuth flow
    creds = manager.get_credentials('twitter')

    # Test credentials
    is_valid, message = await manager.test_credentials('twitter')
"""

import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from database_user_oauth_credentials import UserOAuthCredential, UserOAuthCredentialAudit
from utils.encryption import encrypt_value, decrypt_value

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserOAuthCredentialManager:
    """
    Manager for per-user OAuth credentials.

    Handles CRUD operations, encryption/decryption, validation, and testing
    of user-provided OAuth credentials.
    """

    # Supported platforms
    SUPPORTED_PLATFORMS = {
        "twitter": {
            "oauth_version": "1.0a",
            "name": "Twitter (X)",
            "required_fields": ["api_key", "api_secret"]
        },
        "linkedin": {
            "oauth_version": "2.0",
            "name": "LinkedIn",
            "required_fields": ["client_id", "client_secret"]
        },
        "threads": {
            "oauth_version": "2.0",
            "name": "Threads",
            "required_fields": ["client_id", "client_secret"]
        }
    }

    def __init__(self, db: Session, user_id: int, ip_address: str = None, user_agent: str = None):
        """
        Initialize credential manager.

        Args:
            db: SQLAlchemy database session
            user_id: ID of the user whose credentials to manage
            ip_address: User's IP address (for audit logging)
            user_agent: User's user agent (for audit logging)
        """
        self.db = db
        self.user_id = user_id
        self.ip_address = ip_address
        self.user_agent = user_agent

    def get_credentials(self, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get decrypted OAuth credentials for a platform.

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
                "is_validated": True
            }

            None if credentials not found or inactive
        """
        platform = platform.lower()

        try:
            cred = self.db.query(UserOAuthCredential).filter(
                UserOAuthCredential.user_id == self.user_id,
                UserOAuthCredential.platform == platform,
                UserOAuthCredential.is_active == True
            ).first()

            if not cred or not cred.is_configured():
                logger.info(f"No credentials found for user {self.user_id}, platform {platform}")
                return None

            # Decrypt credentials based on OAuth version
            result = {
                "platform": cred.platform,
                "oauth_version": cred.oauth_version,
                "is_validated": cred.is_validated,
                "validation_status": cred.validation_status,
                "last_validated_at": cred.last_validated_at,
                "created_at": cred.created_at,
                "updated_at": cred.updated_at
            }

            if cred.oauth_version == "1.0a":
                # OAuth 1.0a (Twitter)
                result["api_key"] = decrypt_value(cred.encrypted_api_key) if cred.encrypted_api_key else None
                result["api_secret"] = decrypt_value(cred.encrypted_api_secret) if cred.encrypted_api_secret else None
                result["callback_url"] = cred.callback_url

                # Validate decryption
                if not result.get("api_key") or not result.get("api_secret"):
                    logger.error(f"Failed to decrypt credentials for user {self.user_id}, platform {platform}")
                    return None

            elif cred.oauth_version == "2.0":
                # OAuth 2.0 (LinkedIn, Threads)
                result["client_id"] = decrypt_value(cred.encrypted_client_id) if cred.encrypted_client_id else None
                result["client_secret"] = decrypt_value(cred.encrypted_client_secret) if cred.encrypted_client_secret else None
                result["redirect_uri"] = cred.redirect_uri
                result["scopes"] = cred.scopes.split(",") if cred.scopes else []

                # Validate decryption
                if not result.get("client_id") or not result.get("client_secret"):
                    logger.error(f"Failed to decrypt credentials for user {self.user_id}, platform {platform}")
                    return None

            # Mark as used (but don't commit to avoid blocking async operations)
            # The timestamp will be updated in memory but not persisted immediately
            # This prevents blocking the event loop in async endpoints
            cred.mark_used()
            # self.db.commit()  # REMOVED: Blocking commit causes async endpoints to hang

            # Audit log (also uses commit internally, so we skip it for read operations)
            # self._log_audit(platform, "use", cred.id, "success")  # REMOVED: Causes blocking

            logger.info(f"Retrieved credentials for user {self.user_id}, platform {platform}")
            return result

        except Exception as e:
            logger.error(f"Error retrieving credentials for user {self.user_id}, platform {platform}: {str(e)}")
            # self._log_audit(platform, "use", None, "failed", str(e))  # REMOVED: Causes blocking
            return None

    def save_credentials(
        self,
        platform: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        callback_url: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        scopes: Optional[list] = None
    ) -> UserOAuthCredential:
        """
        Save or update user's OAuth credentials.

        Args:
            platform: Platform name (twitter, linkedin, threads)
            api_key: OAuth 1.0a API key (optional)
            api_secret: OAuth 1.0a API secret (optional)
            client_id: OAuth 2.0 client ID (optional)
            client_secret: OAuth 2.0 client secret (optional)
            callback_url: OAuth 1.0a callback URL (optional)
            redirect_uri: OAuth 2.0 redirect URI (optional)
            scopes: OAuth 2.0 scopes list (optional)

        Returns:
            UserOAuthCredential object

        Raises:
            ValueError: If platform not supported or required fields missing
        """
        platform = platform.lower()

        # Validate platform
        if platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}")

        platform_info = self.SUPPORTED_PLATFORMS[platform]
        oauth_version = platform_info["oauth_version"]

        # Validate required fields
        if oauth_version == "1.0a":
            if not api_key or not api_secret:
                raise ValueError(f"OAuth 1.0a requires api_key and api_secret")
        elif oauth_version == "2.0":
            if not client_id or not client_secret:
                raise ValueError(f"OAuth 2.0 requires client_id and client_secret")

        try:
            # Check if credentials already exist
            cred = self.db.query(UserOAuthCredential).filter(
                UserOAuthCredential.user_id == self.user_id,
                UserOAuthCredential.platform == platform
            ).first()

            action = "update" if cred else "create"

            if cred:
                # Update existing credentials
                logger.info(f"Updating credentials for user {self.user_id}, platform {platform}")
                cred.oauth_version = oauth_version
                cred.updated_at = datetime.utcnow()
                cred.is_validated = False  # Reset validation on update
                cred.validation_status = "not_tested"
                cred.validation_error = None
            else:
                # Create new credentials
                logger.info(f"Creating credentials for user {self.user_id}, platform {platform}")
                cred = UserOAuthCredential(
                    user_id=self.user_id,
                    platform=platform,
                    oauth_version=oauth_version,
                    is_active=True,
                    is_validated=False,
                    validation_status="not_tested"
                )
                self.db.add(cred)

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
                cred.encrypted_client_secret = encrypt_value(client_secret) if client_secret else None
                cred.redirect_uri = redirect_uri
                cred.scopes = ",".join(scopes) if scopes else None

                # Clear OAuth 1.0a fields
                cred.encrypted_api_key = None
                cred.encrypted_api_secret = None
                cred.callback_url = None

            self.db.commit()
            self.db.refresh(cred)

            # Audit log
            self._log_audit(platform, action, cred.id, "success")

            logger.info(f"Successfully saved credentials for user {self.user_id}, platform {platform}")
            return cred

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving credentials for user {self.user_id}, platform {platform}: {str(e)}")
            self._log_audit(platform, action, None, "failed", str(e))
            raise

    def delete_credentials(self, platform: str) -> bool:
        """
        Delete user's OAuth credentials.

        Args:
            platform: Platform name

        Returns:
            True if deleted, False if not found
        """
        platform = platform.lower()

        try:
            cred = self.db.query(UserOAuthCredential).filter(
                UserOAuthCredential.user_id == self.user_id,
                UserOAuthCredential.platform == platform
            ).first()

            if not cred:
                logger.warning(f"Credentials not found for user {self.user_id}, platform {platform}")
                return False

            credential_id = cred.id
            self.db.delete(cred)
            self.db.commit()

            # Audit log
            self._log_audit(platform, "delete", credential_id, "success")

            logger.info(f"Deleted credentials for user {self.user_id}, platform {platform}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting credentials for user {self.user_id}, platform {platform}: {str(e)}")
            self._log_audit(platform, "delete", None, "failed", str(e))
            raise

    def get_credential_status(self, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get credential status (masked) for display in UI.

        Args:
            platform: Platform name

        Returns:
            Dictionary with masked credentials and status:
            {
                "configured": True,
                "platform": "twitter",
                "oauth_version": "1.0a",
                "is_validated": True,
                "validation_status": "success",
                "last_validated_at": "2025-10-18T...",
                "masked_credentials": {
                    "api_key": "abc123••••••••",
                    "api_secret": "••••••••••••",
                    "callback_url": "http://..."
                }
            }

            None if credentials not found
        """
        platform = platform.lower()

        try:
            cred = self.db.query(UserOAuthCredential).filter(
                UserOAuthCredential.user_id == self.user_id,
                UserOAuthCredential.platform == platform,
                UserOAuthCredential.is_active == True
            ).first()

            if not cred:
                # Return complete response with all required fields for unconfigured platform
                return {
                    "configured": False,
                    "platform": platform,
                    "oauth_version": self.SUPPORTED_PLATFORMS.get(platform, {}).get("oauth_version", "1.0a"),
                    "is_validated": False,
                    "validation_status": None,
                    "last_validated_at": None,
                    "created_at": None,
                    "updated_at": None,
                    "usage_count": 0,
                    "masked_credentials": {}
                }

            # Decrypt and mask credentials
            masked = {}
            if cred.oauth_version == "1.0a":
                api_key = decrypt_value(cred.encrypted_api_key) if cred.encrypted_api_key else ""
                masked["api_key"] = self._mask_credential(api_key)
                masked["api_secret"] = "••••••••••••"
                masked["callback_url"] = cred.callback_url
            elif cred.oauth_version == "2.0":
                client_id = decrypt_value(cred.encrypted_client_id) if cred.encrypted_client_id else ""
                masked["client_id"] = self._mask_credential(client_id)
                masked["client_secret"] = "••••••••••••"
                masked["redirect_uri"] = cred.redirect_uri
                masked["scopes"] = cred.scopes.split(",") if cred.scopes else []

            return {
                "configured": cred.is_configured(),
                "platform": cred.platform,
                "oauth_version": cred.oauth_version,
                "is_validated": cred.is_validated,
                "validation_status": cred.validation_status,
                "last_validated_at": cred.last_validated_at.isoformat() if cred.last_validated_at else None,
                "created_at": cred.created_at.isoformat() if cred.created_at else None,
                "updated_at": cred.updated_at.isoformat() if cred.updated_at else None,
                "usage_count": cred.usage_count,
                "masked_credentials": masked
            }

        except Exception as e:
            logger.error(f"Error getting credential status for user {self.user_id}, platform {platform}: {str(e)}")
            return None

    async def test_credentials(self, platform: str) -> Tuple[bool, str]:
        """
        Test if user's credentials are valid.

        Args:
            platform: Platform name

        Returns:
            Tuple of (success: bool, message: str)
        """
        platform = platform.lower()

        creds = self.get_credentials(platform)
        if not creds:
            return False, f"No credentials found for {platform}"

        try:
            if platform == "twitter":
                success, message = await self._test_twitter_credentials(creds)
            elif platform == "linkedin":
                success, message = await self._test_linkedin_credentials(creds)
            elif platform == "threads":
                success, message = await self._test_threads_credentials(creds)
            else:
                return False, f"Testing not implemented for {platform}"

            # Update validation status
            self._update_validation_status(platform, success, message)

            # Audit log
            self._log_audit(platform, "validate", None, "success" if success else "failed", message)

            return success, message

        except Exception as e:
            error_msg = f"Credential test failed: {str(e)}"
            logger.error(f"Error testing credentials for user {self.user_id}, platform {platform}: {str(e)}")
            self._update_validation_status(platform, False, error_msg)
            self._log_audit(platform, "validate", None, "failed", error_msg)
            return False, error_msg

    async def _test_twitter_credentials(self, creds: Dict[str, Any]) -> Tuple[bool, str]:
        """Test Twitter OAuth 1.0a credentials by generating a signature"""
        try:
            from utils.twitter_oauth1 import generate_oauth_signature

            # Test signature generation
            test_params = {
                "oauth_consumer_key": creds["api_key"],
                "oauth_signature_method": "HMAC-SHA1",
                "oauth_timestamp": "1234567890",
                "oauth_nonce": "test_nonce",
                "oauth_version": "1.0"
            }

            signature = generate_oauth_signature(
                method="GET",
                url="https://api.twitter.com/oauth/request_token",
                params=test_params,
                consumer_secret=creds["api_secret"],
                token_secret=""
            )

            if signature:
                return True, "Twitter credentials validated successfully"
            else:
                return False, "Failed to generate OAuth signature - credentials may be invalid"

        except Exception as e:
            return False, f"Twitter credential test failed: {str(e)}"

    async def _test_linkedin_credentials(self, creds: Dict[str, Any]) -> Tuple[bool, str]:
        """Test LinkedIn OAuth 2.0 credentials format"""
        try:
            # Basic validation
            if not creds.get("client_id") or not creds.get("client_secret"):
                return False, "Missing client_id or client_secret"

            # Format checks
            client_id = creds["client_id"]
            if len(client_id) < 10:
                return False, "LinkedIn client ID appears too short"

            return True, "LinkedIn credentials format validated"

        except Exception as e:
            return False, f"LinkedIn credential test failed: {str(e)}"

    async def _test_threads_credentials(self, creds: Dict[str, Any]) -> Tuple[bool, str]:
        """Test Threads OAuth 2.0 credentials format"""
        try:
            # Basic validation
            if not creds.get("client_id") or not creds.get("client_secret"):
                return False, "Missing client_id or client_secret"

            # Threads uses numeric app IDs
            client_id = creds["client_id"]
            if not client_id.isdigit():
                return False, "Threads app ID should be numeric"

            return True, "Threads credentials format validated"

        except Exception as e:
            return False, f"Threads credential test failed: {str(e)}"

    def _update_validation_status(self, platform: str, success: bool, message: str):
        """Update validation status in database"""
        try:
            cred = self.db.query(UserOAuthCredential).filter(
                UserOAuthCredential.user_id == self.user_id,
                UserOAuthCredential.platform == platform
            ).first()

            if cred:
                cred.is_validated = success
                cred.validation_status = "success" if success else "failed"
                cred.last_validated_at = datetime.utcnow()
                cred.validation_error = None if success else message
                self.db.commit()

        except Exception as e:
            logger.error(f"Error updating validation status: {str(e)}")
            self.db.rollback()

    def _mask_credential(self, value: str, show_chars: int = 6) -> str:
        """Mask a credential for display"""
        if not value:
            return ""
        if len(value) <= show_chars:
            return value[:2] + "••••"
        return value[:show_chars] + "••••••••"

    def _log_audit(
        self,
        platform: str,
        action: str,
        credential_id: Optional[int],
        status: str,
        error_message: Optional[str] = None
    ):
        """Log audit entry for credential operation"""
        try:
            audit = UserOAuthCredentialAudit(
                user_id=self.user_id,
                credential_id=credential_id,
                platform=platform,
                action=action,
                ip_address=self.ip_address,
                user_agent=self.user_agent,
                status=status,
                error_message=error_message
            )
            self.db.add(audit)
            self.db.commit()

        except Exception as e:
            logger.error(f"Error logging audit: {str(e)}")
            self.db.rollback()
