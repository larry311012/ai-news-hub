"""Input sanitization and validation"""
import re
import html
from typing import Optional


class InputSanitizer:
    """Sanitize user inputs to prevent XSS and injection attacks"""

    # Dangerous patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|\#|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bUNION\b.*\bSELECT\b)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]

    @staticmethod
    def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
        """Sanitize a string input"""
        if not value:
            return value

        # Strip whitespace
        sanitized = value.strip()

        # HTML escape
        sanitized = html.escape(sanitized)

        # Enforce max length
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def detect_sql_injection(value: str) -> bool:
        """Detect potential SQL injection attempts"""
        for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def detect_xss(value: str) -> bool:
        """Detect potential XSS attempts"""
        for pattern in InputSanitizer.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        # Remove path separators
        sanitized = filename.replace("/", "").replace("\\", "")
        # Remove dangerous characters
        sanitized = re.sub(r"[^\w\s.-]", "", sanitized)
        return sanitized

    @staticmethod
    def validate_and_sanitize_input(
        value: str,
        field_name: str = "Input",
        max_length: Optional[int] = None,
        check_xss: bool = True,
        check_sql: bool = True,
    ) -> str:
        """
        Comprehensive input validation and sanitization

        Args:
            value: Input value to validate
            field_name: Name of field for error messages
            max_length: Maximum allowed length
            check_xss: Check for XSS attempts
            check_sql: Check for SQL injection attempts

        Returns:
            Sanitized value

        Raises:
            ValueError: If input fails validation
        """
        if not value:
            return value

        # Check for XSS
        if check_xss and InputSanitizer.detect_xss(value):
            raise ValueError(f"{field_name} contains potentially malicious content (XSS detected)")

        # Check for SQL injection
        if check_sql and InputSanitizer.detect_sql_injection(value):
            raise ValueError(
                f"{field_name} contains potentially malicious content (SQL injection detected)"
            )

        # Sanitize
        sanitized = InputSanitizer.sanitize_string(value, max_length)

        return sanitized
