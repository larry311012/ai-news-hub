"""
Social Media Connection Manager

This service manages social media connections, token storage, and refreshing.
Provides a high-level interface for working with social media OAuth tokens.
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from database_social_media import SocialMediaConnection
from utils.encryption import encrypt_value, decrypt_value
from utils.social_oauth import (
    is_token_expired,
    calculate_token_expiry,
    refresh_linkedin_token,
    refresh_twitter_token,
    refresh_threads_token,
    get_linkedin_user_info,
    get_twitter_user_info,
    get_threads_user_info,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SocialConnectionManager:
    """
    Manager for social media connections and OAuth tokens.

    Handles token storage, retrieval, refresh, and validation.
    """

    def __init__(self, db: Session):
        """
        Initialize the connection manager.

        Args:
            db: Database session
        """
        self.db = db

    def create_connection(
        self,
        user_id: int,
        platform: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
        scope: Optional[str] = None,
        platform_user_id: Optional[str] = None,
        platform_username: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SocialMediaConnection:
        """
        Create or update a social media connection.

        Args:
            user_id: User ID
            platform: Platform name (linkedin, twitter, threads)
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            expires_in: Token expiration in seconds (optional)
            scope: OAuth scopes granted
            platform_user_id: Platform's user ID
            platform_username: Platform username/handle
            metadata: Additional platform-specific metadata

        Returns:
            SocialMediaConnection object
        """
        try:
            # Check if connection already exists
            existing = (
                self.db.query(SocialMediaConnection)
                .filter(
                    SocialMediaConnection.user_id == user_id,
                    SocialMediaConnection.platform == platform,
                )
                .first()
            )

            # Encrypt tokens
            encrypted_access_token = encrypt_value(access_token)
            encrypted_refresh_token = encrypt_value(refresh_token) if refresh_token else None

            # Calculate expiration
            expires_at = None
            if expires_in:
                expires_at = calculate_token_expiry(expires_in)

            if existing:
                # Update existing connection
                existing.encrypted_access_token = encrypted_access_token
                existing.encrypted_refresh_token = encrypted_refresh_token
                existing.expires_at = expires_at
                existing.scope = scope
                existing.platform_user_id = platform_user_id
                existing.platform_username = platform_username
                existing.platform_metadata = metadata
                existing.is_active = True
                existing.error_message = None
                existing.updated_at = datetime.utcnow()

                self.db.commit()
                self.db.refresh(existing)

                logger.info(f"Updated {platform} connection for user {user_id}")
                return existing
            else:
                # Create new connection
                connection = SocialMediaConnection(
                    user_id=user_id,
                    platform=platform,
                    encrypted_access_token=encrypted_access_token,
                    encrypted_refresh_token=encrypted_refresh_token,
                    expires_at=expires_at,
                    scope=scope,
                    platform_user_id=platform_user_id,
                    platform_username=platform_username,
                    platform_metadata=metadata,
                    is_active=True,
                )

                self.db.add(connection)
                self.db.commit()
                self.db.refresh(connection)

                logger.info(f"Created {platform} connection for user {user_id}")
                return connection

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating {platform} connection: {str(e)}")
            raise

    def get_connection(
        self, user_id: int, platform: str, auto_refresh: bool = True
    ) -> Optional[SocialMediaConnection]:
        """
        Get a social media connection for a user.

        Args:
            user_id: User ID
            platform: Platform name (linkedin, twitter, threads)
            auto_refresh: Automatically refresh expired tokens

        Returns:
            SocialMediaConnection object or None if not found
        """
        connection = (
            self.db.query(SocialMediaConnection)
            .filter(
                SocialMediaConnection.user_id == user_id,
                SocialMediaConnection.platform == platform,
                SocialMediaConnection.is_active == True,
            )
            .first()
        )

        if not connection:
            return None

        # Check if token needs refresh
        if auto_refresh and is_token_expired(connection.expires_at):
            logger.info(f"Token expired for {platform} connection, attempting refresh")
            refreshed = self.refresh_connection(connection)
            if not refreshed:
                logger.warning(f"Failed to refresh {platform} token for user {user_id}")
                connection.is_active = False
                connection.error_message = "Token expired and refresh failed"
                self.db.commit()
                return None

        # Update last used time
        connection.last_used_at = datetime.utcnow()
        self.db.commit()

        return connection

    def get_all_connections(self, user_id: int, active_only: bool = True):
        """
        Get all social media connections for a user.

        Args:
            user_id: User ID
            active_only: Only return active connections

        Returns:
            List of SocialMediaConnection objects
        """
        query = self.db.query(SocialMediaConnection).filter(
            SocialMediaConnection.user_id == user_id
        )

        if active_only:
            query = query.filter(SocialMediaConnection.is_active == True)

        return query.all()

    def refresh_connection(self, connection: SocialMediaConnection) -> bool:
        """
        Refresh an expired OAuth token.

        Args:
            connection: SocialMediaConnection object

        Returns:
            True if refresh successful, False otherwise
        """
        try:
            import asyncio

            # Refresh based on platform
            new_tokens = None
            if connection.platform == "linkedin":
                # Note: LinkedIn typically doesn't provide refresh tokens
                logger.warning("LinkedIn refresh not supported - tokens expire after 60 days")
                return False

            elif connection.platform == "twitter":
                # Twitter uses refresh_token
                refresh_token = decrypt_value(connection.encrypted_refresh_token)
                if not refresh_token:
                    logger.error(f"No refresh token available for {connection.platform}")
                    return False
                new_tokens = asyncio.run(refresh_twitter_token(refresh_token))

            elif connection.platform == "threads":
                # For Threads, we refresh using the current access token (not refresh_token)
                access_token = decrypt_value(connection.encrypted_access_token)
                if not access_token:
                    logger.error(f"No access token available for {connection.platform}")
                    return False
                new_tokens = asyncio.run(refresh_threads_token(access_token))

            if not new_tokens:
                logger.error(f"Failed to refresh {connection.platform} token")
                return False

            # Update connection with new tokens
            connection.encrypted_access_token = encrypt_value(new_tokens["access_token"])

            if "refresh_token" in new_tokens:
                connection.encrypted_refresh_token = encrypt_value(new_tokens["refresh_token"])

            if "expires_in" in new_tokens:
                connection.expires_at = calculate_token_expiry(new_tokens["expires_in"])

            connection.error_message = None
            connection.updated_at = datetime.utcnow()

            self.db.commit()
            logger.info(f"Successfully refreshed {connection.platform} token")
            return True

        except Exception as e:
            logger.error(f"Error refreshing {connection.platform} token: {str(e)}")
            connection.error_message = str(e)
            self.db.commit()
            return False

    def disconnect(self, user_id: int, platform: str) -> bool:
        """
        Disconnect a social media platform.

        Args:
            user_id: User ID
            platform: Platform name

        Returns:
            True if disconnected, False if not found
        """
        connection = (
            self.db.query(SocialMediaConnection)
            .filter(
                SocialMediaConnection.user_id == user_id, SocialMediaConnection.platform == platform
            )
            .first()
        )

        if not connection:
            return False

        # Mark as inactive instead of deleting (for audit trail)
        connection.is_active = False
        connection.updated_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Disconnected {platform} for user {user_id}")
        return True

    def delete_connection(self, user_id: int, platform: str) -> bool:
        """
        Permanently delete a social media connection.

        Args:
            user_id: User ID
            platform: Platform name

        Returns:
            True if deleted, False if not found
        """
        connection = (
            self.db.query(SocialMediaConnection)
            .filter(
                SocialMediaConnection.user_id == user_id, SocialMediaConnection.platform == platform
            )
            .first()
        )

        if not connection:
            return False

        self.db.delete(connection)
        self.db.commit()

        logger.info(f"Deleted {platform} connection for user {user_id}")
        return True

    def get_decrypted_token(self, connection: SocialMediaConnection) -> Optional[str]:
        """
        Get decrypted access token from a connection.

        Args:
            connection: SocialMediaConnection object

        Returns:
            Decrypted access token or None
        """
        return decrypt_value(connection.encrypted_access_token)

    async def validate_connection(self, connection: SocialMediaConnection) -> bool:
        """
        Validate a connection by making a test API call.

        Args:
            connection: SocialMediaConnection object

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            access_token = self.get_decrypted_token(connection)
            if not access_token:
                return False

            # Make a test API call based on platform
            if connection.platform == "linkedin":
                user_info = await get_linkedin_user_info(access_token)
            elif connection.platform == "twitter":
                user_info = await get_twitter_user_info(access_token)
            elif connection.platform == "threads":
                user_info = await get_threads_user_info(access_token)
            else:
                return False

            if user_info:
                # Update metadata with latest user info
                connection.platform_metadata = user_info
                connection.updated_at = datetime.utcnow()
                connection.error_message = None
                self.db.commit()
                return True

            return False

        except Exception as e:
            logger.error(f"Error validating {connection.platform} connection: {str(e)}")
            connection.error_message = str(e)
            self.db.commit()
            return False

    def get_connection_status(self, user_id: int, platform: str) -> Dict[str, Any]:
        """
        Get detailed status of a social media connection.

        Args:
            user_id: User ID
            platform: Platform name

        Returns:
            Dictionary with connection status details
        """
        connection = self.get_connection(user_id, platform, auto_refresh=False)

        if not connection:
            return {"connected": False, "platform": platform, "error": "No connection found"}

        is_expired = is_token_expired(connection.expires_at)
        has_refresh_token = connection.encrypted_refresh_token is not None

        return {
            "connected": connection.is_active,
            "platform": platform,
            "username": connection.platform_username,
            "user_id": connection.platform_user_id,
            "expires_at": connection.expires_at.isoformat() if connection.expires_at else None,
            "is_expired": is_expired,
            "can_refresh": has_refresh_token,
            "last_used": connection.last_used_at.isoformat() if connection.last_used_at else None,
            "error": connection.error_message,
            "metadata": connection.platform_metadata,
        }
