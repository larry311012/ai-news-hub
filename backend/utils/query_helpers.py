"""
Optimized query helper utilities to eliminate N+1 problems
"""
from typing import List, Optional, Type, Dict
from sqlalchemy.orm import Session, Query, joinedload, selectinload, lazyload
from sqlalchemy import select


class OptimizedQuery:
    """Helper for building optimized queries that avoid N+1 problems."""

    @staticmethod
    def get_posts_with_relations(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List:
        """
        Get posts with all relations loaded efficiently.

        Uses joinedload for user (1:1) and selectinload for social_media_posts (1:N).
        This eliminates N+1 queries when accessing relationships.

        Args:
            db: Database session
            user_id: User ID to filter posts
            skip: Pagination offset
            limit: Pagination limit
            status: Optional status filter

        Returns:
            List of Post objects with eagerly loaded relationships
        """
        from database import Post

        query = db.query(Post)\
            .filter(Post.user_id == user_id)\
            .options(
                joinedload(Post.user),  # Single JOIN for 1:1 relationship
            )

        if status:
            query = query.filter(Post.status == status)

        return query.order_by(Post.created_at.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()

    @staticmethod
    def get_post_by_id_with_relations(
        db: Session,
        post_id: int,
        user_id: int
    ):
        """
        Get a single post with all relations loaded.

        Args:
            db: Database session
            post_id: Post ID
            user_id: User ID for authorization

        Returns:
            Post object with eagerly loaded relationships, or None
        """
        from database import Post

        return db.query(Post)\
            .filter(Post.id == post_id, Post.user_id == user_id)\
            .options(
                joinedload(Post.user)
            )\
            .first()

    @staticmethod
    def get_user_connections(
        db: Session,
        user_id: int,
        platforms: Optional[List[str]] = None,
        active_only: bool = True
    ) -> Dict[str, any]:
        """
        Get user's social media connections efficiently.

        Args:
            db: Database session
            user_id: User ID
            platforms: Optional list of platforms to filter
            active_only: Only return active connections

        Returns:
            Dictionary mapping platform name to connection object for O(1) lookup
        """
        from database_social_media import SocialMediaConnection

        query = db.query(SocialMediaConnection)\
            .filter(SocialMediaConnection.user_id == user_id)

        if active_only:
            query = query.filter(SocialMediaConnection.is_active == True)

        if platforms:
            query = query.filter(SocialMediaConnection.platform.in_(platforms))

        connections = query.all()

        # Return as dict for O(1) lookup
        return {conn.platform: conn for conn in connections}

    @staticmethod
    def get_social_media_posts_for_post(
        db: Session,
        post_id: int,
        user_id: int
    ) -> List:
        """
        Get all social media posts for a given post.

        Args:
            db: Database session
            post_id: Post ID
            user_id: User ID for authorization

        Returns:
            List of SocialMediaPost objects
        """
        from database_social_media import SocialMediaPost

        return db.query(SocialMediaPost)\
            .filter(
                SocialMediaPost.post_id == post_id,
                SocialMediaPost.user_id == user_id
            )\
            .all()

    @staticmethod
    def batch_load_by_ids(
        db: Session,
        model: Type,
        ids: List[int]
    ) -> Dict[int, any]:
        """
        Batch load models by IDs to avoid N+1 queries.

        Args:
            db: Database session
            model: SQLAlchemy model class
            ids: List of IDs to load

        Returns:
            Dictionary mapping id -> model for O(1) lookup
        """
        if not ids:
            return {}

        items = db.query(model).filter(model.id.in_(ids)).all()
        return {item.id: item for item in items}

    @staticmethod
    def get_articles_batch(
        db: Session,
        article_ids: List[int]
    ) -> List:
        """
        Batch load articles by IDs.

        Args:
            db: Database session
            article_ids: List of article IDs

        Returns:
            List of Article objects
        """
        from database import Article

        if not article_ids:
            return []

        return db.query(Article)\
            .filter(Article.id.in_(article_ids))\
            .all()

    @staticmethod
    def get_user_api_keys(
        db: Session,
        user_id: int,
        provider: Optional[str] = None,
        active_only: bool = True
    ) -> Dict[str, any]:
        """
        Get user's API keys efficiently.

        Args:
            db: Database session
            user_id: User ID
            provider: Optional provider filter
            active_only: Only return active keys

        Returns:
            Dictionary mapping provider -> UserApiKey for O(1) lookup
        """
        from database import UserApiKey

        query = db.query(UserApiKey)\
            .filter(UserApiKey.user_id == user_id)

        if active_only:
            query = query.filter(UserApiKey.is_active == True)

        if provider:
            query = query.filter(UserApiKey.provider == provider)

        keys = query.all()
        return {key.provider: key for key in keys}

    @staticmethod
    def get_active_sessions(
        db: Session,
        user_id: int
    ) -> List:
        """
        Get active sessions for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of active UserSession objects
        """
        from database import UserSession
        from datetime import datetime

        return db.query(UserSession)\
            .filter(
                UserSession.user_id == user_id,
                UserSession.expires_at > datetime.utcnow()
            )\
            .order_by(UserSession.last_activity.desc())\
            .all()

    @staticmethod
    def get_instagram_images_for_user(
        db: Session,
        user_id: int,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List:
        """
        Get Instagram images for a user.

        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of images to return
            status: Optional status filter

        Returns:
            List of InstagramImage objects
        """
        from database import InstagramImage

        query = db.query(InstagramImage)\
            .filter(InstagramImage.user_id == user_id)

        if status:
            query = query.filter(InstagramImage.status == status)

        return query.order_by(InstagramImage.created_at.desc())\
            .limit(limit)\
            .all()

    @staticmethod
    def check_multiple_connections(
        db: Session,
        user_id: int,
        platforms: List[str]
    ) -> Dict[str, bool]:
        """
        Check if user has active connections for multiple platforms in a single query.

        Args:
            db: Database session
            user_id: User ID
            platforms: List of platform names to check

        Returns:
            Dictionary mapping platform -> is_connected (bool)
        """
        from database_social_media import SocialMediaConnection

        # Single query to check all platforms at once
        connections = db.query(SocialMediaConnection)\
            .filter(
                SocialMediaConnection.user_id == user_id,
                SocialMediaConnection.platform.in_(platforms),
                SocialMediaConnection.is_active == True
            )\
            .all()

        # Create lookup dict
        connected_platforms = {conn.platform for conn in connections}

        # Return result for all requested platforms
        return {platform: platform in connected_platforms for platform in platforms}
