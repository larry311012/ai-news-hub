"""
Auth mode selector - switches between normal and anonymous auth based on environment
"""
import os
import logging

logger = logging.getLogger(__name__)

# Read ANONYMOUS_MODE from environment
ANONYMOUS_MODE = os.getenv("ANONYMOUS_MODE", "false").lower() == "true"

# Import both auth systems
from utils.auth import (
    get_current_user_dependency as normal_auth,
    create_session,
    delete_session,
    cleanup_expired_sessions,
    hash_password,
    verify_password,
    generate_session_token,
    generate_session_fingerprint,
    validate_session_fingerprint,
    get_current_user_optional
)
from utils.anonymous_auth import get_current_user_anonymous

# Select the appropriate auth dependency based on mode
if ANONYMOUS_MODE:
    logger.warning("=" * 80)
    logger.warning("ANONYMOUS MODE ENABLED")
    logger.warning("All API requests will use user_id=1 (no authentication required)")
    logger.warning("WARNING: Only use in single-user deployments!")
    logger.warning("=" * 80)
    get_current_user = get_current_user_anonymous
    get_current_user_dependency = get_current_user_anonymous  # Alias for compatibility
else:
    logger.info("Normal authentication mode enabled")
    get_current_user = normal_auth
    get_current_user_dependency = normal_auth  # Alias for compatibility

# Export all auth functions
__all__ = [
    "get_current_user",
    "get_current_user_dependency",  # Add alias to exports
    "ANONYMOUS_MODE",
    "create_session",
    "delete_session",
    "cleanup_expired_sessions",
    "hash_password",
    "verify_password",
    "generate_session_token",
    "generate_session_fingerprint",
    "validate_session_fingerprint",
    "get_current_user_optional"
]
