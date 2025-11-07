"""
User OAuth Credentials - Per-User Database Model

This module defines the database schema for storing per-user OAuth credentials.
Unlike the centralized OAuthPlatformCredential, this allows each user to provide
their own Twitter/LinkedIn/Threads API credentials.

Key Features:
- Each user has their own OAuth app credentials
- Encrypted storage of all sensitive credentials (AES-256 Fernet)
- Support for OAuth 1.0a (Twitter) and OAuth 2.0 (LinkedIn, Threads)
- Credential validation and testing
- Audit trail and security logging
- Unique constraint: one credential set per user per platform

Architecture:
- User provides API Key + Secret via UI wizard
- Credentials stored encrypted in database
- When connecting to Twitter, use THEIR credentials (not admin's)
- Tokens are still stored in social_media_connections table
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, UniqueConstraint
from datetime import datetime
from database import Base


class UserOAuthCredential(Base):
    """
    Per-user OAuth credentials model.

    Stores encrypted OAuth credentials that users provide for their own
    Twitter developer apps, LinkedIn apps, or Threads apps.

    Security:
    - All credentials encrypted at rest using AES-256 (Fernet)
    - Never logged or exposed in plaintext
    - Unique constraint prevents duplicate credentials per user/platform
    - Audit trail tracks all credential updates
    - Rate limiting prevents brute force attacks

    Flow:
    1. User creates Twitter developer app (gets API Key + Secret)
    2. User enters credentials via UI wizard
    3. System encrypts and stores credentials
    4. When user clicks "Connect Twitter", system uses THEIR credentials
    5. OAuth tokens stored in social_media_connections table
    """
    __tablename__ = "user_oauth_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Platform identification
    platform = Column(String(50), nullable=False, index=True)  # twitter, linkedin, threads
    oauth_version = Column(String(10), nullable=False)  # '1.0a' or '2.0'

    # Encrypted credentials (OAuth 1.0a) - Twitter
    # User provides API Key (Consumer Key) and API Secret (Consumer Secret)
    encrypted_api_key = Column(Text, nullable=True)  # OAuth 1.0a: API Key / Consumer Key
    encrypted_api_secret = Column(Text, nullable=True)  # OAuth 1.0a: API Secret / Consumer Secret

    # Encrypted credentials (OAuth 2.0) - LinkedIn, Threads
    # User provides Client ID and Client Secret
    encrypted_client_id = Column(Text, nullable=True)  # OAuth 2.0: Client ID
    encrypted_client_secret = Column(Text, nullable=True)  # OAuth 2.0: Client Secret

    # OAuth configuration (user-specific callback URLs)
    callback_url = Column(Text, nullable=True)  # OAuth 1.0a callback URL (Twitter)
    redirect_uri = Column(Text, nullable=True)  # OAuth 2.0 redirect URI (LinkedIn, Threads)
    scopes = Column(Text, nullable=True)  # Comma-separated OAuth scopes for 2.0

    # Credential status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_validated = Column(Boolean, default=False, nullable=False)  # True if credentials tested successfully

    # Validation tracking
    last_validated_at = Column(DateTime, nullable=True)
    validation_status = Column(String(50), nullable=True)  # 'success', 'failed', 'not_tested'
    validation_error = Column(Text, nullable=True)  # Error message if validation failed

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)  # Last time credentials were used for OAuth
    usage_count = Column(Integer, default=0, nullable=False)  # Number of times used

    # Security audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes and constraints
    __table_args__ = (
        # Unique constraint: one credential set per user per platform
        UniqueConstraint('user_id', 'platform', name='uq_user_platform_credentials'),
        Index('idx_user_platform_active', 'user_id', 'platform', 'is_active'),
        Index('idx_validation_status', 'validation_status'),
    )

    def __repr__(self):
        return f"<UserOAuthCredential(user_id={self.user_id}, platform='{self.platform}', oauth_version='{self.oauth_version}')>"

    def is_configured(self) -> bool:
        """
        Check if credentials are fully configured.

        Returns:
            True if required credentials are set, False otherwise
        """
        if self.oauth_version == "1.0a":
            return bool(self.encrypted_api_key and self.encrypted_api_secret)
        elif self.oauth_version == "2.0":
            return bool(self.encrypted_client_id and self.encrypted_client_secret)
        return False

    def get_platform_name(self) -> str:
        """Get human-readable platform name"""
        platform_names = {
            "twitter": "Twitter (X)",
            "linkedin": "LinkedIn",
            "threads": "Threads"
        }
        return platform_names.get(self.platform, self.platform.title())

    def mark_used(self):
        """Mark credentials as used (updates last_used_at and usage_count)"""
        self.last_used_at = datetime.utcnow()
        self.usage_count += 1


class UserOAuthCredentialAudit(Base):
    """
    Audit log for user OAuth credential changes.

    Tracks all create, update, and delete operations for security monitoring.
    Helps detect suspicious activity like credential sharing or brute force attacks.
    """
    __tablename__ = "user_oauth_credential_audits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    credential_id = Column(Integer, ForeignKey("user_oauth_credentials.id", ondelete="SET NULL"), nullable=True, index=True)

    # Audit information
    platform = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)  # create, update, delete, validate, use

    # Additional context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    status = Column(String(50), nullable=True)  # success, failed
    error_message = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('idx_user_action', 'user_id', 'action'),
        Index('idx_platform_action', 'platform', 'action'),
    )

    def __repr__(self):
        return f"<UserOAuthCredentialAudit(user_id={self.user_id}, platform='{self.platform}', action='{self.action}')>"
