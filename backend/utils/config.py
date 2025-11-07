"""Configuration management and validation"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration with validation"""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ai_news.db")

    # Security - Required
    ENCRYPTION_KEY: Optional[str] = os.getenv("ENCRYPTION_KEY")

    # Session Configuration
    SESSION_EXPIRE_DAYS: int = int(os.getenv("SESSION_EXPIRE_DAYS", "30"))

    # OAuth Configuration (optional for development)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8001/api/auth/oauth/google/callback"
    )

    # Email Configuration
    EMAIL_MODE: str = os.getenv("EMAIL_MODE", "development")  # development|smtp|sendgrid

    # SMTP Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@example.com")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "AI Post Generator")

    # SendGrid Configuration
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")

    # Application
    APP_URL: str = os.getenv("APP_URL", "http://localhost:3000")

    # Security Features
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    SECURITY_MONITORING_ENABLED: bool = (
        os.getenv("SECURITY_MONITORING_ENABLED", "true").lower() == "true"
    )

    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:3001",
        os.getenv("APP_URL", "http://localhost:3000"),
    ]

    @classmethod
    def validate(cls) -> bool:
        """
        Validate configuration settings

        Returns:
            bool: True if valid, raises ValueError otherwise
        """
        errors = []

        # Required settings
        if not cls.ENCRYPTION_KEY:
            errors.append(
                "ENCRYPTION_KEY is required. Generate one with: "
                'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )

        # Validate encryption key format
        if cls.ENCRYPTION_KEY:
            try:
                from cryptography.fernet import Fernet

                Fernet(cls.ENCRYPTION_KEY.encode())
            except Exception as e:
                errors.append(f"Invalid ENCRYPTION_KEY format: {e}")

        # Email configuration validation (only in production mode)
        if cls.EMAIL_MODE == "sendgrid" and not cls.SENDGRID_API_KEY:
            errors.append("SENDGRID_API_KEY required when EMAIL_MODE=sendgrid")

        if cls.EMAIL_MODE == "smtp" and not (cls.SMTP_USERNAME and cls.SMTP_PASSWORD):
            errors.append("SMTP_USERNAME and SMTP_PASSWORD required when EMAIL_MODE=smtp")

        # OAuth validation (warnings only)
        if not cls.GOOGLE_CLIENT_ID or not cls.GOOGLE_CLIENT_SECRET:
            print("WARNING: OAuth not configured. Google login will not work.")
            print("  Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable.")

        # Raise errors if any critical issues found
        if errors:
            error_message = "Configuration validation failed:\n  - " + "\n  - ".join(errors)
            raise ValueError(error_message)

        return True

    @classmethod
    def get_email_config(cls) -> dict:
        """Get email configuration based on mode"""
        if cls.EMAIL_MODE == "sendgrid":
            return {
                "mode": "sendgrid",
                "api_key": cls.SENDGRID_API_KEY,
                "from_email": cls.SMTP_FROM_EMAIL,
                "from_name": cls.SMTP_FROM_NAME,
            }
        elif cls.EMAIL_MODE == "smtp":
            return {
                "mode": "smtp",
                "host": cls.SMTP_HOST,
                "port": cls.SMTP_PORT,
                "username": cls.SMTP_USERNAME,
                "password": cls.SMTP_PASSWORD,
                "from_email": cls.SMTP_FROM_EMAIL,
                "from_name": cls.SMTP_FROM_NAME,
            }
        else:  # development
            return {
                "mode": "development",
                "from_email": cls.SMTP_FROM_EMAIL,
                "from_name": cls.SMTP_FROM_NAME,
            }

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production mode"""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"

    @classmethod
    def print_config(cls) -> None:
        """Print configuration (hiding sensitive values)"""
        print("\n" + "=" * 60)
        print("Configuration:")
        print("=" * 60)
        print(f"Database: {cls.DATABASE_URL}")
        print(f"Encryption Key: {'***SET***' if cls.ENCRYPTION_KEY else 'NOT SET'}")
        print(f"Session Expiry: {cls.SESSION_EXPIRE_DAYS} days")
        print(f"Email Mode: {cls.EMAIL_MODE}")
        print(f"App URL: {cls.APP_URL}")
        print(f"Rate Limiting: {'Enabled' if cls.RATE_LIMIT_ENABLED else 'Disabled'}")
        print(
            f"Security Monitoring: {'Enabled' if cls.SECURITY_MONITORING_ENABLED else 'Disabled'}"
        )
        print(f"OAuth Google: {'Configured' if cls.GOOGLE_CLIENT_ID else 'Not Configured'}")
        print("=" * 60 + "\n")


# Validate configuration on module import (in production only)
# In development, we allow missing optional settings
try:
    Config.validate()
except ValueError as e:
    if Config.is_production():
        raise
    else:
        print(f"\nConfiguration Warning (development mode):\n{e}\n")
