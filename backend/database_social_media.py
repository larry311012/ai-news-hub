"""
Social Media Connection Models - Database Extension

This module extends the database schema with models for managing
social media platform connections (LinkedIn, Twitter, Threads).
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index
from datetime import datetime
from database import Base


class SocialMediaConnection(Base):
    """
    Social media platform connection model for OAuth tokens.

    Stores encrypted access tokens, refresh tokens, and metadata for
    LinkedIn, Twitter/X, and Threads platforms.
    """

    __tablename__ = "social_media_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Platform information
    platform = Column(String(50), nullable=False, index=True)  # linkedin, twitter, threads
    platform_user_id = Column(String(255), nullable=True)  # Platform's user ID
    platform_username = Column(String(255), nullable=True)  # @username or handle

    # OAuth tokens (encrypted)
    encrypted_access_token = Column(Text, nullable=False)
    encrypted_refresh_token = Column(Text, nullable=True)  # Some platforms don't use refresh tokens

    # Token metadata
    token_type = Column(String(50), default="Bearer", nullable=False)
    scope = Column(Text, nullable=True)  # OAuth scopes granted
    expires_at = Column(DateTime, nullable=True)  # Token expiration time

    # Platform-specific metadata (JSON)
    platform_metadata = Column(JSON, nullable=True)  # Profile info, additional data

    # Connection status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_used_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)  # Last error if connection failed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Composite unique constraint: one connection per user per platform
    __table_args__ = (Index("idx_user_platform", "user_id", "platform", unique=True),)


class SocialMediaPost(Base):
    """
    Social media post publication tracking.

    Tracks individual platform publications from a generated post,
    including success/failure status and platform-specific URLs.
    """

    __tablename__ = "social_media_posts"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_id = Column(
        Integer,
        ForeignKey("social_media_connections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Platform and content
    platform = Column(String(50), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Actual content posted

    # Publication status
    status = Column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, published, failed
    platform_post_id = Column(String(255), nullable=True)  # Platform's post ID
    platform_url = Column(String(1000), nullable=True)  # URL to the published post

    # Metadata
    error_message = Column(Text, nullable=True)
    post_metadata = Column(JSON, nullable=True)  # Engagement metrics, additional data

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    published_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_social_media_post_platform", "post_id", "platform"),
        Index("idx_user_status", "user_id", "status"),
    )


class SocialMediaRateLimit(Base):
    """
    Rate limit tracking for social media platforms.

    Tracks API rate limits to prevent exceeding platform limits
    and getting connections suspended.
    """

    __tablename__ = "social_media_rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_id = Column(
        Integer,
        ForeignKey("social_media_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Platform and endpoint
    platform = Column(String(50), nullable=False, index=True)
    endpoint = Column(String(255), nullable=False)  # e.g., "post", "upload_media"

    # Rate limit tracking
    requests_made = Column(Integer, default=0, nullable=False)
    limit_max = Column(Integer, nullable=False)  # Max requests allowed
    window_start = Column(DateTime, nullable=False, index=True)
    window_duration_seconds = Column(Integer, nullable=False)  # Window duration

    # Reset time
    resets_at = Column(DateTime, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_connection_endpoint", "connection_id", "endpoint"),
        Index("idx_platform_window", "platform", "window_start"),
    )


class SocialMediaWebhook(Base):
    """
    Webhook events from social media platforms.

    Stores webhook events for tracking post engagement,
    connection status changes, etc.
    """

    __tablename__ = "social_media_webhooks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    connection_id = Column(
        Integer,
        ForeignKey("social_media_connections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Webhook metadata
    platform = Column(String(50), nullable=False, index=True)
    event_type = Column(
        String(100), nullable=False, index=True
    )  # post_engagement, token_revoked, etc.
    event_id = Column(
        String(255), nullable=True, unique=True
    )  # Platform's event ID for deduplication

    # Event payload
    payload = Column(JSON, nullable=False)

    # Processing status
    processed = Column(Boolean, default=False, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (Index("idx_platform_event", "platform", "event_type"),)
