"""
Publishing Service (Phase 4 - Task 4.2)

Unified service for publishing posts to multiple social media platforms.
Handles publishing logic, error handling, rate limiting, and retry mechanisms.

Supports:
- Twitter (OAuth 1.0a)
- LinkedIn (OAuth 2.0)
- Instagram (OAuth 2.0)
- Threads (OAuth 2.0)
- Multi-platform batch publishing
- Automatic retry with exponential backoff
- Rate limit enforcement
- Status tracking
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import hashlib
import asyncio
from enum import Enum

from database import Post, User
from database_social_media import SocialMediaConnection
from database_publishing import (
    PostPublishingHistory,
    PublishingStatus,
    ErrorCategory,
    PublishingQueue,
    PublishingRateLimit
)
from utils.social_connection_manager import SocialConnectionManager

# Import platform-specific publishers
try:
    from src.publishers.instagram_publisher import InstagramPublisher
    from src.publishers.exceptions import (
        AuthenticationException,
        RateLimitException,
        PublishingException
    )
    PUBLISHERS_AVAILABLE = True
except ImportError:
    PUBLISHERS_AVAILABLE = False
    logging.warning("Publishers not available - mock mode enabled")

logger = logging.getLogger(__name__)


class PlatformLimits:
    """Platform-specific character limits and constraints"""

    TWITTER_MAX_CHARS = 280
    LINKEDIN_MAX_CHARS = 3000
    INSTAGRAM_MAX_CAPTION_CHARS = 2200
    THREADS_MAX_CHARS = 500

    LIMITS = {
        "twitter": TWITTER_MAX_CHARS,
        "linkedin": LINKEDIN_MAX_CHARS,
        "instagram": INSTAGRAM_MAX_CAPTION_CHARS,
        "threads": THREADS_MAX_CHARS
    }


class PublishingService:
    """
    Unified publishing service for all social media platforms.

    Features:
    - Multi-platform publishing
    - Error handling and categorization
    - Automatic retry with exponential backoff
    - Rate limit enforcement (100 publishes/hour per user)
    - Publishing history tracking
    - Content validation
    """

    # Rate limit: 100 publishes per hour per user
    RATE_LIMIT_MAX = 100
    RATE_LIMIT_WINDOW_SECONDS = 3600  # 1 hour

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAYS = [60, 300, 900]  # 1 min, 5 min, 15 min

    def __init__(self, db: Session):
        """
        Initialize publishing service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.connection_manager = SocialConnectionManager(db)

    # ========================================================================
    # Public API Methods
    # ========================================================================

    async def publish_to_platform(
        self,
        post_id: int,
        user_id: int,
        platform: str,
        content: str,
        media_urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Publish a single post to a single platform.

        Args:
            post_id: Post ID
            user_id: User ID
            platform: Platform name (twitter, linkedin, instagram, threads)
            content: Content to publish
            media_urls: Optional list of media URLs

        Returns:
            {
                "success": True/False,
                "platform": "twitter",
                "status": "success"|"failed"|"rate_limited",
                "platform_url": "https://twitter.com/...",
                "platform_post_id": "123456",
                "error": "Error message if failed",
                "error_category": "auth_error"|"validation_error"|...,
                "published_at": "2025-11-04T...",
                "retry_scheduled": True/False
            }

        Raises:
            ValueError: If invalid parameters
        """
        logger.info(f"Publishing post {post_id} to {platform} for user {user_id}")

        # Validate inputs
        if platform not in ["twitter", "linkedin", "instagram", "threads"]:
            raise ValueError(f"Unsupported platform: {platform}")

        # Check rate limit
        if not self._check_rate_limit(user_id, platform):
            return self._create_rate_limit_response(platform, user_id, post_id)

        # Get or create publishing history record
        history = self._get_or_create_history(
            post_id=post_id,
            user_id=user_id,
            platform=platform,
            content=content,
            media_urls=media_urls
        )

        # Update status to publishing
        history.status = PublishingStatus.PUBLISHING
        history.started_at = datetime.utcnow()
        self.db.commit()

        try:
            # Validate content length
            validation_result = self._validate_content(platform, content)
            if not validation_result["valid"]:
                return self._handle_validation_error(
                    history, validation_result["error"]
                )

            # Get platform connection
            connection = self.connection_manager.get_connection(
                user_id, platform, auto_refresh=True
            )

            if not connection:
                return self._handle_auth_error(
                    history, f"{platform.title()} not connected"
                )

            # Publish to platform
            result = await self._publish_to_platform_internal(
                platform=platform,
                connection=connection,
                content=content,
                media_urls=media_urls,
                user_id=user_id,
                post_id=post_id
            )

            if result["success"]:
                # Update history with success
                history.status = PublishingStatus.SUCCESS
                history.platform_post_id = result.get("platform_post_id")
                history.platform_url = result.get("platform_url")
                history.published_at = datetime.utcnow()
                history.publishing_metadata = result.get("metadata", {})
                self.db.commit()

                # Increment rate limit counter
                self._increment_rate_limit(user_id, platform)

                logger.info(f"Successfully published post {post_id} to {platform}")

                return {
                    "success": True,
                    "platform": platform,
                    "status": "success",
                    "platform_url": history.platform_url,
                    "platform_post_id": history.platform_post_id,
                    "published_at": history.published_at.isoformat() + "Z"
                }
            else:
                # Handle failure
                error_category = result.get("error_category", ErrorCategory.UNKNOWN_ERROR)
                error_message = result.get("error", "Unknown error")

                return self._handle_publishing_error(
                    history, error_category, error_message, result.get("error_details")
                )

        except Exception as e:
            logger.error(f"Unexpected error publishing to {platform}: {str(e)}", exc_info=True)
            return self._handle_publishing_error(
                history, ErrorCategory.UNKNOWN_ERROR, str(e)
            )

    async def publish_to_multiple(
        self,
        post_id: int,
        user_id: int,
        platforms: List[str],
        content_map: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Publish a post to multiple platforms simultaneously.

        Args:
            post_id: Post ID
            user_id: User ID
            platforms: List of platform names
            content_map: Optional platform-specific content
                         e.g., {"twitter": "tweet", "linkedin": "longer post"}

        Returns:
            {
                "post_id": 123,
                "results": {
                    "twitter": { "success": True, ... },
                    "linkedin": { "success": False, ... }
                },
                "summary": {
                    "total": 2,
                    "successful": 1,
                    "failed": 1,
                    "rate_limited": 0
                }
            }
        """
        logger.info(f"Publishing post {post_id} to {len(platforms)} platforms for user {user_id}")

        # Get post from database
        post = self.db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user_id
        ).first()

        if not post:
            return {
                "success": False,
                "error": "Post not found",
                "post_id": post_id
            }

        # Publish to each platform (in parallel)
        tasks = []
        for platform in platforms:
            # Get platform-specific content or use default
            content = content_map.get(platform) if content_map else None

            if not content:
                # Get content from post fields
                content = self._get_post_content_for_platform(post, platform)

            if not content:
                logger.warning(f"No content found for {platform} in post {post_id}")
                continue

            # Get media URLs for platform
            media_urls = self._get_media_urls_for_platform(post, platform)

            # Create publish task
            task = self.publish_to_platform(
                post_id=post_id,
                user_id=user_id,
                platform=platform,
                content=content,
                media_urls=media_urls
            )
            tasks.append((platform, task))

        # Execute all tasks in parallel
        results = {}
        for platform, task in tasks:
            try:
                result = await task
                results[platform] = result
            except Exception as e:
                logger.error(f"Error publishing to {platform}: {str(e)}")
                results[platform] = {
                    "success": False,
                    "platform": platform,
                    "error": str(e),
                    "error_category": "unknown_error"
                }

        # Calculate summary
        summary = {
            "total": len(results),
            "successful": sum(1 for r in results.values() if r.get("success")),
            "failed": sum(1 for r in results.values() if not r.get("success") and r.get("status") != "rate_limited"),
            "rate_limited": sum(1 for r in results.values() if r.get("status") == "rate_limited")
        }

        return {
            "post_id": post_id,
            "results": results,
            "summary": summary
        }

    def get_publishing_history(
        self,
        user_id: int,
        post_id: Optional[int] = None,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get publishing history with optional filters.

        Args:
            user_id: User ID
            post_id: Optional filter by post ID
            platform: Optional filter by platform
            status: Optional filter by status
            limit: Maximum results (default 50)
            offset: Pagination offset (default 0)

        Returns:
            {
                "total": 100,
                "limit": 50,
                "offset": 0,
                "items": [
                    {
                        "id": 1,
                        "post_id": 123,
                        "platform": "twitter",
                        "status": "success",
                        "platform_url": "...",
                        "published_at": "...",
                        ...
                    }
                ]
            }
        """
        query = self.db.query(PostPublishingHistory).filter(
            PostPublishingHistory.user_id == user_id
        )

        if post_id:
            query = query.filter(PostPublishingHistory.post_id == post_id)

        if platform:
            query = query.filter(PostPublishingHistory.platform == platform)

        if status:
            query = query.filter(PostPublishingHistory.status == status)

        # Order by most recent first
        query = query.order_by(PostPublishingHistory.created_at.desc())

        # Get total count
        total = query.count()

        # Apply pagination
        items = query.offset(offset).limit(limit).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [self._serialize_history(item) for item in items]
        }

    def get_publishing_status(self, publish_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific publishing attempt.

        Args:
            publish_id: Publishing history ID
            user_id: User ID (for authorization)

        Returns:
            Publishing history details or None if not found
        """
        history = self.db.query(PostPublishingHistory).filter(
            PostPublishingHistory.id == publish_id,
            PostPublishingHistory.user_id == user_id
        ).first()

        if not history:
            return None

        return self._serialize_history(history)

    async def retry_failed_publish(
        self,
        publish_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Retry a failed publishing attempt.

        Args:
            publish_id: Publishing history ID
            user_id: User ID (for authorization)

        Returns:
            New publishing result
        """
        history = self.db.query(PostPublishingHistory).filter(
            PostPublishingHistory.id == publish_id,
            PostPublishingHistory.user_id == user_id
        ).first()

        if not history:
            return {
                "success": False,
                "error": "Publishing history not found"
            }

        if history.status == PublishingStatus.SUCCESS:
            return {
                "success": False,
                "error": "Post already published successfully"
            }

        if history.retry_count >= history.max_retries:
            return {
                "success": False,
                "error": f"Maximum retries ({history.max_retries}) exceeded"
            }

        # Increment retry count
        history.retry_count += 1
        history.status = PublishingStatus.RETRYING
        self.db.commit()

        logger.info(
            f"Retrying publish {publish_id} (attempt {history.retry_count}/{history.max_retries})"
        )

        # Retry publish
        media_urls = history.media_urls if history.media_urls else None

        return await self.publish_to_platform(
            post_id=history.post_id,
            user_id=history.user_id,
            platform=history.platform,
            content=history.content,
            media_urls=media_urls
        )

    # ========================================================================
    # Internal Helper Methods
    # ========================================================================

    def _get_or_create_history(
        self,
        post_id: int,
        user_id: int,
        platform: str,
        content: str,
        media_urls: Optional[List[str]]
    ) -> PostPublishingHistory:
        """Get existing or create new publishing history record"""
        # Check if record exists
        history = self.db.query(PostPublishingHistory).filter(
            PostPublishingHistory.post_id == post_id,
            PostPublishingHistory.platform == platform
        ).first()

        if history:
            # Update existing record
            history.content = content
            history.content_hash = self._hash_content(content)
            history.media_urls = media_urls
            history.status = PublishingStatus.PENDING
            history.updated_at = datetime.utcnow()
        else:
            # Create new record
            history = PostPublishingHistory(
                post_id=post_id,
                user_id=user_id,
                platform=platform,
                content=content,
                content_hash=self._hash_content(content),
                media_urls=media_urls,
                status=PublishingStatus.PENDING
            )
            self.db.add(history)

        self.db.commit()
        return history

    def _hash_content(self, content: str) -> str:
        """Generate SHA-256 hash of content for deduplication"""
        return hashlib.sha256(content.encode()).hexdigest()

    def _validate_content(self, platform: str, content: str) -> Dict[str, Any]:
        """Validate content meets platform requirements"""
        max_length = PlatformLimits.LIMITS.get(platform)

        if not max_length:
            return {"valid": True}

        if len(content) > max_length:
            return {
                "valid": False,
                "error": f"Content exceeds {platform} limit of {max_length} characters (got {len(content)})"
            }

        return {"valid": True}

    def _check_rate_limit(self, user_id: int, platform: str) -> bool:
        """Check if user has exceeded rate limit"""
        # Get or create rate limit record
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.RATE_LIMIT_WINDOW_SECONDS)

        rate_limit = self.db.query(PublishingRateLimit).filter(
            PublishingRateLimit.user_id == user_id,
            PublishingRateLimit.platform == platform,
            PublishingRateLimit.window_end > now
        ).first()

        if not rate_limit:
            # No active rate limit window
            return True

        # Check if limit exceeded
        if rate_limit.requests_made >= rate_limit.limit_max:
            logger.warning(
                f"Rate limit exceeded for user {user_id} on {platform}: "
                f"{rate_limit.requests_made}/{rate_limit.limit_max}"
            )
            return False

        return True

    def _increment_rate_limit(self, user_id: int, platform: str):
        """Increment rate limit counter"""
        now = datetime.utcnow()
        window_start = now
        window_end = now + timedelta(seconds=self.RATE_LIMIT_WINDOW_SECONDS)

        # Get or create rate limit record
        rate_limit = self.db.query(PublishingRateLimit).filter(
            PublishingRateLimit.user_id == user_id,
            PublishingRateLimit.platform == platform,
            PublishingRateLimit.window_end > now
        ).first()

        if rate_limit:
            rate_limit.requests_made += 1
            rate_limit.updated_at = now
        else:
            rate_limit = PublishingRateLimit(
                user_id=user_id,
                platform=platform,
                endpoint="publish",
                limit_max=self.RATE_LIMIT_MAX,
                window_seconds=self.RATE_LIMIT_WINDOW_SECONDS,
                requests_made=1,
                window_start=window_start,
                window_end=window_end
            )
            self.db.add(rate_limit)

        self.db.commit()

    def _create_rate_limit_response(
        self,
        platform: str,
        user_id: int,
        post_id: int
    ) -> Dict[str, Any]:
        """Create response for rate-limited request"""
        # Get rate limit details
        now = datetime.utcnow()
        rate_limit = self.db.query(PublishingRateLimit).filter(
            PublishingRateLimit.user_id == user_id,
            PublishingRateLimit.platform == platform,
            PublishingRateLimit.window_end > now
        ).first()

        reset_at = rate_limit.window_end if rate_limit else now + timedelta(hours=1)

        return {
            "success": False,
            "platform": platform,
            "status": "rate_limited",
            "error": f"Rate limit exceeded for {platform}. Try again after {reset_at.isoformat()}",
            "error_category": "rate_limit_error",
            "rate_limit_reset_at": reset_at.isoformat() + "Z",
            "retry_scheduled": False
        }

    def _handle_validation_error(
        self,
        history: PostPublishingHistory,
        error_message: str
    ) -> Dict[str, Any]:
        """Handle content validation error"""
        history.status = PublishingStatus.FAILED
        history.error_category = ErrorCategory.VALIDATION_ERROR
        history.error_message = error_message
        self.db.commit()

        return {
            "success": False,
            "platform": history.platform,
            "status": "failed",
            "error": error_message,
            "error_category": "validation_error",
            "retry_scheduled": False
        }

    def _handle_auth_error(
        self,
        history: PostPublishingHistory,
        error_message: str
    ) -> Dict[str, Any]:
        """Handle authentication error"""
        history.status = PublishingStatus.FAILED
        history.error_category = ErrorCategory.AUTH_ERROR
        history.error_message = error_message
        self.db.commit()

        return {
            "success": False,
            "platform": history.platform,
            "status": "failed",
            "error": error_message,
            "error_category": "auth_error",
            "retry_scheduled": False
        }

    def _handle_publishing_error(
        self,
        history: PostPublishingHistory,
        error_category: str,
        error_message: str,
        error_details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Handle publishing error with retry logic"""
        history.status = PublishingStatus.FAILED
        history.error_category = error_category
        history.error_message = error_message
        history.error_details = error_details

        # Schedule retry if not exceeded max
        retry_scheduled = False
        if history.retry_count < self.MAX_RETRIES:
            retry_delay_seconds = self.RETRY_DELAYS[history.retry_count]
            history.next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay_seconds)
            retry_scheduled = True
            logger.info(
                f"Scheduled retry for publish {history.id} in {retry_delay_seconds} seconds"
            )

        self.db.commit()

        return {
            "success": False,
            "platform": history.platform,
            "status": "failed",
            "error": error_message,
            "error_category": error_category,
            "retry_scheduled": retry_scheduled,
            "next_retry_at": history.next_retry_at.isoformat() + "Z" if retry_scheduled else None
        }

    async def _publish_to_platform_internal(
        self,
        platform: str,
        connection: SocialMediaConnection,
        content: str,
        media_urls: Optional[List[str]],
        user_id: int,
        post_id: int
    ) -> Dict[str, Any]:
        """
        Internal method to publish to specific platform.

        This delegates to platform-specific implementation.
        """
        try:
            if platform == "instagram":
                return await self._publish_to_instagram(
                    connection, content, media_urls
                )
            elif platform == "twitter":
                return await self._publish_to_twitter(
                    connection, content, media_urls
                )
            elif platform == "linkedin":
                return await self._publish_to_linkedin(
                    connection, content, media_urls
                )
            elif platform == "threads":
                return await self._publish_to_threads(
                    connection, content, media_urls
                )
            else:
                return {
                    "success": False,
                    "error": f"Unsupported platform: {platform}",
                    "error_category": ErrorCategory.PLATFORM_ERROR
                }
        except Exception as e:
            logger.error(f"Error publishing to {platform}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_category": ErrorCategory.UNKNOWN_ERROR
            }

    async def _publish_to_instagram(
        self,
        connection: SocialMediaConnection,
        content: str,
        media_urls: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Publish to Instagram"""
        if not PUBLISHERS_AVAILABLE:
            return self._mock_publish_response("instagram")

        try:
            from src.publishers.instagram_publisher import InstagramPublisher

            # Get access token
            access_token = self.connection_manager.get_decrypted_token(connection)
            if not access_token:
                return {
                    "success": False,
                    "error": "Failed to decrypt Instagram access token",
                    "error_category": ErrorCategory.AUTH_ERROR
                }

            # Get Instagram account ID
            instagram_account_id = None
            if connection.platform_metadata:
                instagram_account_id = connection.platform_metadata.get("instagram_account_id")
            if not instagram_account_id:
                instagram_account_id = connection.platform_user_id

            if not instagram_account_id:
                return {
                    "success": False,
                    "error": "Instagram account ID not found",
                    "error_category": ErrorCategory.AUTH_ERROR
                }

            # Validate media URL
            if not media_urls or len(media_urls) == 0:
                return {
                    "success": False,
                    "error": "Instagram requires at least one image",
                    "error_category": ErrorCategory.VALIDATION_ERROR
                }

            image_url = media_urls[0]

            # Publish
            publisher = InstagramPublisher()
            result = await publisher.publish(
                image_url=image_url,
                caption=content,
                instagram_account_id=instagram_account_id,
                access_token=access_token
            )

            return result

        except AuthenticationException as e:
            return {
                "success": False,
                "error": str(e),
                "error_category": ErrorCategory.AUTH_ERROR
            }
        except RateLimitException as e:
            return {
                "success": False,
                "error": str(e),
                "error_category": ErrorCategory.RATE_LIMIT_ERROR
            }
        except PublishingException as e:
            return {
                "success": False,
                "error": str(e),
                "error_category": ErrorCategory.PLATFORM_ERROR
            }

    async def _publish_to_twitter(
        self,
        connection: SocialMediaConnection,
        content: str,
        media_urls: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Publish to Twitter - placeholder for implementation"""
        # TODO: Implement Twitter publishing using Twitter API v2
        logger.warning("Twitter publishing not yet implemented")
        return {
            "success": False,
            "error": "Twitter publishing not yet implemented",
            "error_category": ErrorCategory.PLATFORM_ERROR
        }

    async def _publish_to_linkedin(
        self,
        connection: SocialMediaConnection,
        content: str,
        media_urls: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Publish to LinkedIn - placeholder for implementation"""
        # TODO: Implement LinkedIn publishing using LinkedIn API
        logger.warning("LinkedIn publishing not yet implemented")
        return {
            "success": False,
            "error": "LinkedIn publishing not yet implemented",
            "error_category": ErrorCategory.PLATFORM_ERROR
        }

    async def _publish_to_threads(
        self,
        connection: SocialMediaConnection,
        content: str,
        media_urls: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Publish to Threads - placeholder for implementation"""
        # TODO: Implement Threads publishing using Threads API
        logger.warning("Threads publishing not yet implemented")
        return {
            "success": False,
            "error": "Threads publishing not yet implemented",
            "error_category": ErrorCategory.PLATFORM_ERROR
        }

    def _mock_publish_response(self, platform: str) -> Dict[str, Any]:
        """Mock response for testing without publishers"""
        return {
            "success": True,
            "platform": platform,
            "platform_post_id": f"mock_{platform}_id_12345",
            "platform_url": f"https://{platform}.com/p/mock_12345",
            "published_at": datetime.utcnow().isoformat() + "Z"
        }

    def _get_post_content_for_platform(self, post: Post, platform: str) -> Optional[str]:
        """Extract platform-specific content from post"""
        content_map = {
            "twitter": post.twitter_content,
            "linkedin": post.linkedin_content,
            "threads": post.threads_content,
            "instagram": post.instagram_caption
        }
        return content_map.get(platform)

    def _get_media_urls_for_platform(self, post: Post, platform: str) -> Optional[List[str]]:
        """Extract platform-specific media URLs from post"""
        if platform == "instagram" and post.instagram_image_url:
            return [post.instagram_image_url]
        return None

    def _serialize_history(self, history: PostPublishingHistory) -> Dict[str, Any]:
        """Convert history record to dictionary"""
        return {
            "id": history.id,
            "post_id": history.post_id,
            "platform": history.platform,
            "status": history.status,
            "platform_post_id": history.platform_post_id,
            "platform_url": history.platform_url,
            "error_category": history.error_category,
            "error_message": history.error_message,
            "retry_count": history.retry_count,
            "max_retries": history.max_retries,
            "next_retry_at": history.next_retry_at.isoformat() + "Z" if history.next_retry_at else None,
            "created_at": history.created_at.isoformat() + "Z",
            "published_at": history.published_at.isoformat() + "Z" if history.published_at else None
        }
