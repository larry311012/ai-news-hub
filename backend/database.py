"""
Database configuration and models
"""
from typing import Generator, Union, Type
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    JSON,
    ForeignKey,
    Index,
    Float,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import QueuePool, NullPool, Pool
from datetime import datetime, timedelta
import os
import time
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Database URL - PostgreSQL with fallback to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_news.db")

# Connection arguments based on database type
connect_args: dict = {}
poolclass: Type[Pool] = QueuePool

if "sqlite" in DATABASE_URL:
    # SQLite-specific configuration
    connect_args = {"check_same_thread": False}
    poolclass = NullPool  # SQLite doesn't support connection pooling well
    engine = create_engine(DATABASE_URL, connect_args=connect_args, poolclass=poolclass)
elif "postgresql" in DATABASE_URL:
    # PostgreSQL-specific configuration with connection pooling
    # Production-grade settings for scalability
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,  # Number of connections to keep open
        max_overflow=20,  # Additional connections when pool is exhausted
        pool_pre_ping=True,  # Verify connections before using them
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False,  # Set to True for SQL query logging (debug only)
        future=True,  # Enable SQLAlchemy 2.0 features
    )
else:
    # Generic database configuration
    engine = create_engine(DATABASE_URL)


# ============================================================================
# QUERY PERFORMANCE MONITORING
# ============================================================================

# Query performance tracking
if os.getenv("SQL_DEBUG", "false").lower() == "true":
    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault('query_start_time', []).append(time.time())
        logger.debug(f"Start Query: {statement[:200]}")

    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total = time.time() - conn.info['query_start_time'].pop(-1)
        logger.info(f"Query Complete in {total:.3f}s")

        # Warn on slow queries (>100ms threshold)
        if total > 0.1:
            logger.warning(f"SLOW QUERY ({total:.3f}s): {statement[:200]}")


# Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class
Base: DeclarativeMeta = declarative_base()


# Models
class User(Base):  # type: ignore[misc, valid-type]
    """User model for authentication"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Phase 3: Nullable for OAuth users
    full_name = Column(String(255), nullable=False)
    bio = Column(Text, nullable=True)  # Phase 2: User bio/description
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Phase 3: OAuth fields
    oauth_provider = Column(String(50), nullable=True, index=True)  # google, github, etc.
    oauth_id = Column(String(255), nullable=True, index=True)  # Provider's user ID
    oauth_profile_picture = Column(String(500), nullable=True)  # URL from OAuth

    # Phase 3: Email verification fields
    verification_token = Column(String(64), nullable=True, unique=True, index=True)
    verification_token_expires = Column(DateTime, nullable=True)

    # Phase 3: Guest mode
    is_guest = Column(Boolean, default=False, nullable=False, index=True)

    # Phase 4: Password reset fields
    reset_token = Column(String(64), nullable=True, unique=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)  # Track last password change

    # Admin privileges
    is_admin = Column(Boolean, default=False, nullable=False, index=True)

    # USER TIER SYSTEM: Freemium model
    user_tier = Column(String(20), default="free", nullable=False, index=True)  # guest, free, paid
    daily_quota_used = Column(Integer, default=0, nullable=False)  # Posts generated today
    quota_reset_date = Column(DateTime, nullable=True)  # When quota resets (daily at midnight UTC)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    articles = relationship("Article", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("UserApiKey", back_populates="user", cascade="all, delete-orphan")
    security_settings = relationship(
        "UserSecuritySettings", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    login_activities = relationship(
        "LoginActivity", back_populates="user", cascade="all, delete-orphan"
    )
    security_audits = relationship(
        "SecurityAudit", back_populates="user", cascade="all, delete-orphan"
    )
    ab_assignments = relationship(
        "ABAssignment", back_populates="user", cascade="all, delete-orphan"
    )
    # Instagram feature relationships
    instagram_images = relationship(
        "InstagramImage", back_populates="user", cascade="all, delete-orphan"
    )
    image_generation_quota = relationship(
        "ImageGenerationQuota", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    # User-specific settings relationship
    settings = relationship("Settings", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):  # type: ignore[misc, valid-type]
    """User session model for token-based authentication"""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Phase 4: Session activity tracking
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Security Hardening: Session fingerprinting
    session_fingerprint = Column(String(64), nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")


class UserApiKey(Base):  # type: ignore[misc, valid-type]
    """User API key model for storing encrypted API keys"""

    __tablename__ = "user_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider = Column(String(50), nullable=False, index=True)  # openai, anthropic, deepseek, twitter, etc.
    encrypted_key = Column(Text, nullable=False)  # AES-256 encrypted API key
    name = Column(String(255), nullable=True)  # Optional friendly name for the key
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # Added for optimization
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    # Composite index for fast active key lookups
    __table_args__ = (
        Index("idx_user_api_keys_user_provider_active", "user_id", "provider", "is_active"),
    )


class AdminSettings(Base):  # type: ignore[misc, valid-type]
    """Admin settings for system-wide configuration"""

    __tablename__ = "admin_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=False)
    encrypted = Column(Boolean, default=False, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class UserSecuritySettings(Base):  # type: ignore[misc, valid-type]
    """Phase 4: User security preferences and settings"""

    __tablename__ = "user_security_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Email notification preferences
    notify_new_login = Column(Boolean, default=True, nullable=False)
    notify_password_change = Column(Boolean, default=True, nullable=False)
    notify_api_key_change = Column(Boolean, default=True, nullable=False)

    # Session timeout preference
    session_timeout_days = Column(Integer, default=30, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="security_settings")


class LoginActivity(Base):  # type: ignore[misc, valid-type]
    """Phase 4: Track login and security-related activities"""

    __tablename__ = "login_activity"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action = Column(String(50), nullable=False, index=True)  # login, logout, password_change, etc.
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    details = Column(JSON, nullable=True)  # Additional context
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="login_activities")


class SecurityAudit(Base):  # type: ignore[misc, valid-type]
    """Phase 4: Security audit log for tracking security events"""

    __tablename__ = "security_audit"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    details = Column(JSON, nullable=True)
    risk_level = Column(String(20), default="low", nullable=False, index=True)  # low, medium, high
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="security_audits")


class RateLimitLog(Base):  # type: ignore[misc, valid-type]
    """Phase 4: Rate limiting tracking"""

    __tablename__ = "rate_limit_log"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(255), nullable=False, index=True)  # IP address or user_id
    endpoint = Column(String(255), nullable=False, index=True)
    attempt_count = Column(Integer, default=1, nullable=False)
    window_start = Column(DateTime, nullable=False, index=True)
    blocked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Article(Base):  # type: ignore[misc, valid-type]
    """Article model"""

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    link = Column(String(1000), unique=True, nullable=False)
    summary = Column(Text)
    content = Column(Text)
    source = Column(String(200))
    category = Column(String(100))
    published = Column(DateTime, default=datetime.utcnow)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    bookmarked = Column(Boolean, default=False)
    tags = Column(JSON)
    image_url = Column(String(1000))

    # Phase 1: Add user_id (nullable for backward compatibility)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="articles")


class Post(Base):  # type: ignore[misc, valid-type]
    """Social media post model"""

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, nullable=True)
    article_title = Column(String(500))

    # Content for each platform
    twitter_content = Column(Text)
    linkedin_content = Column(Text)
    threads_content = Column(Text)

    # Instagram support (Day 1-2 Feature)
    instagram_caption = Column(Text, nullable=True)
    instagram_image_url = Column(Text, nullable=True)
    instagram_image_prompt = Column(Text, nullable=True)
    instagram_hashtags = Column(Text, nullable=True)  # JSON array as string
    instagram_url = Column(String(500), nullable=True)
    instagram_post_id = Column(String(255), nullable=True)

    # Publishing status
    platforms = Column(JSON)  # List of platforms to publish to
    status = Column(String(50), default="draft", index=True)  # draft, published, failed, processing

    # Publishing results
    twitter_url = Column(String(500))
    linkedin_url = Column(String(500))
    threads_url = Column(String(500))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    published_at = Column(DateTime, nullable=True)

    # Metadata
    ai_summary = Column(Text)
    error_message = Column(Text, nullable=True)  # Legacy: Simple error message
    error_details = Column(JSON, nullable=True)  # NEW: Structured error information

    # Phase 1: Add user_id (nullable for backward compatibility)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="posts")


# Instagram Feature Models (Day 1-2 Implementation)
class InstagramImage(Base):  # type: ignore[misc, valid-type]
    """Instagram Image Generation Tracking"""

    __tablename__ = "instagram_images"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(
        Integer, ForeignKey("posts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    article_id = Column(
        Integer, ForeignKey("articles.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Image metadata
    prompt = Column(Text, nullable=False)
    prompt_hash = Column(String(64), index=True)
    image_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text, nullable=True)
    width = Column(Integer)
    height = Column(Integer)
    format = Column(String(10))
    file_size_bytes = Column(Integer)

    # AI generation metadata
    ai_provider = Column(String(50), default="openai")
    ai_model = Column(String(100), default="dall-e-3")
    generation_params = Column(Text)
    revised_prompt = Column(Text)

    # Cache and reuse tracking
    times_used = Column(Integer, default=1)
    last_used_at = Column(DateTime)

    # Status tracking
    status = Column(String(50), default="active")
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="instagram_images")
    post = relationship("Post")
    article = relationship("Article")


class ImageGenerationQuota(Base):  # type: ignore[misc, valid-type]
    """User Image Generation Quota Tracking"""

    __tablename__ = "image_generation_quota"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # Daily quota
    daily_limit = Column(Integer, default=50)
    images_generated_today = Column(Integer, default=0)
    quota_reset_date = Column(DateTime, nullable=False)

    # Lifetime stats
    total_images_generated = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="image_generation_quota")


class Settings(Base):  # type: ignore[misc, valid-type]
    """User-specific settings model"""

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )  # Nullable for global settings
    key = Column(String(100), nullable=False, index=True)
    value = Column(Text, nullable=False)
    encrypted = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="settings")

    # Composite unique constraint (enforced in PostgreSQL, handled in application for SQLite)
    __table_args__ = (
        Index("idx_settings_user_key", "user_id", "key"),
    )


# A/B Testing Models
class ABExperiment(Base):  # type: ignore[misc, valid-type]
    """A/B Experiment definitions"""

    __tablename__ = "ab_experiments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    variants = Column(JSON, nullable=False)  # ["A", "B", "C"]
    traffic_allocation = Column(JSON, nullable=True)  # {"A": 0.33, "B": 0.33, "C": 0.34}
    start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    assignments = relationship(
        "ABAssignment", back_populates="experiment", cascade="all, delete-orphan"
    )
    conversions = relationship(
        "ABConversion", back_populates="experiment", cascade="all, delete-orphan"
    )


class ABAssignment(Base):  # type: ignore[misc, valid-type]
    """User/Session variant assignments"""

    __tablename__ = "ab_assignments"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(
        Integer, ForeignKey("ab_experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id = Column(String(64), nullable=True, index=True)  # For guests
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    variant = Column(String(10), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    experiment = relationship("ABExperiment", back_populates="assignments")
    user = relationship("User", back_populates="ab_assignments")
    conversions = relationship(
        "ABConversion", back_populates="assignment", cascade="all, delete-orphan"
    )

    # Composite unique constraints
    __table_args__ = (
        Index("idx_experiment_session", "experiment_id", "session_id", unique=True),
        Index("idx_experiment_user", "experiment_id", "user_id", unique=True),
    )


class ABConversion(Base):  # type: ignore[misc, valid-type]
    """Conversion event tracking"""

    __tablename__ = "ab_conversions"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(
        Integer, ForeignKey("ab_experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignment_id = Column(
        Integer, ForeignKey("ab_assignments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_name = Column(String(100), nullable=False, index=True)
    properties = Column(JSON, nullable=True)  # Additional event data
    converted_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    experiment = relationship("ABExperiment", back_populates="conversions")
    assignment = relationship("ABAssignment", back_populates="conversions")


def init_db() -> None:
    """Initialize database"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
