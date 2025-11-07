"""
Twitter OAuth 1.0a Database Models

This module defines database models specifically for Twitter OAuth 1.0a flow,
including request token storage and OAuth state management.

Following Twitter's official documentation:
https://developer.twitter.com/en/docs/authentication/oauth-1-0a
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from datetime import datetime, timedelta
from database import Base


class TwitterOAuthRequestToken(Base):
    """
    Temporary storage for Twitter OAuth 1.0a request tokens.

    During the OAuth flow:
    1. We obtain a request token from Twitter
    2. Store it temporarily (with TTL)
    3. User authorizes on Twitter
    4. We exchange request token for access token
    5. Delete this record

    Security:
    - Request tokens expire after 10 minutes
    - One-time use only
    - CSRF protection via state parameter
    - Associated with specific user session
    """
    __tablename__ = "twitter_oauth_request_tokens"

    id = Column(Integer, primary_key=True, index=True)

    # OAuth request token data
    oauth_token = Column(String(255), nullable=False, unique=True, index=True)
    oauth_token_secret = Column(String(255), nullable=False)  # Encrypted

    # CSRF protection
    state = Column(String(64), nullable=False, unique=True, index=True)  # Random state for CSRF

    # User context
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Callback configuration
    return_url = Column(String(1000), nullable=True)  # Frontend URL to redirect after OAuth

    # Expiration
    expires_at = Column(DateTime, nullable=False, index=True)  # 10 minutes from creation
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Status tracking
    used = Column(Boolean, default=False, nullable=False, index=True)  # One-time use

    __table_args__ = (
        Index('idx_token_expiry', 'oauth_token', 'expires_at'),
        Index('idx_state_user', 'state', 'user_id'),
    )

    def is_expired(self) -> bool:
        """Check if request token has expired"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if request token is valid for use"""
        return not self.used and not self.is_expired()

    @classmethod
    def create_token_expiry(cls, minutes: int = 10) -> datetime:
        """Create expiry datetime for request token (default 10 minutes)"""
        return datetime.utcnow() + timedelta(minutes=minutes)


class TwitterOAuthState(Base):
    """
    OAuth state tracking for CSRF protection and flow management.

    Tracks the complete OAuth flow from initiation to completion,
    providing audit trail and security validation.
    """
    __tablename__ = "twitter_oauth_states"

    id = Column(Integer, primary_key=True, index=True)

    # State identifier (CSRF token)
    state = Column(String(64), nullable=False, unique=True, index=True)

    # User context
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Flow tracking
    flow_step = Column(String(50), nullable=False)  # initiated, authorized, completed, failed

    # OAuth tokens
    request_token = Column(String(255), nullable=True)  # Reference to request token
    access_token_obtained = Column(Boolean, default=False, nullable=False)

    # Metadata
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Timestamps
    initiated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    authorized_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_user_flow', 'user_id', 'flow_step'),
        Index('idx_state_expiry', 'state', 'expires_at'),
    )


class TwitterWebhook(Base):
    """
    Twitter webhook events for token revocation and account changes.

    Handles webhook events from Twitter to detect when:
    - User revokes access
    - User changes password
    - Account suspension/deletion
    """
    __tablename__ = "twitter_webhooks"

    id = Column(Integer, primary_key=True, index=True)

    # User context (may be null if webhook arrives before we identify user)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    connection_id = Column(Integer, ForeignKey("social_media_connections.id", ondelete="SET NULL"),
                          nullable=True, index=True)

    # Webhook metadata
    event_type = Column(String(100), nullable=False, index=True)  # revoke, suspend, etc.
    twitter_user_id = Column(String(255), nullable=True, index=True)  # Twitter's user ID

    # Event payload
    payload = Column(Text, nullable=False)  # JSON payload from Twitter

    # Processing
    processed = Column(Boolean, default=False, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    action_taken = Column(String(255), nullable=True)  # What we did in response

    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('idx_event_processed', 'event_type', 'processed'),
        Index('idx_twitter_user', 'twitter_user_id', 'event_type'),
    )


class TwitterRateLimitLog(Base):
    """
    Track Twitter API rate limits to prevent exceeding limits.

    Twitter has strict rate limits. We track usage to ensure we don't
    exceed limits and get our app suspended.

    Rate Limits (per user):
    - Tweet creation: 300 per 3 hours
    - Media upload: 500 per 15 minutes
    - User lookup: 900 per 15 minutes
    """
    __tablename__ = "twitter_rate_limit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # User/Connection
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id = Column(Integer, ForeignKey("social_media_connections.id", ondelete="CASCADE"),
                          nullable=True, index=True)

    # Endpoint tracking
    endpoint = Column(String(255), nullable=False, index=True)  # e.g., "statuses/update"
    method = Column(String(10), nullable=False)  # GET, POST, etc.

    # Rate limit info
    limit_max = Column(Integer, nullable=False)  # Max requests allowed
    limit_remaining = Column(Integer, nullable=False)  # Requests remaining
    limit_reset_at = Column(DateTime, nullable=False, index=True)  # When limit resets

    # Request details
    success = Column(Boolean, default=True, nullable=False)
    response_code = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('idx_user_endpoint', 'user_id', 'endpoint'),
        Index('idx_reset_time', 'limit_reset_at', 'endpoint'),
    )


class TwitterOAuthAudit(Base):
    """
    Audit log for Twitter OAuth operations.

    Tracks all OAuth-related operations for security auditing and debugging.
    """
    __tablename__ = "twitter_oauth_audit"

    id = Column(Integer, primary_key=True, index=True)

    # User context
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Operation details
    operation = Column(String(100), nullable=False, index=True)  # connect, refresh, disconnect, etc.
    success = Column(Boolean, default=True, nullable=False, index=True)

    # OAuth details
    oauth_version = Column(String(10), default="1.0a", nullable=False)
    state = Column(String(64), nullable=True)  # CSRF state if applicable

    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Results
    error_message = Column(Text, nullable=True)
    extra_data = Column(Text, nullable=True)  # JSON with additional context (renamed from metadata)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('idx_user_operation', 'user_id', 'operation'),
        Index('idx_operation_success', 'operation', 'success'),
    )
