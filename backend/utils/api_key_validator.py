"""
API Key Validation Utilities

Provides validation functions for API keys from different providers
to catch formatting errors before encryption/storage.
"""
import re
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def validate_openai_key(key: str) -> Tuple[bool, str]:
    """
    Validate OpenAI API key format.

    Valid formats:
    - sk-proj-... (project keys, newer format)
    - sk-... (legacy keys)

    Args:
        key: API key to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if key passes validation
        - error_message: Empty string if valid, error description if invalid
    """
    if not key:
        return False, "API key cannot be empty"

    # Remove whitespace
    key = key.strip()

    # Check prefix
    if not key.startswith('sk-'):
        return False, "OpenAI keys must start with 'sk-' (found: '{}...')".format(key[:5] if len(key) >= 5 else key)

    # Check minimum length
    if len(key) < 20:
        return False, f"OpenAI keys must be at least 20 characters (got {len(key)} characters)"

    # Check for valid characters (alphanumeric, hyphens, underscores)
    if not re.match(r'^sk-[a-zA-Z0-9_-]+$', key):
        invalid_chars = set(c for c in key if not (c.isalnum() or c in '-_'))
        return False, f"OpenAI keys contain invalid characters: {invalid_chars}"

    # Specific format checks
    if key.startswith('sk-proj-'):
        # Project keys should be longer
        if len(key) < 40:
            return False, f"OpenAI project keys are typically longer (got {len(key)} characters)"

    return True, ""


def validate_anthropic_key(key: str) -> Tuple[bool, str]:
    """
    Validate Anthropic (Claude) API key format.

    Valid format: sk-ant-...

    Args:
        key: API key to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not key:
        return False, "API key cannot be empty"

    # Remove whitespace
    key = key.strip()

    # Check prefix
    if not key.startswith('sk-ant-'):
        return False, "Anthropic keys must start with 'sk-ant-' (found: '{}...')".format(key[:10] if len(key) >= 10 else key)

    # Check minimum length
    if len(key) < 30:
        return False, f"Anthropic keys must be at least 30 characters (got {len(key)} characters)"

    # Check for valid characters
    if not re.match(r'^sk-ant-[a-zA-Z0-9_-]+$', key):
        invalid_chars = set(c for c in key if not (c.isalnum() or c in '-_'))
        return False, f"Anthropic keys contain invalid characters: {invalid_chars}"

    return True, ""


def validate_api_key(provider: str, key: str) -> Tuple[bool, str]:
    """
    Validate an API key for a specific provider.

    Args:
        provider: Provider name (e.g., 'openai', 'anthropic')
        key: API key to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    provider = provider.lower().strip()

    # Provider-specific validation
    validators = {
        'openai': validate_openai_key,
        'anthropic': validate_anthropic_key,
    }

    if provider in validators:
        return validators[provider](key)

    # Generic validation for unknown providers
    if not key or not key.strip():
        return False, f"API key for {provider} cannot be empty"

    if len(key.strip()) < 10:
        return False, f"API key for {provider} seems too short (got {len(key.strip())} characters)"

    return True, ""


def sanitize_api_key(key: str) -> str:
    """
    Sanitize an API key before storage.

    Operations:
    - Strip leading/trailing whitespace
    - Remove newlines/carriage returns
    - Normalize Unicode (if needed)

    Args:
        key: Raw API key from user input

    Returns:
        Sanitized API key
    """
    if not key:
        return ""

    # Strip whitespace
    key = key.strip()

    # Remove newlines and carriage returns
    key = key.replace('\n', '').replace('\r', '')

    # Remove any zero-width characters (Unicode edge case)
    key = ''.join(c for c in key if ord(c) >= 32 and ord(c) != 127)

    return key


def mask_api_key(key: str, show_prefix_chars: int = 7, show_suffix_chars: int = 4) -> str:
    """
    Mask an API key for display purposes.

    Args:
        key: API key to mask
        show_prefix_chars: Number of characters to show at the beginning
        show_suffix_chars: Number of characters to show at the end

    Returns:
        Masked API key (e.g., "sk-proj-...E8dcA")
    """
    if not key:
        return "***"

    if len(key) <= show_prefix_chars + show_suffix_chars:
        # Key is too short to mask meaningfully
        return "***" + key[-min(4, len(key)):]

    prefix = key[:show_prefix_chars]
    suffix = key[-show_suffix_chars:]

    return f"{prefix}...{suffix}"


def detect_potential_corruption(key: str) -> Tuple[bool, str]:
    """
    Detect potential corruption in an API key.

    Common corruption patterns:
    - Missing first character (e.g., 'k-...' instead of 'sk-...')
    - Truncated key
    - Garbled characters

    Args:
        key: API key to check

    Returns:
        Tuple of (is_corrupted, corruption_description)
    """
    if not key:
        return True, "Key is empty"

    # Check for common corruption patterns
    corruption_patterns = {
        r'^k-': "Missing 's' prefix (should start with 'sk-')",
        r'^-': "Missing prefix (starts with '-')",
        r'^sk$': "Key is truncated (only 'sk')",
        r'^sk-$': "Key is truncated (only 'sk-')",
        r'[^\x20-\x7E]': "Contains non-printable characters",
    }

    for pattern, description in corruption_patterns.items():
        if re.search(pattern, key):
            return True, description

    # Check for suspiciously short keys
    if len(key) < 10:
        return True, f"Key is suspiciously short ({len(key)} characters)"

    return False, ""


# Test cases for validation
if __name__ == "__main__":
    print("Testing API Key Validation\n")

    # Test OpenAI keys
    openai_tests = [
        ("sk-proj-abc123def456ghi789jkl012mno345pqr678", True, "Valid project key"),
        ("sk-abc123def456ghi789", True, "Valid legacy key"),
        ("k-proj-abc123", False, "Missing 's' prefix"),
        ("  sk-proj-abc123  ", True, "Key with whitespace (should trim)"),
        ("sk-", False, "Too short"),
        ("abc123", False, "Wrong prefix"),
        ("", False, "Empty key"),
    ]

    print("OpenAI Key Validation:")
    print("-" * 60)
    for key, expected_valid, description in openai_tests:
        is_valid, error = validate_openai_key(key)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"{status} {description}")
        print(f"   Input: {repr(key)}")
        print(f"   Result: valid={is_valid}, error='{error}'")
        print()

    # Test Anthropic keys
    anthropic_tests = [
        ("sk-ant-api03-abc123def456", True, "Valid key"),
        ("sk-ant-", False, "Too short"),
        ("sk-abc123", False, "Wrong prefix"),
    ]

    print("\nAnthropic Key Validation:")
    print("-" * 60)
    for key, expected_valid, description in anthropic_tests:
        is_valid, error = validate_anthropic_key(key)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"{status} {description}")
        print(f"   Input: {repr(key)}")
        print(f"   Result: valid={is_valid}, error='{error}'")
        print()

    # Test corruption detection
    corruption_tests = [
        ("k-proj-abc123", True, "Missing 's' prefix"),
        ("sk-proj-abc123", False, "Valid key"),
        ("-proj-abc123", True, "Missing 'sk' prefix"),
        ("sk", True, "Truncated"),
    ]

    print("\nCorruption Detection:")
    print("-" * 60)
    for key, expected_corrupted, description in corruption_tests:
        is_corrupted, corruption = detect_potential_corruption(key)
        status = "✅" if is_corrupted == expected_corrupted else "❌"
        print(f"{status} {description}")
        print(f"   Input: {repr(key)}")
        print(f"   Result: corrupted={is_corrupted}, description='{corruption}'")
        print()
