"""CSRF token generation and validation"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional


class CSRFProtection:
    """CSRF token management"""

    TOKEN_LENGTH = 32
    TOKEN_EXPIRY = 3600  # 1 hour

    @staticmethod
    def generate_token() -> str:
        """Generate a new CSRF token"""
        return secrets.token_urlsafe(CSRFProtection.TOKEN_LENGTH)

    @staticmethod
    def hash_token(token: str, secret: str) -> str:
        """Hash token with secret for storage"""
        return hashlib.sha256(f"{token}{secret}".encode()).hexdigest()

    @staticmethod
    def validate_token(token: str, stored_hash: str, secret: str) -> bool:
        """Validate CSRF token"""
        expected_hash = CSRFProtection.hash_token(token, secret)
        return secrets.compare_digest(expected_hash, stored_hash)

    @staticmethod
    def create_token_with_timestamp() -> tuple[str, datetime]:
        """Create token with expiry timestamp"""
        token = CSRFProtection.generate_token()
        expires_at = datetime.utcnow() + timedelta(seconds=CSRFProtection.TOKEN_EXPIRY)
        return token, expires_at

    @staticmethod
    def is_token_expired(expires_at: datetime) -> bool:
        """Check if token has expired"""
        return datetime.utcnow() > expires_at
