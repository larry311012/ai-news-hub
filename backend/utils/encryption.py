"""
Encryption utilities for API keys and sensitive data

This module provides encryption/decryption functionality using AES-256 (Fernet)
for securely storing API keys and other sensitive data in the database.
"""
from cryptography.fernet import Fernet, InvalidToken
import os
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Encryption key from environment
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())


def get_cipher_suite() -> Fernet:
    """
    Get the Fernet cipher suite for encryption/decryption.

    Returns:
        Fernet cipher suite instance
    """
    return Fernet(ENCRYPTION_KEY.encode())


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value using AES-256 (Fernet).

    Args:
        value: Plain text string to encrypt

    Returns:
        Encrypted string (base64 encoded)

    Raises:
        Exception: If encryption fails
    """
    try:
        cipher_suite = get_cipher_suite()
        encrypted_bytes = cipher_suite.encrypt(value.encode())
        encrypted_str = encrypted_bytes.decode()
        logger.debug("Successfully encrypted value")
        return encrypted_str
    except Exception as e:
        logger.error(f"Encryption failed: {str(e)}")
        raise Exception(f"Failed to encrypt value: {str(e)}")


def decrypt_value(encrypted_value: str) -> Optional[str]:
    """
    Decrypt an encrypted string value.

    Args:
        encrypted_value: Encrypted string (base64 encoded)

    Returns:
        Decrypted plain text string, or None if decryption fails
    """
    try:
        cipher_suite = get_cipher_suite()
        decrypted_bytes = cipher_suite.decrypt(encrypted_value.encode())
        decrypted_str = decrypted_bytes.decode()
        logger.debug("Successfully decrypted value")
        return decrypted_str
    except InvalidToken:
        logger.error("Decryption failed: Invalid token or encryption key changed")
        return None
    except Exception as e:
        logger.error(f"Decryption failed: {str(e)}")
        return None


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for secure storage.

    This is a convenience wrapper around encrypt_value specifically for API keys.

    Args:
        api_key: Plain text API key

    Returns:
        Encrypted API key string

    Raises:
        Exception: If encryption fails
    """
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")

    return encrypt_value(api_key.strip())


def decrypt_api_key(encrypted_api_key: str) -> Optional[str]:
    """
    Decrypt an API key from storage.

    This is a convenience wrapper around decrypt_value specifically for API keys.

    Args:
        encrypted_api_key: Encrypted API key string

    Returns:
        Decrypted API key, or None if decryption fails
    """
    if not encrypted_api_key or not encrypted_api_key.strip():
        logger.warning("Attempted to decrypt empty API key")
        return None

    return decrypt_value(encrypted_api_key.strip())


def validate_encryption_key() -> bool:
    """
    Validate that the encryption key is properly configured.

    Returns:
        True if encryption key is valid, False otherwise
    """
    try:
        # Try to create a cipher suite
        cipher_suite = get_cipher_suite()

        # Test encryption/decryption
        test_value = "test_encryption_validation"
        encrypted = cipher_suite.encrypt(test_value.encode())
        decrypted = cipher_suite.decrypt(encrypted).decode()

        if decrypted == test_value:
            logger.info("Encryption key validation successful")
            return True
        else:
            logger.error("Encryption key validation failed: decryption mismatch")
            return False

    except Exception as e:
        logger.error(f"Encryption key validation failed: {str(e)}")
        return False
