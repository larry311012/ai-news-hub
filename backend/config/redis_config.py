"""
Redis Configuration for Caching Layer

Provides centralized Redis configuration with connection pooling,
async support, and comprehensive TTL management.
"""
import os
from typing import Optional
from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from loguru import logger


class RedisConfig:
    """Redis connection configuration with production-ready defaults."""

    # Connection settings
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    REDIS_SSL = os.getenv("REDIS_SSL", "false").lower() == "true"

    # Connection pool settings
    REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", 50))
    REDIS_SOCKET_TIMEOUT = int(os.getenv("REDIS_SOCKET_TIMEOUT", 5))
    REDIS_SOCKET_CONNECT_TIMEOUT = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", 5))

    # Cache TTL settings (in seconds)
    CACHE_TTL_SHORT = 60  # 1 minute (for rapidly changing data)
    CACHE_TTL_MEDIUM = 300  # 5 minutes (for semi-static data)
    CACHE_TTL_LONG = 3600  # 1 hour (for static data)
    CACHE_TTL_VERY_LONG = 86400  # 24 hours (for rarely changing data)

    # Feature flags
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_DEBUG = os.getenv("CACHE_DEBUG", "false").lower() == "true"


# Singleton Redis clients
_redis_client: Optional[Redis] = None
_async_redis_client: Optional[AsyncRedis] = None


def get_redis_client() -> Redis:
    """
    Get synchronous Redis client (for non-async contexts).

    Returns:
        Redis: Synchronous Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = Redis(
            host=RedisConfig.REDIS_HOST,
            port=RedisConfig.REDIS_PORT,
            db=RedisConfig.REDIS_DB,
            password=RedisConfig.REDIS_PASSWORD,
            ssl=RedisConfig.REDIS_SSL,
            max_connections=RedisConfig.REDIS_MAX_CONNECTIONS,
            socket_timeout=RedisConfig.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=RedisConfig.REDIS_SOCKET_CONNECT_TIMEOUT,
            decode_responses=True
        )
        logger.info("Synchronous Redis client initialized")

    return _redis_client


async def get_async_redis_client() -> AsyncRedis:
    """
    Get async Redis client (for FastAPI async contexts).

    Returns:
        AsyncRedis: Async Redis client instance
    """
    global _async_redis_client

    if _async_redis_client is None:
        _async_redis_client = AsyncRedis(
            host=RedisConfig.REDIS_HOST,
            port=RedisConfig.REDIS_PORT,
            db=RedisConfig.REDIS_DB,
            password=RedisConfig.REDIS_PASSWORD,
            ssl=RedisConfig.REDIS_SSL,
            max_connections=RedisConfig.REDIS_MAX_CONNECTIONS,
            socket_timeout=RedisConfig.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=RedisConfig.REDIS_SOCKET_CONNECT_TIMEOUT,
            decode_responses=True
        )
        logger.info("Async Redis client initialized")

    return _async_redis_client


async def close_redis_connections():
    """Close Redis connections on app shutdown."""
    global _redis_client, _async_redis_client

    if _redis_client:
        _redis_client.close()
        _redis_client = None
        logger.info("Synchronous Redis connection closed")

    if _async_redis_client:
        await _async_redis_client.close()
        _async_redis_client = None
        logger.info("Async Redis connection closed")


async def test_redis_connection() -> bool:
    """
    Test Redis connection on startup.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        redis = await get_async_redis_client()
        await redis.ping()
        logger.info("Redis connection test successful")
        return True
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False
