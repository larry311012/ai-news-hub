"""
Centralized Configuration Management

Provides type-safe configuration with environment variable validation.
All configuration should flow through this module for consistency.

Usage:
    from config.settings import settings

    openai_key = settings.OPENAI_API_KEY
    db_url = settings.DATABASE_URL
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict
from typing import Optional, List
import os
from pathlib import Path


class Settings(BaseSettings):
    """
    Application Settings

    All settings are loaded from environment variables.
    Default values are provided for development.
    """

    # ========================================================================
    # ENVIRONMENT
    # ========================================================================
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR")

    # ========================================================================
    # SERVER
    # ========================================================================
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    RELOAD: bool = Field(default=True, description="Enable auto-reload (development only)")

    # ========================================================================
    # DATABASE
    # ========================================================================
    DATABASE_URL: str = Field(
        default="sqlite:///./ai_news.db",
        description="Database connection URL"
    )
    DB_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Connection timeout (seconds)")

    # ========================================================================
    # SECURITY
    # ========================================================================
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT tokens"
    )
    ENCRYPTION_KEY: str = Field(
        default="",
        description="Fernet encryption key for API keys"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    SESSION_EXPIRY_DAYS: int = Field(default=30, description="Session expiry in days")

    # ========================================================================
    # CORS
    # ========================================================================
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080"
        ],
        description="Allowed CORS origins"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow CORS credentials")

    # ========================================================================
    # AI PROVIDERS
    # ========================================================================
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    OPENAI_ORG_ID: Optional[str] = Field(default=None, description="OpenAI organization ID")
    OPENAI_MODEL: str = Field(default="gpt-4", description="OpenAI model to use")
    OPENAI_MAX_TOKENS: int = Field(default=1000, description="Max tokens per request")
    OPENAI_TEMPERATURE: float = Field(default=0.7, description="Generation temperature")

    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    ANTHROPIC_MODEL: str = Field(default="claude-3-sonnet-20240229", description="Anthropic model")

    # ========================================================================
    # IMAGE GENERATION (DALL-E)
    # ========================================================================
    DALLE_API_URL: str = Field(
        default="https://api.openai.com/v1/images/generations",
        description="DALL-E API endpoint"
    )
    DALLE_MODEL: str = Field(default="dall-e-3", description="DALL-E model version")
    DALLE_IMAGE_SIZE: str = Field(default="1024x1024", description="Default image size")
    DALLE_IMAGE_QUALITY: str = Field(default="standard", description="Image quality: standard or hd")
    MAX_IMAGE_GENERATIONS_PER_DAY: int = Field(default=50, description="Daily image generation quota per user")
    IMAGE_CACHE_ENABLED: bool = Field(default=True, description="Enable image prompt caching")

    # ========================================================================
    # STORAGE
    # ========================================================================
    IMAGE_STORAGE_PATH: str = Field(
        default="./static/instagram_images",
        description="Path for storing generated images"
    )
    IMAGE_MAX_SIZE_MB: int = Field(default=8, description="Max image size in MB")
    THUMBNAIL_SIZE: tuple = Field(default=(256, 256), description="Thumbnail dimensions")

    # ========================================================================
    # OAUTH / SOCIAL MEDIA
    # ========================================================================
    # Instagram/Facebook
    INSTAGRAM_APP_ID: Optional[str] = Field(default=None, description="Instagram/Facebook App ID")
    INSTAGRAM_APP_SECRET: Optional[str] = Field(default=None, description="Instagram/Facebook App Secret")
    INSTAGRAM_CALLBACK_URL: str = Field(
        default="http://localhost:8000/api/social-media/instagram/callback",
        description="Instagram OAuth callback URL"
    )

    # Twitter
    TWITTER_API_KEY: Optional[str] = Field(default=None, description="Twitter API key")
    TWITTER_API_SECRET: Optional[str] = Field(default=None, description="Twitter API secret")
    TWITTER_CALLBACK_URL: str = Field(
        default="http://localhost:8000/api/social-media/twitter/callback",
        description="Twitter OAuth callback URL"
    )

    # LinkedIn
    LINKEDIN_CLIENT_ID: Optional[str] = Field(default=None, description="LinkedIn client ID")
    LINKEDIN_CLIENT_SECRET: Optional[str] = Field(default=None, description="LinkedIn client secret")
    LINKEDIN_CALLBACK_URL: str = Field(
        default="http://localhost:8000/api/social-media/linkedin/callback",
        description="LinkedIn OAuth callback URL"
    )

    # Threads
    THREADS_APP_ID: Optional[str] = Field(default=None, description="Threads App ID")
    THREADS_APP_SECRET: Optional[str] = Field(default=None, description="Threads App Secret")
    THREADS_CALLBACK_URL: str = Field(
        default="http://localhost:8000/api/social-media/threads/callback",
        description="Threads OAuth callback URL"
    )

    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, description="Requests per minute per user")
    RATE_LIMIT_BURST: int = Field(default=10, description="Burst allowance")

    # ========================================================================
    # CACHING
    # ========================================================================
    CACHE_ENABLED: bool = Field(default=True, description="Enable caching")
    CACHE_TTL_SECONDS: int = Field(default=300, description="Default cache TTL (5 minutes)")
    CACHE_BACKEND: str = Field(default="memory", description="Cache backend: memory or redis")
    REDIS_URL: Optional[str] = Field(default=None, description="Redis URL for caching")

    # ========================================================================
    # MONITORING & PERFORMANCE
    # ========================================================================
    ENABLE_PROFILING: bool = Field(default=False, description="Enable request profiling")
    ENABLE_METRICS: bool = Field(default=True, description="Enable metrics collection")
    SLOW_QUERY_THRESHOLD_MS: int = Field(default=1000, description="Log queries slower than this")
    MAX_CONCURRENT_GENERATIONS: int = Field(default=10, description="Max concurrent post generations")

    # ========================================================================
    # EMAIL (SendGrid)
    # ========================================================================
    SENDGRID_API_KEY: Optional[str] = Field(default=None, description="SendGrid API key")
    FROM_EMAIL: str = Field(default="noreply@ainews.app", description="From email address")
    FROM_NAME: str = Field(default="AI News Aggregator", description="From name")

    # ========================================================================
    # VALIDATORS (Pydantic V2)
    # ========================================================================

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of: {allowed}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {allowed}")
        return v.upper()

    @field_validator("IMAGE_STORAGE_PATH")
    @classmethod
    def validate_storage_path(cls, v: str) -> str:
        """Ensure storage path is absolute and exists"""
        path = Path(v).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @field_validator("DALLE_IMAGE_SIZE")
    @classmethod
    def validate_image_size(cls, v: str) -> str:
        """Validate DALL-E image size"""
        allowed = ["1024x1024", "1024x1792", "1792x1024"]
        if v not in allowed:
            raise ValueError(f"DALLE_IMAGE_SIZE must be one of: {allowed}")
        return v

    @field_validator("DALLE_IMAGE_QUALITY")
    @classmethod
    def validate_image_quality(cls, v: str) -> str:
        """Validate DALL-E image quality"""
        allowed = ["standard", "hd"]
        if v not in allowed:
            raise ValueError(f"DALLE_IMAGE_QUALITY must be one of: {allowed}")
        return v

    @field_validator("PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number"""
        if not (1 <= v <= 65535):
            raise ValueError("PORT must be between 1 and 65535")
        return v

    # ========================================================================
    # COMPUTED PROPERTIES
    # ========================================================================

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"

    @property
    def dalle_cost_per_image(self) -> float:
        """Calculate DALL-E cost per image"""
        if self.DALLE_IMAGE_QUALITY == "hd":
            return 0.080 if self.DALLE_IMAGE_SIZE == "1024x1024" else 0.120
        else:
            return 0.040 if self.DALLE_IMAGE_SIZE == "1024x1024" else 0.080

    @property
    def database_is_sqlite(self) -> bool:
        """Check if using SQLite"""
        return "sqlite" in self.DATABASE_URL.lower()

    # ========================================================================
    # CONFIG
    # ========================================================================

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Allow extra fields from .env file
    )


# Singleton instance
settings = Settings()


# ========================================================================
# HELPER FUNCTIONS
# ========================================================================

def get_settings() -> Settings:
    """
    Get settings instance (for dependency injection)

    Usage in FastAPI:
        @app.get("/")
        def endpoint(settings: Settings = Depends(get_settings)):
            return {"env": settings.ENVIRONMENT}
    """
    return settings


def validate_production_config() -> List[str]:
    """
    Validate configuration for production deployment

    Returns:
        List of configuration warnings/errors
    """
    warnings = []

    if settings.ENVIRONMENT == "production":
        # Critical checks
        if settings.SECRET_KEY == "dev-secret-key-change-in-production":
            warnings.append("CRITICAL: SECRET_KEY is using default value in production!")

        if not settings.ENCRYPTION_KEY:
            warnings.append("CRITICAL: ENCRYPTION_KEY not set in production!")

        if settings.DEBUG:
            warnings.append("WARNING: DEBUG is enabled in production")

        if not settings.OPENAI_API_KEY and not settings.ANTHROPIC_API_KEY:
            warnings.append("WARNING: No AI provider API keys configured")

        if settings.database_is_sqlite:
            warnings.append("WARNING: Using SQLite in production (consider PostgreSQL)")

        if "*" in settings.CORS_ORIGINS or "http://localhost" in str(settings.CORS_ORIGINS):
            warnings.append("WARNING: CORS allows localhost in production")

    return warnings


# Run validation on import
_production_warnings = validate_production_config()
if _production_warnings and settings.is_production:
    import warnings as py_warnings
    for warning in _production_warnings:
        py_warnings.warn(warning, UserWarning)
