"""
OAuth Platform Credentials - Database Model

This module defines the database schema for storing OAuth platform credentials
(API keys, secrets, etc.) in a centralized, secure manner. This allows admins
to manage OAuth credentials through a UI instead of editing .env files.

Key Features:
- Encrypted storage of all sensitive credentials
- Support for OAuth 1.0a and OAuth 2.0
- Platform-specific configuration (callback URLs, scopes)
- Connection testing and status tracking
- Audit trail of who created/updated credentials
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from datetime import datetime
from database import Base


class OAuthPlatformCredential(Base):
    """
    OAuth platform credentials model.

    Stores encrypted OAuth credentials for social media platforms
    (Twitter, LinkedIn, Threads) that are used for centralized authentication.

    Security:
    - All credentials are encrypted at rest using AES-256 (Fernet)
    - Database credentials take precedence over .env credentials
    - Only admins can view/edit credentials
    - API responses only return masked credentials

    Supported Platforms:
    - twitter (OAuth 1.0a)
    - linkedin (OAuth 2.0)
    - threads (OAuth 2.0)
    """

    __tablename__ = "oauth_platform_credentials"

    id = Column(Integer, primary_key=True, index=True)

    # Platform identification
    platform = Column(
        String(50), nullable=False, unique=True, index=True
    )  # twitter, linkedin, threads
    oauth_version = Column(String(10), nullable=False)  # '1.0a' or '2.0'

    # Encrypted credentials (OAuth 1.0a)
    # For Twitter OAuth 1.0a: API Key (Consumer Key) and API Secret (Consumer Secret)
    encrypted_api_key = Column(Text, nullable=True)  # OAuth 1.0a: Consumer Key / API Key
    encrypted_api_secret = Column(Text, nullable=True)  # OAuth 1.0a: Consumer Secret / API Secret

    # Encrypted credentials (OAuth 2.0)
    # For LinkedIn/Threads OAuth 2.0: Client ID and Client Secret
    encrypted_client_id = Column(Text, nullable=True)  # OAuth 2.0: Client ID
    encrypted_client_secret = Column(Text, nullable=True)  # OAuth 2.0: Client Secret

    # OAuth configuration
    redirect_uri = Column(Text, nullable=True)  # OAuth 2.0 redirect URI
    callback_url = Column(Text, nullable=True)  # OAuth 1.0a callback URL
    scopes = Column(Text, nullable=True)  # JSON array of OAuth scopes (comma-separated)

    # Additional configuration (platform-specific)
    # For example: bearer_token for Twitter API v2, app_id for Threads, etc.
    additional_config = Column(Text, nullable=True)  # JSON object for platform-specific config

    # Connection testing
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_tested_at = Column(DateTime, nullable=True)
    test_status = Column(String(50), nullable=True)  # 'success', 'failed', 'not_tested'
    test_error_message = Column(Text, nullable=True)

    # Audit trail
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin user who created
    updated_by = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Admin user who last updated
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_platform_active", "platform", "is_active"),
        Index("idx_test_status", "test_status"),
    )

    def __repr__(self):
        return f"<OAuthPlatformCredential(platform='{self.platform}', oauth_version='{self.oauth_version}', is_active={self.is_active})>"

    def is_configured(self) -> bool:
        """
        Check if platform credentials are configured.

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
        platform_names = {"twitter": "Twitter (X)", "linkedin": "LinkedIn", "threads": "Threads"}
        return platform_names.get(self.platform, self.platform.title())
