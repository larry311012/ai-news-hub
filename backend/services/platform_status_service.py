"""
Platform Status Service

This service provides platform connection status and publish readiness checks.
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from database import Post
from database_social_media import SocialMediaConnection
from utils.social_connection_manager import SocialConnectionManager
from schemas.posts import PlatformConnectionStatus, ContentValidation, PlatformEnum

logger = logging.getLogger(__name__)


class PlatformStatusService:
    """
    Service for checking platform connection and publishing readiness

    Provides comprehensive status checks including:
    - OAuth connection status
    - Token expiration
    - Content validation
    - Publishing readiness
    """

    @classmethod
    def get_platform_status(
        cls,
        user_id: int,
        platform: str,
        db: Session
    ) -> PlatformConnectionStatus:
        """
        Get comprehensive status for a single platform

        Checks OAuth connection, token validity, and readiness to publish
        """
        manager = SocialConnectionManager(db)

        try:
            # Get connection status
            status_info = manager.get_connection_status(user_id, platform)

            connected = status_info.get('connected', False)
            is_expired = status_info.get('is_expired', False)
            username = status_info.get('username')
            error = status_info.get('error')

            # Determine if can publish
            can_publish = connected and not is_expired

            # Get last used time if connected
            last_used = None
            if connected:
                connection = manager.get_connection(user_id, platform)
                if connection:
                    last_used = connection.last_used_at

            return PlatformConnectionStatus(
                platform=platform,
                connected=connected,
                username=username,
                needs_reconnection=is_expired,
                is_expired=is_expired,
                last_used=last_used,
                error=error,
                can_publish=can_publish
            )

        except Exception as e:
            logger.error(f"Error checking {platform} status for user {user_id}: {e}")
            return PlatformConnectionStatus(
                platform=platform,
                connected=False,
                needs_reconnection=False,
                is_expired=False,
                error=str(e),
                can_publish=False
            )

    @classmethod
    def get_all_platform_statuses(
        cls,
        user_id: int,
        platforms: List[str],
        db: Session
    ) -> List[PlatformConnectionStatus]:
        """
        Get status for multiple platforms

        Returns a list of platform statuses for the requested platforms
        """
        statuses = []

        for platform in platforms:
            status = cls.get_platform_status(user_id, platform, db)
            statuses.append(status)

        return statuses

    @classmethod
    def get_post_platform_statuses(
        cls,
        post_id: int,
        user_id: int,
        db: Session
    ) -> List[PlatformConnectionStatus]:
        """
        Get platform statuses for a specific post

        Returns status for all platforms associated with the post
        """
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user_id
        ).first()

        if not post:
            return []

        platforms = post.platforms or []
        return cls.get_all_platform_statuses(user_id, platforms, db)

    @classmethod
    def check_publish_readiness(
        cls,
        user_id: int,
        platforms: List[str],
        db: Session
    ) -> Dict[str, Dict]:
        """
        Check if ready to publish to requested platforms

        Returns:
            {
                'ready': bool,
                'missing_connections': List[str],
                'expired_connections': List[str],
                'platform_details': Dict[str, PlatformConnectionStatus]
            }
        """
        statuses = cls.get_all_platform_statuses(user_id, platforms, db)

        missing = []
        expired = []
        platform_details = {}

        for status in statuses:
            platform_details[status.platform] = status

            if not status.connected:
                missing.append(status.platform)
            elif status.is_expired:
                expired.append(status.platform)

        ready = len(missing) == 0 and len(expired) == 0

        return {
            'ready': ready,
            'missing_connections': missing,
            'expired_connections': expired,
            'platform_details': platform_details
        }

    @classmethod
    def validate_post_content(
        cls,
        post_id: int,
        db: Session
    ) -> Dict[str, ContentValidation]:
        """
        Validate content for all platforms in a post

        Returns validation results keyed by platform
        """
        from services.post_generation_service import PostGenerationService

        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return {}

        validations = {}

        # Validate each platform's content
        if post.twitter_content and 'twitter' in (post.platforms or []):
            validations['twitter'] = PostGenerationService.validate_content(
                'twitter',
                post.twitter_content
            )

        if post.linkedin_content and 'linkedin' in (post.platforms or []):
            validations['linkedin'] = PostGenerationService.validate_content(
                'linkedin',
                post.linkedin_content
            )

        if post.threads_content and 'threads' in (post.platforms or []):
            validations['threads'] = PostGenerationService.validate_content(
                'threads',
                post.threads_content
            )

        return validations

    @classmethod
    def get_publishing_errors(
        cls,
        user_id: int,
        post_id: int,
        platforms: List[str],
        db: Session
    ) -> Dict[str, List[str]]:
        """
        Get all potential publishing errors

        Checks connections, tokens, and content validation
        Returns errors organized by platform
        """
        errors = {}

        # Check connection status
        readiness = cls.check_publish_readiness(user_id, platforms, db)

        for platform in platforms:
            platform_errors = []

            # Check connection
            if platform in readiness['missing_connections']:
                platform_errors.append(f"No {platform} connection. Please connect in Settings.")

            # Check expiration
            if platform in readiness['expired_connections']:
                platform_errors.append(f"{platform} token expired. Please reconnect.")

            # Check content validation
            validations = cls.validate_post_content(post_id, db)
            if platform in validations:
                validation = validations[platform]
                if not validation.is_valid:
                    platform_errors.extend(validation.errors)

            if platform_errors:
                errors[platform] = platform_errors

        return errors
