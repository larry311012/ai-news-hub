"""
Input Sanitization Utilities
Prevents XSS and injection attacks using bleach for HTML sanitization
"""
import bleach
import re
from typing import Optional

# Allowed HTML tags for content that supports formatting (like LinkedIn posts)
ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li']
ALLOWED_ATTRIBUTES = {'a': ['href', 'title']}


def sanitize_html(text: str) -> str:
    """
    Remove dangerous HTML tags while keeping safe formatting.

    Used for content like LinkedIn posts that support rich text.

    Args:
        text: HTML content to sanitize

    Returns:
        Sanitized HTML with only safe tags allowed
    """
    if not text:
        return ""
    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )


def sanitize_plain_text(text: str) -> str:
    """
    Strip all HTML tags for plain text fields.

    Used for Twitter, Threads, Instagram captions where HTML is not allowed.

    Args:
        text: Text content that should not contain HTML

    Returns:
        Text with all HTML tags removed
    """
    if not text:
        return ""
    return bleach.clean(text, tags=[], strip=True)


def validate_email(email: str) -> bool:
    """
    Validate email format using regex.

    Args:
        email: Email address to validate

    Returns:
        True if email format is valid, False otherwise
    """
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_url(url: str) -> str:
    """
    Sanitize and validate URLs, removing dangerous protocols.

    Prevents javascript:, data:, vbscript: injection attacks.

    Args:
        url: URL to sanitize

    Returns:
        Sanitized URL or empty string if dangerous
    """
    if not url:
        return ""

    # Remove whitespace
    url = url.strip()

    # Block dangerous protocols
    if url.startswith(('javascript:', 'data:', 'vbscript:', 'file:', 'about:')):
        return ""

    # Ensure http or https
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    return url


def sanitize_filename(filename: str) -> str:
    """
    Remove dangerous characters from filenames.

    Prevents path traversal attacks (../) and OS command injection.

    Args:
        filename: Filename to sanitize

    Returns:
        Safe filename with only alphanumeric, dots, hyphens, and underscores
    """
    if not filename:
        return ""

    # Remove path traversal attempts
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')

    # Allow only alphanumeric, dots, hyphens, underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    # Limit length to prevent filesystem issues
    return filename[:255]


def sanitize_json_field(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize a generic JSON field by removing HTML and limiting length.

    Used for fields like post titles, summaries, etc.

    Args:
        value: Field value to sanitize
        max_length: Maximum allowed length (optional)

    Returns:
        Sanitized field value
    """
    if not value:
        return ""

    # Strip HTML tags
    sanitized = sanitize_plain_text(value)

    # Strip leading/trailing whitespace
    sanitized = sanitized.strip()

    # Enforce max length if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def detect_xss_attempt(text: str) -> bool:
    """
    Detect potential XSS attack patterns.

    Args:
        text: Text to analyze

    Returns:
        True if XSS patterns detected, False otherwise
    """
    if not text:
        return False

    # XSS patterns to detect
    xss_patterns = [
        r'<script[^>]*>',
        r'javascript:',
        r'on\w+\s*=',  # Event handlers like onclick=
        r'<iframe',
        r'<object',
        r'<embed',
        r'onerror\s*=',
        r'onload\s*=',
    ]

    text_lower = text.lower()
    for pattern in xss_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True

    return False


# Platform-specific sanitizers
def sanitize_twitter_content(content: str) -> str:
    """Sanitize Twitter post content (280 char, plain text)"""
    return sanitize_plain_text(content)[:280]


def sanitize_linkedin_content(content: str) -> str:
    """Sanitize LinkedIn post content (3000 char, allows some HTML)"""
    return sanitize_html(content)[:3000]


def sanitize_threads_content(content: str) -> str:
    """Sanitize Threads post content (500 char, plain text)"""
    return sanitize_plain_text(content)[:500]


def sanitize_instagram_caption(content: str) -> str:
    """Sanitize Instagram caption (2200 char, plain text)"""
    return sanitize_plain_text(content)[:2200]
