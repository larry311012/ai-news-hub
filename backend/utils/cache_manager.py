"""
Redis Cache Manager with decorators and utilities

Provides a comprehensive caching layer with:
- Automatic JSON serialization/deserialization
- Key namespacing
- TTL management
- Cache invalidation patterns
- Hit/miss tracking
- Decorator support for easy caching
"""
import json
import hashlib
import functools
from typing import Any, Optional, Callable
from datetime import datetime
import asyncio
from loguru import logger

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from config.redis_config import get_async_redis_client, RedisConfig


class CacheManager:
    """
    Centralized cache management with automatic serialization.

    Features:
    - Automatic JSON serialization
    - Key namespacing
    - TTL management
    - Cache invalidation patterns
    - Hit/miss tracking (via Redis INFO)

    Example:
        >>> cache = CacheManager(namespace="users")
        >>> await cache.set("user:123", {"name": "John", "email": "john@example.com"}, ttl=300)
        >>> user_data = await cache.get("user:123")
        >>> await cache.delete("user:123")
    """

    def __init__(self, namespace: str = "aipost"):
        """
        Initialize cache manager.

        Args:
            namespace: Prefix for all cache keys (default: "aipost")
        """
        self.namespace = namespace
        self.enabled = RedisConfig.CACHE_ENABLED

    def _make_key(self, key: str) -> str:
        """
        Create namespaced cache key.

        Args:
            key: Raw cache key

        Returns:
            Namespaced key (e.g., "aipost:user:123")
        """
        return f"{self.namespace}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.enabled:
            return None

        try:
            redis = await get_async_redis_client()
            full_key = self._make_key(key)
            value = await redis.get(full_key)

            if value is None:
                if RedisConfig.CACHE_DEBUG:
                    logger.debug(f"Cache MISS: {full_key}")
                return None

            if RedisConfig.CACHE_DEBUG:
                logger.debug(f"Cache HIT: {full_key}")

            # Deserialize JSON
            return json.loads(value)

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default: CACHE_TTL_MEDIUM = 5 minutes)

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            redis = await get_async_redis_client()
            full_key = self._make_key(key)

            # Serialize to JSON
            serialized = json.dumps(value, default=str)

            # Set with TTL
            if ttl is None:
                ttl = RedisConfig.CACHE_TTL_MEDIUM

            await redis.setex(full_key, ttl, serialized)

            if RedisConfig.CACHE_DEBUG:
                logger.debug(f"Cache SET: {full_key} (TTL: {ttl}s)")

            return True

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            redis = await get_async_redis_client()
            full_key = self._make_key(key)
            await redis.delete(full_key)

            if RedisConfig.CACHE_DEBUG:
                logger.debug(f"Cache DELETE: {full_key}")

            return True

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Glob pattern (e.g., "user:123:*")

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            redis = await get_async_redis_client()
            full_pattern = self._make_key(pattern)

            # Get all matching keys
            keys = []
            async for key in redis.scan_iter(match=full_pattern):
                keys.append(key)

            if keys:
                deleted = await redis.delete(*keys)
                if RedisConfig.CACHE_DEBUG:
                    logger.debug(f"Cache DELETE PATTERN: {full_pattern} ({deleted} keys)")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key to check

        Returns:
            True if key exists
        """
        if not self.enabled:
            return False

        try:
            redis = await get_async_redis_client()
            full_key = self._make_key(key)
            return await redis.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
        """
        Increment counter in cache.

        Args:
            key: Cache key
            amount: Amount to increment by (default: 1)
            ttl: Optional TTL for the key

        Returns:
            New value after increment
        """
        if not self.enabled:
            return None

        try:
            redis = await get_async_redis_client()
            full_key = self._make_key(key)
            new_value = await redis.incrby(full_key, amount)

            # Set TTL if provided and this is a new key
            if ttl and new_value == amount:
                await redis.expire(full_key, ttl)

            return new_value
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, or None if key doesn't exist
        """
        if not self.enabled:
            return None

        try:
            redis = await get_async_redis_client()
            full_key = self._make_key(key)
            ttl = await redis.ttl(full_key)
            return ttl if ttl > 0 else None
        except Exception as e:
            logger.error(f"Cache get_ttl error for key {key}: {e}")
            return None


# Create default cache manager instance
cache = CacheManager()


def cache_key(*args, **kwargs) -> str:
    """
    Generate deterministic cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        MD5 hash of arguments as cache key

    Example:
        >>> cache_key(123, "test", foo="bar")
        'a1b2c3d4e5f6...'
    """
    # Combine args and kwargs into single string
    key_data = f"{args}:{sorted(kwargs.items())}"

    # Create hash
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(
    ttl: int = RedisConfig.CACHE_TTL_MEDIUM,
    key_prefix: str = "",
    key_builder: Optional[Callable] = None
):
    """
    Decorator for caching async function results.

    Usage:
        @cached(ttl=300, key_prefix="user")
        async def get_user(user_id: int):
            # Expensive database query
            return await db.query(User).filter(User.id == user_id).first()

    Args:
        ttl: Cache TTL in seconds (default: 5 minutes)
        key_prefix: Prefix for cache key (default: "")
        key_builder: Custom function to build cache key from args

    Returns:
        Decorated async function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key_str = key_builder(*args, **kwargs)
            else:
                cache_key_str = cache_key(*args, **kwargs)

            full_key = f"{key_prefix}:{func.__name__}:{cache_key_str}"

            # Try to get from cache
            cached_value = await cache.get(full_key)
            if cached_value is not None:
                return cached_value

            # Cache miss - call function
            result = await func(*args, **kwargs)

            # Store in cache (only if result is not None)
            if result is not None:
                await cache.set(full_key, result, ttl=ttl)

            return result

        # Add cache invalidation method
        async def invalidate(*args, **kwargs):
            """Invalidate cache for this function call."""
            if key_builder:
                cache_key_str = key_builder(*args, **kwargs)
            else:
                cache_key_str = cache_key(*args, **kwargs)

            full_key = f"{key_prefix}:{func.__name__}:{cache_key_str}"
            await cache.delete(full_key)

        # Add cache invalidation pattern method
        async def invalidate_pattern(pattern: str):
            """Invalidate all cache entries matching pattern."""
            full_pattern = f"{key_prefix}:{func.__name__}:{pattern}"
            await cache.delete_pattern(full_pattern)

        wrapper.invalidate = invalidate
        wrapper.invalidate_pattern = invalidate_pattern
        return wrapper

    return decorator


class CacheStats:
    """Utility class for gathering cache statistics."""

    @staticmethod
    async def get_stats() -> dict:
        """
        Get Redis cache statistics.

        Returns:
            Dictionary with cache stats including hit rate, memory usage, etc.
        """
        try:
            redis = await get_async_redis_client()

            # Get Redis info
            info = await redis.info()

            # Calculate hit rate
            hits = int(info.get("keyspace_hits", 0))
            misses = int(info.get("keyspace_misses", 0))
            total = hits + misses
            hit_rate = round((hits / total) * 100, 2) if total > 0 else 0.0

            return {
                "enabled": RedisConfig.CACHE_ENABLED,
                "connected": True,
                "used_memory_human": info.get("used_memory_human"),
                "used_memory_bytes": info.get("used_memory"),
                "connected_clients": info.get("connected_clients"),
                "total_connections_received": info.get("total_connections_received"),
                "keyspace_hits": hits,
                "keyspace_misses": misses,
                "hit_rate_percent": hit_rate,
                "evicted_keys": info.get("evicted_keys", 0),
                "expired_keys": info.get("expired_keys", 0),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "redis_version": info.get("redis_version"),
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "enabled": RedisConfig.CACHE_ENABLED,
                "connected": False,
                "error": str(e)
            }

    @staticmethod
    async def flush_all() -> bool:
        """
        Flush all cache entries (USE WITH CAUTION).

        Returns:
            True if successful
        """
        try:
            redis = await get_async_redis_client()
            await redis.flushdb()
            logger.warning("Cache flushed - all keys deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to flush cache: {e}")
            return False
