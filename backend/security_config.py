"""Centralized security configuration"""
from typing import Dict, List
import os


class SecurityConfig:
    """Security settings and policies"""

    # Password Policy
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    PASSWORD_CHECK_BREACHES = True
    PASSWORD_MIN_STRENGTH_SCORE = 3  # 0-4 scale

    # Session Security
    SESSION_TIMEOUT_MINUTES = 30
    SESSION_ABSOLUTE_TIMEOUT_HOURS = 24
    SESSION_REQUIRE_FINGERPRINT = True
    SESSION_RENEW_ON_ACTIVITY = True

    # Rate Limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_STORAGE = "database"  # or "redis"
    RATE_LIMIT_BY_IP = True
    RATE_LIMIT_BY_USER = True

    # Account Security
    ACCOUNT_LOCKOUT_ENABLED = True
    ACCOUNT_LOCKOUT_THRESHOLD = 5
    ACCOUNT_LOCKOUT_DURATION_MINUTES = 30

    # Audit Logging
    AUDIT_LOG_ALL_EVENTS = True
    AUDIT_LOG_RETENTION_DAYS = 90
    AUDIT_LOG_SENSITIVE_DATA = False

    # CSRF Protection
    CSRF_ENABLED = True
    CSRF_TOKEN_LENGTH = 32
    CSRF_TOKEN_EXPIRY_MINUTES = 60

    # Security Headers
    SECURITY_HEADERS_ENABLED = True
    HSTS_MAX_AGE_SECONDS = 31536000
    CSP_ENABLED = True

    # Input Validation
    SANITIZE_ALL_INPUTS = True
    MAX_INPUT_LENGTH = 10000
    DETECT_SQL_INJECTION = True
    DETECT_XSS = True

    # OAuth Security
    OAUTH_STATE_TIMEOUT_MINUTES = 10
    OAUTH_REQUIRE_EMAIL_VERIFICATION = True

    # API Security
    API_KEY_ROTATION_DAYS = 90
    API_KEY_ENCRYPTION = "AES-256"

    # Advanced Security Features
    ENABLE_SESSION_FINGERPRINTING = True
    ENABLE_ACCOUNT_LOCKOUT = True
    ENABLE_BREACH_CHECKING = True
    ENABLE_ADVANCED_AUDIT = True

    @classmethod
    def get_all_settings(cls) -> Dict:
        """Get all security settings as dict"""
        return {key: getattr(cls, key) for key in dir(cls) if key.isupper()}

    @classmethod
    def validate_config(cls) -> List[str]:
        """Validate security configuration"""
        warnings = []

        if not cls.RATE_LIMIT_ENABLED:
            warnings.append("Rate limiting is disabled")

        if not cls.ACCOUNT_LOCKOUT_ENABLED:
            warnings.append("Account lockout is disabled")

        if not cls.CSRF_ENABLED:
            warnings.append("CSRF protection is disabled")

        if not cls.SECURITY_HEADERS_ENABLED:
            warnings.append("Security headers are disabled")

        if cls.PASSWORD_MIN_LENGTH < 8:
            warnings.append("Password minimum length is below recommended (8)")

        if not cls.PASSWORD_CHECK_BREACHES:
            warnings.append("Password breach checking is disabled")

        if not cls.ENABLE_SESSION_FINGERPRINTING:
            warnings.append("Session fingerprinting is disabled")

        return warnings

    @classmethod
    def get_security_score(cls) -> tuple[int, str]:
        """
        Calculate overall security score

        Returns:
            (score, grade)
        """
        score = 0
        max_score = 100

        # Password policy (20 points)
        if cls.PASSWORD_MIN_LENGTH >= 8:
            score += 5
        if cls.PASSWORD_REQUIRE_UPPERCASE and cls.PASSWORD_REQUIRE_LOWERCASE:
            score += 5
        if cls.PASSWORD_REQUIRE_DIGIT and cls.PASSWORD_REQUIRE_SPECIAL:
            score += 5
        if cls.PASSWORD_CHECK_BREACHES:
            score += 5

        # Session security (15 points)
        if cls.SESSION_REQUIRE_FINGERPRINT:
            score += 5
        if cls.SESSION_TIMEOUT_MINUTES <= 30:
            score += 5
        if cls.SESSION_RENEW_ON_ACTIVITY:
            score += 5

        # Rate limiting (15 points)
        if cls.RATE_LIMIT_ENABLED:
            score += 10
        if cls.RATE_LIMIT_BY_IP and cls.RATE_LIMIT_BY_USER:
            score += 5

        # Account security (15 points)
        if cls.ACCOUNT_LOCKOUT_ENABLED:
            score += 10
        if cls.ACCOUNT_LOCKOUT_THRESHOLD <= 5:
            score += 5

        # Security headers (10 points)
        if cls.SECURITY_HEADERS_ENABLED:
            score += 5
        if cls.CSP_ENABLED:
            score += 5

        # CSRF protection (10 points)
        if cls.CSRF_ENABLED:
            score += 10

        # Input validation (10 points)
        if cls.SANITIZE_ALL_INPUTS:
            score += 5
        if cls.DETECT_SQL_INJECTION and cls.DETECT_XSS:
            score += 5

        # Audit logging (5 points)
        if cls.AUDIT_LOG_ALL_EVENTS:
            score += 5

        # Advanced features (bonus points, can exceed 100)
        if cls.ENABLE_SESSION_FINGERPRINTING:
            score += 3
        if cls.ENABLE_BREACH_CHECKING:
            score += 3
        if cls.ENABLE_ADVANCED_AUDIT:
            score += 2

        # Determine grade
        if score >= 95:
            grade = "A+"
        elif score >= 90:
            grade = "A"
        elif score >= 85:
            grade = "A-"
        elif score >= 80:
            grade = "B+"
        elif score >= 75:
            grade = "B"
        elif score >= 70:
            grade = "B-"
        elif score >= 65:
            grade = "C+"
        elif score >= 60:
            grade = "C"
        else:
            grade = "D"

        return min(score, 100), grade
