"""
Setup Guide Database Models

This module provides database models for tracking user progress through
social media setup guides (Twitter, LinkedIn, Instagram, Threads).

Features:
- Setup progress tracking per platform
- Validation history and errors
- Step completion tracking
- Analytics and metrics
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index, Float
from datetime import datetime
from database import Base


class SetupProgress(Base):
    """
    Track user progress through social media setup guides.

    Stores current step, completed steps, errors, and timing metrics
    for each platform setup process.
    """
    __tablename__ = "setup_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Platform information
    platform = Column(String(50), nullable=False, index=True)  # twitter, linkedin, instagram, threads

    # Progress tracking
    status = Column(String(50), default="not_started", nullable=False, index=True)
    # Status values: not_started, in_progress, completed, error, abandoned

    current_step = Column(Integer, default=0, nullable=False)
    total_steps = Column(Integer, nullable=False)  # Total steps for this platform

    # Step completion tracking (JSON array of completed step numbers)
    completed_steps = Column(JSON, default=list, nullable=False)

    # Error tracking
    error_log = Column(Text, nullable=True)  # Last error message
    error_count = Column(Integer, default=0, nullable=False)

    # Validation results (JSON object)
    # {
    #   "credentials_valid": true,
    #   "redirect_uri_valid": true,
    #   "permissions_granted": ["tweet.read", "tweet.write"],
    #   "warnings": ["Redirect URI not in app whitelist"]
    # }
    validation_results = Column(JSON, nullable=True)

    # Connected account info (once completed)
    connected_as = Column(String(255), nullable=True)  # @username or display name
    platform_user_id = Column(String(255), nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Metadata
    setup_metadata = Column(JSON, nullable=True)  # Additional platform-specific data

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Composite unique constraint: one setup process per user per platform
    __table_args__ = (
        Index('idx_user_platform_setup', 'user_id', 'platform', unique=True),
        Index('idx_status_platform', 'status', 'platform'),
    )


class SetupValidation(Base):
    """
    Track credential validation attempts.

    Logs all validation attempts to help users debug configuration issues
    and provide analytics on common setup problems.
    """
    __tablename__ = "setup_validations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    progress_id = Column(Integer, ForeignKey("setup_progress.id", ondelete="CASCADE"), nullable=True, index=True)

    # Platform and validation type
    platform = Column(String(50), nullable=False, index=True)
    validation_type = Column(String(100), nullable=False)  # credentials, redirect_uri, permissions, test_connection

    # Validation results
    is_valid = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)
    warnings = Column(JSON, nullable=True)  # Array of warning messages

    # Request details (for debugging)
    request_data = Column(JSON, nullable=True)  # Sanitized request data (no secrets)
    response_data = Column(JSON, nullable=True)  # API response data

    # Network info
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('idx_platform_validation', 'platform', 'validation_type'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )


class SetupMetrics(Base):
    """
    Aggregate metrics for setup process analytics.

    Tracks completion rates, average time, common errors, and drop-off points
    to help improve the setup experience.
    """
    __tablename__ = "setup_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # Platform and time period
    platform = Column(String(50), nullable=False, index=True)
    metric_date = Column(DateTime, nullable=False, index=True)  # Daily aggregation

    # Completion metrics
    total_started = Column(Integer, default=0, nullable=False)
    total_completed = Column(Integer, default=0, nullable=False)
    total_abandoned = Column(Integer, default=0, nullable=False)
    total_errors = Column(Integer, default=0, nullable=False)

    # Timing metrics (in seconds)
    avg_completion_time = Column(Float, nullable=True)
    median_completion_time = Column(Float, nullable=True)
    min_completion_time = Column(Float, nullable=True)
    max_completion_time = Column(Float, nullable=True)

    # Step-level metrics (JSON object)
    # {
    #   "1": {"completed": 100, "dropped": 10, "avg_time": 45},
    #   "2": {"completed": 90, "dropped": 5, "avg_time": 120},
    #   ...
    # }
    step_metrics = Column(JSON, nullable=True)

    # Common errors (JSON array)
    # [
    #   {"error": "Invalid redirect URI", "count": 25, "step": 2},
    #   {"error": "Credentials rejected", "count": 15, "step": 3}
    # ]
    common_errors = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_platform_date', 'platform', 'metric_date', unique=True),
    )


class PlatformConfiguration(Base):
    """
    Platform configuration reference data.

    Stores the expected configuration for each platform, used by the
    setup guide to provide users with correct values and documentation links.
    """
    __tablename__ = "platform_configurations"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), unique=True, nullable=False, index=True)

    # OAuth configuration
    oauth_version = Column(String(10), nullable=False)  # 1.0a, 2.0
    authorization_url = Column(String(500), nullable=True)
    token_url = Column(String(500), nullable=True)

    # Required configuration
    required_credentials = Column(JSON, nullable=False)
    # ["client_id", "client_secret", "redirect_uri"]

    required_permissions = Column(JSON, nullable=False)
    # ["tweet.read", "tweet.write", "users.read"]

    # Setup steps (JSON array)
    # [
    #   {"step": 1, "title": "Create Developer Account", "description": "...", "url": "..."},
    #   {"step": 2, "title": "Create App", "description": "...", "url": "..."}
    # ]
    setup_steps = Column(JSON, nullable=False)

    # Documentation links
    developer_portal_url = Column(String(500), nullable=True)
    documentation_url = Column(String(500), nullable=True)
    setup_guide_url = Column(String(500), nullable=True)

    # Server configuration status
    is_configured = Column(Boolean, default=False, nullable=False)
    server_redirect_uri = Column(String(500), nullable=True)

    # Validation settings
    validation_enabled = Column(Boolean, default=True, nullable=False)
    test_connection_enabled = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
