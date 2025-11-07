"""
Posts API Caching Layer

Provides cached database queries and cache invalidation strategies
for posts endpoints.

Caching Strategy:
- List posts: 1 minute TTL (high traffic, frequently updated)
- Single post: 5 minutes TTL (moderate traffic)
- Post status: 30 seconds TTL (generation status changes frequently)
- Connections: 5 minutes TTL (infrequent changes)

Cache Invalidation:
- On post create: invalidate user's post list
- On post update: invalidate specific post + user's post list
- On post delete: invalidate specific post + user's post list
- On post publish: invalidate specific post
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from loguru import logger

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from database import Post
from database_social_media import SocialMediaConnection
from utils.cache_manager import cache, cached, CacheManager
from config.redis_config import RedisConfig


# Cached database queries
class PostsCache:
    """Centralized caching for posts API endpoints."""

    def __init__(self):
        self.cache = CacheManager(namespace="posts")

    # =========================================================================
    # CACHED QUERIES
    # =========================================================================

    @staticmethod
    async def get_user_posts(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get user's posts with caching (1 minute TTL).

        Cache key: posts:user:{user_id}:list:skip:{skip}:limit:{limit}
        """
        cache_key = f"user:{user_id}:list:skip:{skip}:limit:{limit}"

        # Try cache
        cached_result = await cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache HIT: User posts for user_id={user_id}")
            return cached_result

        # Cache miss - query database
        logger.debug(f"Cache MISS: User posts for user_id={user_id}")
        posts = db.query(Post).filter(Post.user_id == user_id)\
            .order_by(Post.created_at.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()

        # Convert to dict for caching
        result = [
            {
                "id": post.id,
                "article_title": post.article_title,
                "twitter_content": post.twitter_content,
                "linkedin_content": post.linkedin_content,
                "threads_content": post.threads_content,
                "instagram_caption": post.instagram_caption,
                "platforms": post.platforms or [],
                "status": post.status,
                "created_at": post.created_at.isoformat() if post.created_at else None,
                "published_at": post.published_at.isoformat() if post.published_at else None,
            }
            for post in posts
        ]

        # Cache for 1 minute (short TTL for frequently changing data)
        await cache.set(cache_key, result, ttl=RedisConfig.CACHE_TTL_SHORT)
        return result

    @staticmethod
    async def get_single_post(
        db: Session,
        post_id: int,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get single post with caching (5 minutes TTL).

        Cache key: posts:post:{post_id}:user:{user_id}
        """
        cache_key = f"post:{post_id}:user:{user_id}"

        # Try cache
        cached_result = await cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache HIT: Post {post_id}")
            return cached_result

        # Cache miss - query database
        logger.debug(f"Cache MISS: Post {post_id}")
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user_id
        ).first()

        if not post:
            return None

        # Convert to dict
        result = {
            "id": post.id,
            "article_title": post.article_title,
            "twitter_content": post.twitter_content,
            "linkedin_content": post.linkedin_content,
            "threads_content": post.threads_content,
            "instagram_caption": post.instagram_caption,
            "platforms": post.platforms or [],
            "status": post.status,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "published_at": post.published_at.isoformat() if post.published_at else None,
        }

        # Cache for 5 minutes
        await cache.set(cache_key, result, ttl=RedisConfig.CACHE_TTL_MEDIUM)
        return result

    @staticmethod
    async def get_post_status(
        post_id: int,
        status_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cache post generation status (30 seconds TTL).

        Note: Status changes frequently during generation,
        so we use very short TTL.

        Cache key: posts:status:{post_id}
        """
        cache_key = f"status:{post_id}"

        # Try cache
        cached_result = await cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache HIT: Post status {post_id}")
            return cached_result

        # Cache for 30 seconds (very short TTL)
        logger.debug(f"Cache MISS: Post status {post_id}")
        await cache.set(cache_key, status_data, ttl=30)
        return status_data

    @staticmethod
    async def get_user_connections(
        db: Session,
        user_id: int,
        platforms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get user's social media connections with caching (5 minutes TTL).

        Cache key: posts:connections:user:{user_id}:platforms:{platforms}
        """
        platforms_str = ":".join(sorted(platforms)) if platforms else "all"
        cache_key = f"connections:user:{user_id}:platforms:{platforms_str}"

        # Try cache
        cached_result = await cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache HIT: Connections for user_id={user_id}")
            return cached_result

        # Cache miss - query database
        logger.debug(f"Cache MISS: Connections for user_id={user_id}")
        query = db.query(SocialMediaConnection).filter(
            SocialMediaConnection.user_id == user_id
        )

        if platforms:
            query = query.filter(SocialMediaConnection.platform.in_(platforms))

        connections = query.all()

        # Convert to dict
        result = {
            conn.platform: {
                "connected": conn.is_active,
                "username": conn.platform_username,
                "needs_reconnection": not conn.is_active,
            }
            for conn in connections
        }

        # Cache for 5 minutes
        await cache.set(cache_key, result, ttl=RedisConfig.CACHE_TTL_MEDIUM)
        return result

    # =========================================================================
    # CACHE INVALIDATION
    # =========================================================================

    @staticmethod
    async def invalidate_user_posts(user_id: int):
        """
        Invalidate all cached post lists for a user.

        Called when:
        - New post created
        - Post deleted
        - Post status changes (draft → published)
        """
        pattern = f"user:{user_id}:list:*"
        deleted = await cache.delete_pattern(pattern)
        logger.info(f"Invalidated {deleted} cached post list entries for user {user_id}")

    @staticmethod
    async def invalidate_single_post(post_id: int, user_id: int):
        """
        Invalidate cached single post.

        Called when:
        - Post updated
        - Post published
        """
        cache_key = f"post:{post_id}:user:{user_id}"
        await cache.delete(cache_key)
        logger.info(f"Invalidated cached post {post_id}")

    @staticmethod
    async def invalidate_post_status(post_id: int):
        """
        Invalidate cached post generation status.

        Called when:
        - Generation progress updates
        - Generation completes
        """
        cache_key = f"status:{post_id}"
        await cache.delete(cache_key)
        logger.debug(f"Invalidated cached status for post {post_id}")

    @staticmethod
    async def invalidate_post_and_list(post_id: int, user_id: int):
        """
        Invalidate both single post and user's post list.

        Called when:
        - Post updated (PATCH)
        - Post deleted (DELETE)

        This ensures both the detail view and list view are updated.
        """
        await PostsCache.invalidate_single_post(post_id, user_id)
        await PostsCache.invalidate_user_posts(user_id)
        logger.info(f"Invalidated post {post_id} and user {user_id} post list")

    @staticmethod
    async def invalidate_user_connections(user_id: int):
        """
        Invalidate cached user connections.

        Called when:
        - User connects/disconnects social media account
        - OAuth token refreshed
        """
        pattern = f"connections:user:{user_id}:*"
        deleted = await cache.delete_pattern(pattern)
        logger.info(f"Invalidated {deleted} cached connection entries for user {user_id}")


# Create singleton instance
posts_cache = PostsCache()
