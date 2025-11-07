"""
Publishing History Database Models (Phase 4 - Task 4.3)

Database models for tracking social media publishing status, history, and errors.
Supports multi-platform publishing with retry mechanism and error categorization.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index, Enum
from datetime import datetime
from database import Base
import enum


class PublishingStatus(str, enum.Enum):
    """Publishing status states"""
    PENDING = "pending"
    PUBLISHING = "publishing"
    SUCCESS = "success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    RETRYING = "retrying"


class ErrorCategory(str, enum.Enum):
    """Error categorization for troubleshooting"""
    AUTH_ERROR = "auth_error"  # Token expired, invalid credentials
    VALIDATION_ERROR = "validation_error"  # Content too long, invalid format
    RATE_LIMIT_ERROR = "rate_limit_error"  # API rate limit exceeded
    NETWORK_ERROR = "network_error"  # Connection timeout, DNS failure
    PLATFORM_ERROR = "platform_error"  # Platform-specific errors
    UNKNOWN_ERROR = "unknown_error"  # Uncategorized errors


class PostPublishingHistory(Base):
    """
    Track publishing attempts for each post to each platform.

    Stores detailed information about publishing attempts including:
    - Success/failure status
    - Platform-specific post IDs and URLs
    - Error messages and categorization
    - Retry attempts
    - Publishing metadata
    """

    __tablename__ = "post_publishing_history"

    id = Column(Integer, primary_key=True, index=True)

    # Post and user references
    post_id = Column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Platform information
    platform = Column(String(50), nullable=False, index=True)  # twitter, linkedin, instagram, threads

    # Publishing status
    status = Column(
        String(50),
        default=PublishingStatus.PENDING,
        nullable=False,
        index=True
    )

    # Platform response
    platform_post_id = Column(String(255), nullable=True, index=True)  # Platform's post ID
    platform_url = Column(String(1000), nullable=True)  # URL to published post

    # Error tracking
    error_category = Column(String(50), nullable=True, index=True)  # ErrorCategory enum
    error_message = Column(Text, nullable=True)  # Human-readable error
    error_details = Column(JSON, nullable=True)  # Structured error data

    # Retry mechanism
    retry_count = Column(Integer, default=0, nullable=False)  # Number of retry attempts
    max_retries = Column(Integer, default=3, nullable=False)  # Maximum retry attempts
    next_retry_at = Column(DateTime, nullable=True, index=True)  # When to retry

    # Content metadata
    content = Column(Text, nullable=True)  # Content that was published/attempted
    content_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hash for deduplication
    media_urls = Column(JSON, nullable=True)  # List of media URLs

    # Publishing metadata
    publishing_metadata = Column(JSON, nullable=True)  # Platform-specific metadata

    # Rate limiting
    rate_limit_reset_at = Column(DateTime, nullable=True, index=True)  # When rate limit resets

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)  # When publishing started
    published_at = Column(DateTime, nullable=True, index=True)  # When successfully published
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_user_platform_status", "user_id", "platform", "status"),
        Index("idx_post_platform", "post_id", "platform", unique=True),  # One record per post per platform
        Index("idx_retry_queue", "status", "next_retry_at"),  # For retry queue
        Index("idx_rate_limit_recovery", "status", "rate_limit_reset_at"),  # For rate limit recovery
    )


class PublishingQueue(Base):
    """
    Queue for batch publishing and background tasks.

    Allows scheduling multiple posts for publishing across multiple platforms.
    Supports delayed publishing and background task execution.
    """

    __tablename__ = "publishing_queue"

    id = Column(Integer, primary_key=True, index=True)

    # User and post references
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    post_id = Column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Publishing configuration
    platforms = Column(JSON, nullable=False)  # List of platforms to publish to
    scheduled_at = Column(DateTime, nullable=True, index=True)  # When to publish (null = immediate)

    # Status
    status = Column(
        String(50),
        default="queued",
        nullable=False,
        index=True
    )  # queued, processing, completed, failed

    # Priority (lower number = higher priority)
    priority = Column(Integer, default=5, nullable=False, index=True)

    # Processing metadata
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Publishing results
    results = Column(JSON, nullable=True)  # Results per platform

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_queue_processing", "status", "scheduled_at", "priority"),
        Index("idx_user_queue", "user_id", "status"),
    )


class PublishingRateLimit(Base):
    """
    Track API rate limits per user per platform.

    Prevents exceeding platform rate limits by tracking usage and enforcing limits.
    Supports both per-user and global rate limiting.
    """

    __tablename__ = "publishing_rate_limits"

    id = Column(Integer, primary_key=True, index=True)

    # User reference (null = global limit)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Platform and endpoint
    platform = Column(String(50), nullable=False, index=True)
    endpoint = Column(String(100), default="publish", nullable=False)

    # Rate limit configuration
    limit_max = Column(Integer, nullable=False)  # Max requests allowed
    window_seconds = Column(Integer, nullable=False)  # Time window in seconds

    # Current usage
    requests_made = Column(Integer, default=0, nullable=False)
    window_start = Column(DateTime, nullable=False, index=True)
    window_end = Column(DateTime, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_user_platform_endpoint", "user_id", "platform", "endpoint", unique=True),
        Index("idx_window_check", "platform", "window_end"),
    )


class PublishingWebhook(Base):
    """
    Store webhook events from social media platforms.

    Captures async publishing results and platform notifications.
    Used for platforms that return immediate response but publish asynchronously.
    """

    __tablename__ = "publishing_webhooks"

    id = Column(Integer, primary_key=True, index=True)

    # References
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    publishing_history_id = Column(
        Integer,
        ForeignKey("post_publishing_history.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Webhook metadata
    platform = Column(String(50), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)  # post_published, post_failed, etc.
    event_id = Column(String(255), nullable=True, unique=True, index=True)  # Platform's event ID

    # Event payload
    payload = Column(JSON, nullable=False)

    # Processing status
    processed = Column(Boolean, default=False, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)

    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Indexes
    __table_args__ = (
        Index("idx_platform_event_type", "platform", "event_type"),
        Index("idx_processing_queue", "processed", "received_at"),
    )
