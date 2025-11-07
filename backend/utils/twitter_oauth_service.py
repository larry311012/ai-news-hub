"""
Twitter OAuth 1.0a Service - Enhanced Implementation

This service provides a complete Twitter OAuth 1.0a implementation following
the official Twitter documentation with enhanced security and production features.

Official Documentation:
https://developer.twitter.com/en/docs/authentication/oauth-1-0a/obtaining-user-access-tokens

Key Features:
- Complete 3-legged OAuth 1.0a flow
- CSRF protection via state parameter
- Database-backed request token storage (production-ready)
- Comprehensive error handling
- Rate limit tracking
- Audit logging
- Token validation and refresh
"""

import secrets
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database import User
from database_social_media import SocialMediaConnection
from database_twitter_oauth import (
    TwitterOAuthRequestToken,
    TwitterOAuthState,
    TwitterOAuthAudit,
    TwitterRateLimitLog
)
from utils.twitter_oauth1 import (
    get_request_token,
    get_authorization_url,
    get_access_token,
    get_user_info,
    is_oauth1_configured
)
from utils.encryption import encrypt_value, decrypt_value
from utils.social_connection_manager import SocialConnectionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TwitterOAuthService:
    """
    Complete Twitter OAuth 1.0a service with enhanced security and production features.

    This service manages the entire OAuth flow:
    1. Initiate OAuth (get request token)
    2. User authorization (redirect to Twitter)
    3. Handle callback (exchange for access token)
    4. Store and manage tokens
    5. Validate and refresh connections
    """

    def __init__(self, db: Session):
        """
        Initialize the Twitter OAuth service.

        Args:
            db: Database session
        """
        self.db = db
        self.connection_manager = SocialConnectionManager(db)

    def generate_state(self) -> str:
        """
        Generate a cryptographically secure state parameter for CSRF protection.

        Returns:
            Random 32-byte hex string
        """
        return secrets.token_hex(32)

    async def initiate_oauth(
        self,
        user: User,
        return_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Step 1: Initiate Twitter OAuth 1.0a flow.

        This method:
        1. Validates OAuth configuration
        2. Generates CSRF state
        3. Obtains request token from Twitter
        4. Stores request token securely
        5. Creates OAuth state record
        6. Returns authorization URL

        Args:
            user: User object
            return_url: Frontend URL to redirect after OAuth
            user_agent: User's browser user agent
            ip_address: User's IP address

        Returns:
            Dictionary with:
            - success: bool
            - authorization_url: str (URL to redirect user to)
            - state: str (CSRF state parameter)
            - platform: str ("twitter")
            - oauth_version: str ("1.0a")

        Raises:
            ValueError: If OAuth not configured
            Exception: If request token request fails
        """
        try:
            # Validate configuration
            if not is_oauth1_configured():
                self._audit_log(
                    user_id=user.id,
                    operation="initiate_oauth",
                    success=False,
                    error_message="Twitter OAuth 1.0a not configured",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                raise ValueError("Twitter OAuth 1.0a is not configured on this server")

            # Generate CSRF state
            state = self.generate_state()

            # Step 1: Get request token from Twitter
            request_token_data = await get_request_token()

            if not request_token_data:
                self._audit_log(
                    user_id=user.id,
                    operation="initiate_oauth",
                    success=False,
                    error_message="Failed to obtain request token from Twitter",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                raise Exception("Failed to obtain request token from Twitter")

            oauth_token = request_token_data["oauth_token"]
            oauth_token_secret = request_token_data["oauth_token_secret"]

            # Encrypt token secret before storage
            encrypted_secret = encrypt_value(oauth_token_secret)

            # Store request token in database
            request_token_record = TwitterOAuthRequestToken(
                oauth_token=oauth_token,
                oauth_token_secret=encrypted_secret,
                state=state,
                user_id=user.id,
                return_url=return_url,
                expires_at=TwitterOAuthRequestToken.create_token_expiry(minutes=10),
                created_at=datetime.utcnow(),
                used=False
            )
            self.db.add(request_token_record)

            # Create OAuth state record
            oauth_state = TwitterOAuthState(
                state=state,
                user_id=user.id,
                flow_step="initiated",
                request_token=oauth_token,
                access_token_obtained=False,
                user_agent=user_agent,
                ip_address=ip_address,
                initiated_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=15)
            )
            self.db.add(oauth_state)

            self.db.commit()

            # Generate authorization URL
            auth_url = get_authorization_url(oauth_token)

            # Audit log
            self._audit_log(
                user_id=user.id,
                operation="initiate_oauth",
                success=True,
                state=state,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=f"Request token: {oauth_token[:10]}..."
            )

            logger.info(f"Initiated Twitter OAuth for user {user.id}, state: {state[:10]}...")

            return {
                "success": True,
                "authorization_url": auth_url,
                "state": state,
                "platform": "twitter",
                "oauth_version": "1.0a"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error initiating Twitter OAuth: {str(e)}")
            raise

    async def handle_callback(
        self,
        oauth_token: str,
        oauth_verifier: str,
        state: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Step 2: Handle Twitter OAuth callback.

        This method:
        1. Validates CSRF state
        2. Retrieves request token from database
        3. Validates request token (not expired, not used)
        4. Exchanges request token for access token
        5. Gets user info from Twitter
        6. Stores connection in database
        7. Cleans up temporary data

        Args:
            oauth_token: Request token from Twitter callback
            oauth_verifier: OAuth verifier from Twitter
            state: CSRF state parameter (optional but recommended)
            user_agent: User's browser user agent
            ip_address: User's IP address

        Returns:
            Dictionary with:
            - success: bool
            - connection: SocialMediaConnection object
            - username: str (Twitter username)
            - return_url: str (Frontend redirect URL)

        Raises:
            ValueError: If state invalid or token expired
            Exception: If access token exchange fails
        """
        try:
            # Step 1: Validate and retrieve request token
            request_token_record = self.db.query(TwitterOAuthRequestToken).filter(
                TwitterOAuthRequestToken.oauth_token == oauth_token
            ).first()

            if not request_token_record:
                self._audit_log(
                    user_id=None,
                    operation="handle_callback",
                    success=False,
                    error_message="Request token not found",
                    state=state,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                raise ValueError("Invalid or expired OAuth token")

            # Validate CSRF state
            if state and request_token_record.state != state:
                self._audit_log(
                    user_id=request_token_record.user_id,
                    operation="handle_callback",
                    success=False,
                    error_message="CSRF state mismatch",
                    state=state,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                raise ValueError("Invalid state parameter - possible CSRF attack")

            # Validate token status
            if not request_token_record.is_valid():
                error_msg = "Token expired" if request_token_record.is_expired() else "Token already used"
                self._audit_log(
                    user_id=request_token_record.user_id,
                    operation="handle_callback",
                    success=False,
                    error_message=error_msg,
                    state=state,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                raise ValueError(error_msg)

            # Mark token as used
            request_token_record.used = True
            user_id = request_token_record.user_id
            return_url = request_token_record.return_url

            # Decrypt token secret
            oauth_token_secret = decrypt_value(request_token_record.oauth_token_secret)
            if not oauth_token_secret:
                raise Exception("Failed to decrypt request token secret")

            # Step 2: Exchange for access token
            access_token_data = await get_access_token(
                oauth_token=oauth_token,
                oauth_token_secret=oauth_token_secret,
                oauth_verifier=oauth_verifier
            )

            if not access_token_data:
                self._audit_log(
                    user_id=user_id,
                    operation="handle_callback",
                    success=False,
                    error_message="Failed to exchange request token for access token",
                    state=state,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                raise Exception("Failed to authenticate with Twitter")

            access_token = access_token_data["oauth_token"]
            access_token_secret = access_token_data["oauth_token_secret"]
            twitter_user_id = access_token_data["user_id"]
            twitter_username = access_token_data["screen_name"]

            # Step 3: Get detailed user info
            user_info = await get_user_info(access_token, access_token_secret)

            if not user_info:
                logger.warning("Failed to get detailed user info, using basic data")
                user_info = {
                    "id": twitter_user_id,
                    "username": twitter_username,
                    "name": twitter_username
                }

            # Step 4: Store connection
            connection = self.connection_manager.create_connection(
                user_id=user_id,
                platform="twitter",
                access_token=access_token,
                refresh_token=access_token_secret,  # Store secret in refresh_token field
                expires_in=None,  # OAuth 1.0a tokens don't expire
                scope=None,  # OAuth 1.0a doesn't use scopes
                platform_user_id=user_info.get("id"),
                platform_username=user_info.get("username"),
                metadata=user_info
            )

            # Update OAuth state
            oauth_state = self.db.query(TwitterOAuthState).filter(
                TwitterOAuthState.state == request_token_record.state
            ).first()

            if oauth_state:
                oauth_state.flow_step = "completed"
                oauth_state.access_token_obtained = True
                oauth_state.completed_at = datetime.utcnow()

            # Clean up old request tokens (older than 15 minutes)
            self._cleanup_expired_tokens()

            self.db.commit()

            # Audit log
            self._audit_log(
                user_id=user_id,
                operation="handle_callback",
                success=True,
                state=state,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=f"Connected @{user_info.get('username')}"
            )

            logger.info(f"Twitter OAuth completed for user {user_id} (@{user_info.get('username')})")

            return {
                "success": True,
                "connection": connection,
                "username": user_info.get("username"),
                "user_id": user_info.get("id"),
                "return_url": return_url,
                "platform": "twitter",
                "oauth_version": "1.0a"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error handling Twitter OAuth callback: {str(e)}")
            raise

    def validate_connection(self, user_id: int) -> bool:
        """
        Validate a Twitter connection by making a test API call.

        Args:
            user_id: User ID

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            connection = self.connection_manager.get_connection(
                user_id=user_id,
                platform="twitter",
                auto_refresh=False
            )

            if not connection:
                return False

            # OAuth 1.0a tokens don't expire, but we can validate by calling verify_credentials
            access_token = decrypt_value(connection.encrypted_access_token)
            access_token_secret = decrypt_value(connection.encrypted_refresh_token)

            if not access_token or not access_token_secret:
                logger.error(f"Failed to decrypt tokens for user {user_id}")
                return False

            # Make validation request
            import asyncio
            user_info = asyncio.run(get_user_info(access_token, access_token_secret))

            if user_info:
                # Update metadata with latest info
                connection.platform_metadata = user_info
                connection.last_used_at = datetime.utcnow()
                connection.error_message = None
                self.db.commit()

                self._audit_log(
                    user_id=user_id,
                    operation="validate_connection",
                    success=True,
                    metadata=f"Validated @{user_info.get('username')}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error validating Twitter connection: {str(e)}")
            self._audit_log(
                user_id=user_id,
                operation="validate_connection",
                success=False,
                error_message=str(e)
            )
            return False

    def disconnect(self, user_id: int) -> bool:
        """
        Disconnect Twitter account.

        Args:
            user_id: User ID

        Returns:
            True if disconnected successfully
        """
        try:
            success = self.connection_manager.disconnect(user_id, "twitter")

            if success:
                self._audit_log(
                    user_id=user_id,
                    operation="disconnect",
                    success=True
                )
                logger.info(f"Disconnected Twitter for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error disconnecting Twitter: {str(e)}")
            self._audit_log(
                user_id=user_id,
                operation="disconnect",
                success=False,
                error_message=str(e)
            )
            return False

    def _cleanup_expired_tokens(self):
        """
        Clean up expired request tokens and OAuth states.

        Removes records older than 15 minutes to prevent database bloat.
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=15)

            # Delete expired request tokens
            deleted_tokens = self.db.query(TwitterOAuthRequestToken).filter(
                TwitterOAuthRequestToken.expires_at < cutoff_time
            ).delete()

            # Delete expired OAuth states
            deleted_states = self.db.query(TwitterOAuthState).filter(
                TwitterOAuthState.expires_at < cutoff_time
            ).delete()

            self.db.commit()

            if deleted_tokens > 0 or deleted_states > 0:
                logger.debug(f"Cleaned up {deleted_tokens} tokens and {deleted_states} states")

        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {str(e)}")
            self.db.rollback()

    def _audit_log(
        self,
        operation: str,
        success: bool,
        user_id: Optional[int] = None,
        state: Optional[str] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[str] = None
    ):
        """
        Create an audit log entry for OAuth operations.

        Args:
            operation: Operation name
            success: Whether operation succeeded
            user_id: User ID (if available)
            state: CSRF state
            error_message: Error message if failed
            ip_address: User's IP address
            user_agent: User's browser user agent
            metadata: Additional metadata
        """
        try:
            audit_log = TwitterOAuthAudit(
                user_id=user_id,
                operation=operation,
                success=success,
                oauth_version="1.0a",
                state=state,
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=error_message,
                metadata=metadata,
                created_at=datetime.utcnow()
            )
            self.db.add(audit_log)
            self.db.commit()

        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")
            self.db.rollback()

    def get_connection_status(self, user_id: int) -> Dict[str, Any]:
        """
        Get detailed status of Twitter connection.

        Args:
            user_id: User ID

        Returns:
            Dictionary with connection status details
        """
        return self.connection_manager.get_connection_status(user_id, "twitter")

    def get_oauth_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get OAuth statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with OAuth statistics
        """
        try:
            # Count OAuth operations
            total_operations = self.db.query(TwitterOAuthAudit).filter(
                TwitterOAuthAudit.user_id == user_id
            ).count()

            successful_operations = self.db.query(TwitterOAuthAudit).filter(
                TwitterOAuthAudit.user_id == user_id,
                TwitterOAuthAudit.success == True
            ).count()

            failed_operations = total_operations - successful_operations

            # Get last operation
            last_operation = self.db.query(TwitterOAuthAudit).filter(
                TwitterOAuthAudit.user_id == user_id
            ).order_by(TwitterOAuthAudit.created_at.desc()).first()

            # Get current connection
            connection = self.connection_manager.get_connection(
                user_id=user_id,
                platform="twitter",
                auto_refresh=False
            )

            return {
                "total_operations": total_operations,
                "successful_operations": successful_operations,
                "failed_operations": failed_operations,
                "last_operation": {
                    "operation": last_operation.operation,
                    "success": last_operation.success,
                    "timestamp": last_operation.created_at.isoformat()
                } if last_operation else None,
                "connection": {
                    "connected": bool(connection and connection.is_active),
                    "username": connection.platform_username if connection else None,
                    "connected_at": connection.created_at.isoformat() if connection else None
                } if connection else None
            }

        except Exception as e:
            logger.error(f"Error getting OAuth stats: {str(e)}")
            return {
                "error": str(e)
            }
