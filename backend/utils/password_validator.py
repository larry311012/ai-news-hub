"""
Phase 4: Password validation and strength checking with breach detection
"""
import re
import os
import hashlib
import logging
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Load common passwords list
COMMON_PASSWORDS_FILE = Path(__file__).parent.parent / "common_passwords.txt"


def load_common_passwords() -> set:
    """Load common passwords from file"""
    try:
        if COMMON_PASSWORDS_FILE.exists():
            with open(COMMON_PASSWORDS_FILE, "r") as f:
                return {line.strip().lower() for line in f if line.strip()}
    except (FileNotFoundError, IOError, PermissionError) as e:
        logger.warning(f"Could not load common passwords file: {e}. Using default password list.")
    except Exception as e:
        logger.error(f"Unexpected error loading common passwords file: {e}", exc_info=True)

    # Return a small set of very common passwords as fallback
    return {
        "password",
        "123456",
        "12345678",
        "qwerty",
        "abc123",
        "monkey",
        "1234567",
        "letmein",
        "trustno1",
        "dragon",
        "baseball",
        "iloveyou",
        "master",
        "sunshine",
        "ashley",
        "bailey",
        "passw0rd",
        "shadow",
        "123123",
        "654321",
    }


COMMON_PASSWORDS = load_common_passwords()


class PasswordBreachChecker:
    """Check if password has been exposed in data breaches (HIBP)"""

    HIBP_API = "https://api.pwnedpasswords.com/range/"

    @staticmethod
    async def is_password_breached(password: str) -> tuple[bool, int]:
        """
        Check if password appears in haveibeenpwned database
        Returns (is_breached, count_found)
        """
        # Hash password with SHA-1
        sha1_hash = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()

        # Use k-anonymity: only send first 5 chars
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]

        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{PasswordBreachChecker.HIBP_API}{prefix}")

            if response.status_code != 200:
                # If API fails, don't block user
                return False, 0

            # Check if our hash suffix appears in results
            hashes = response.text.split("\r\n")
            for hash_line in hashes:
                if ":" not in hash_line:
                    continue
                hash_suffix, count = hash_line.split(":")
                if hash_suffix == suffix:
                    return True, int(count)

            return False, 0

        except Exception:
            # If check fails, don't block user
            return False, 0

    @staticmethod
    def is_password_breached_sync(password: str) -> tuple[bool, int]:
        """
        Synchronous version for non-async contexts
        Returns (is_breached, count_found)
        """
        # Hash password with SHA-1
        sha1_hash = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()

        # Use k-anonymity: only send first 5 chars
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]

        try:
            import requests

            response = requests.get(f"{PasswordBreachChecker.HIBP_API}{prefix}", timeout=5.0)

            if response.status_code != 200:
                # If API fails, don't block user
                return False, 0

            # Check if our hash suffix appears in results
            hashes = response.text.split("\r\n")
            for hash_line in hashes:
                if ":" not in hash_line:
                    continue
                hash_suffix, count = hash_line.split(":")
                if hash_suffix == suffix:
                    return True, int(count)

            return False, 0

        except Exception:
            # If check fails, don't block user
            return False, 0


def check_password_strength(
    password: str, user_email: str = None, user_name: str = None
) -> Dict[str, Any]:
    """
    Check password strength and return detailed results.

    Args:
        password: Password to check
        user_email: User's email (to check for similarity)
        user_name: User's full name (to check for similarity)

    Returns:
        Dictionary with strength score and requirements met
    """
    requirements = {
        "min_length": False,
        "has_uppercase": False,
        "has_lowercase": False,
        "has_number": False,
        "has_special": False,
        "not_common": False,
        "not_email": False,
        "not_name": False,
    }

    score = 0
    max_score = 100
    messages = []

    # Check minimum length (8 characters)
    if len(password) >= 8:
        requirements["min_length"] = True
        score += 20
    else:
        messages.append("Password must be at least 8 characters long")

    # Check for uppercase letter
    if re.search(r"[A-Z]", password):
        requirements["has_uppercase"] = True
        score += 15
    else:
        messages.append("Password must contain at least one uppercase letter")

    # Check for lowercase letter
    if re.search(r"[a-z]", password):
        requirements["has_lowercase"] = True
        score += 15
    else:
        messages.append("Password must contain at least one lowercase letter")

    # Check for number
    if re.search(r"\d", password):
        requirements["has_number"] = True
        score += 15
    else:
        messages.append("Password must contain at least one number")

    # Check for special character
    if re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        requirements["has_special"] = True
        score += 15
    else:
        messages.append("Password must contain at least one special character")

    # Check if password is not in common passwords list
    if password.lower() not in COMMON_PASSWORDS:
        requirements["not_common"] = True
        score += 10
    else:
        messages.append("Password is too common. Please choose a more unique password")

    # Check if password doesn't contain email
    if user_email:
        email_username = user_email.split("@")[0].lower()
        if email_username not in password.lower() and password.lower() not in email_username:
            requirements["not_email"] = True
            score += 5
        else:
            messages.append("Password should not be similar to your email")
    else:
        requirements["not_email"] = True
        score += 5

    # Check if password doesn't contain name
    if user_name:
        name_parts = user_name.lower().split()
        contains_name = any(
            part in password.lower() or password.lower() in part
            for part in name_parts
            if len(part) > 2
        )
        if not contains_name:
            requirements["not_name"] = True
            score += 5
        else:
            messages.append("Password should not be similar to your name")
    else:
        requirements["not_name"] = True
        score += 5

    # Bonus points for longer passwords
    if len(password) >= 12:
        score += 5
    if len(password) >= 16:
        score += 5

    # Determine strength level
    if score >= 90:
        strength = "strong"
    elif score >= 70:
        strength = "good"
    elif score >= 50:
        strength = "fair"
    else:
        strength = "weak"

    return {
        "score": min(score, max_score),
        "strength": strength,
        "requirements": requirements,
        "messages": messages,
        "is_valid": all(
            [
                requirements["min_length"],
                requirements["has_uppercase"],
                requirements["has_lowercase"],
                requirements["has_number"],
                requirements["has_special"],
                requirements["not_common"],
            ]
        ),
    }


def validate_password_strength(
    password: str, user_email: str = None, user_name: str = None
) -> bool:
    """
    Validate that password meets minimum requirements.

    Args:
        password: Password to validate
        user_email: User's email
        user_name: User's full name

    Returns:
        True if password meets all requirements

    Raises:
        ValueError: If password doesn't meet requirements
    """
    result = check_password_strength(password, user_email, user_name)

    if not result["is_valid"]:
        # Combine all error messages
        error_message = "; ".join(result["messages"])
        raise ValueError(error_message)

    return True


def generate_password_requirements_text() -> str:
    """Generate human-readable password requirements"""
    return """Password must meet the following requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter (A-Z)
    - Contains at least one lowercase letter (a-z)
    - Contains at least one number (0-9)
    - Contains at least one special character (!@#$%^&*()_+-=[]{}...)
    - Not a commonly used password
    - Not similar to your email or name
    """
