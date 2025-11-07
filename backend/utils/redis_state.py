"""
Redis-based state storage for OAuth flows (Production)

This module provides Redis-backed storage for OAuth state parameters and PKCE verifiers.
Falls back to in-memory storage if Redis is not available.
"""
import json
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Try to import redis, but gracefully handle if not installed
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis package not installed. Using in-memory state storage only.")

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

# Initialize Redis client
redis_client = None

if REDIS_AVAILABLE:
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        redis_client.ping()  # Test connection
        logger.info(f"Redis connection successful: {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Falling back to in-memory storage.")
        redis_client = None


def is_redis_available() -> bool:
    """Check if Redis is available and connected"""
    return redis_client is not None


def store_oauth_state(state: str, data: Dict[str, Any], ttl_seconds: int = 600) -> bool:
    """
    Store OAuth state in Redis with TTL.

    Args:
        state: OAuth state parameter
        data: State data to store (user_id, platform, return_url, etc.)
        ttl_seconds: Time to live in seconds (default: 10 minutes)

    Returns:
        True if stored successfully, False otherwise
    """
    if not redis_client:
        return False

    try:
        key = f"oauth_state:{state}"
        value = json.dumps(data, default=str)
        redis_client.setex(key, ttl_seconds, value)
        logger.debug(f"Stored OAuth state: {state}")
        return True
    except Exception as e:
        logger.error(f"Failed to store OAuth state: {e}")
        return False


def get_oauth_state(state: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve OAuth state from Redis.

    Args:
        state: OAuth state parameter

    Returns:
        State data dictionary or None if not found
    """
    if not redis_client:
        return None

    try:
        key = f"oauth_state:{state}"
        value = redis_client.get(key)
        if value:
            data = json.loads(value)
            logger.debug(f"Retrieved OAuth state: {state}")
            return data
        return None
    except Exception as e:
        logger.error(f"Failed to retrieve OAuth state: {e}")
        return None


def delete_oauth_state(state: str) -> bool:
    """
    Delete OAuth state from Redis.

    Args:
        state: OAuth state parameter

    Returns:
        True if deleted successfully, False otherwise
    """
    if not redis_client:
        return False

    try:
        key = f"oauth_state:{state}"
        redis_client.delete(key)
        logger.debug(f"Deleted OAuth state: {state}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete OAuth state: {e}")
        return False


def store_pkce_verifier(state: str, verifier: str, ttl_seconds: int = 600) -> bool:
    """
    Store PKCE code_verifier in Redis.

    Args:
        state: OAuth state parameter (used as key)
        verifier: PKCE code_verifier
        ttl_seconds: Time to live in seconds (default: 10 minutes)

    Returns:
        True if stored successfully, False otherwise
    """
    if not redis_client:
        return False

    try:
        key = f"pkce_verifier:{state}"
        redis_client.setex(key, ttl_seconds, verifier)
        logger.debug(f"Stored PKCE verifier for state: {state}")
        return True
    except Exception as e:
        logger.error(f"Failed to store PKCE verifier: {e}")
        return False


def get_pkce_verifier(state: str) -> Optional[str]:
    """
    Retrieve PKCE code_verifier from Redis.

    Args:
        state: OAuth state parameter

    Returns:
        PKCE code_verifier or None if not found
    """
    if not redis_client:
        return None

    try:
        key = f"pkce_verifier:{state}"
        verifier = redis_client.get(key)
        if verifier:
            logger.debug(f"Retrieved PKCE verifier for state: {state}")
        return verifier
    except Exception as e:
        logger.error(f"Failed to retrieve PKCE verifier: {e}")
        return None


def delete_pkce_verifier(state: str) -> bool:
    """
    Delete PKCE verifier from Redis.

    Args:
        state: OAuth state parameter

    Returns:
        True if deleted successfully, False otherwise
    """
    if not redis_client:
        return False

    try:
        key = f"pkce_verifier:{state}"
        redis_client.delete(key)
        logger.debug(f"Deleted PKCE verifier for state: {state}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete PKCE verifier: {e}")
        return False


def cleanup_expired_states() -> int:
    """
    Cleanup expired OAuth states and PKCE verifiers.
    This is done automatically by Redis TTL, but this function
    can be called manually if needed.

    Returns:
        Number of keys cleaned up
    """
    if not redis_client:
        return 0

    try:
        # Redis automatically handles TTL expiration
        # This function is here for compatibility with in-memory storage
        logger.debug("Redis automatically handles expired state cleanup via TTL")
        return 0
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return 0


# Health check function for monitoring
def redis_health_check() -> Dict[str, Any]:
    """
    Check Redis health status.

    Returns:
        Dictionary with health status information
    """
    if not REDIS_AVAILABLE:
        return {"available": False, "connected": False, "error": "Redis package not installed"}

    if not redis_client:
        return {"available": True, "connected": False, "error": "Redis client not connected"}

    try:
        redis_client.ping()
        info = redis_client.info("server")
        return {
            "available": True,
            "connected": True,
            "version": info.get("redis_version", "unknown"),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
        }
    except Exception as e:
        return {"available": True, "connected": False, "error": str(e)}
