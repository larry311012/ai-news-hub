"""
Caching Service

Provides a unified caching interface with support for:
- In-memory caching (development)
- Redis caching (production)
- TTL-based expiration
- Cache invalidation

Usage:
    from services.cache_service import cache_service

    # Set value
    cache_service.set("user:123:quota", {"remaining": 10}, ttl=300)

    # Get value
    quota = cache_service.get("user:123:quota")

    # Delete value
    cache_service.delete("user:123:quota")
"""
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import json
import hashlib
from loguru import logger


class InMemoryCache:
    """Simple in-memory cache with TTL support"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self._cache:
            self._stats["misses"] += 1
            return None

        entry = self._cache[key]

        # Check expiration
        if "expires_at" in entry and entry["expires_at"] < datetime.utcnow():
            del self._cache[key]
            self._stats["misses"] += 1
            return None

        self._stats["hits"] += 1
        return entry["value"]

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL (seconds)"""
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)

            self._cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": datetime.utcnow()
            }

            self._stats["sets"] += 1
            return True

        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if key in self._cache:
            del self._cache[key]
            self._stats["deletes"] += 1
            return True
        return False

    def clear(self) -> bool:
        """Clear entire cache"""
        self._cache.clear()
        return True

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self._stats,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "size": len(self._cache)
        }

    def cleanup_expired(self) -> int:
        """Remove expired entries"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in self._cache.items()
            if "expires_at" in entry and entry["expires_at"] < now
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)


class RedisCache:
    """Redis-based cache (for production)"""

    def __init__(self, redis_url: str):
        """
        Initialize Redis cache

        Args:
            redis_url: Redis connection URL
        """
        try:
            import redis
            self._redis = redis.from_url(redis_url, decode_responses=True)
            self._available = True
            logger.info(f"Redis cache initialized: {redis_url}")
        except ImportError:
            logger.warning("Redis library not installed, falling back to in-memory cache")
            self._available = False
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._available = False

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if not self._available:
            return None

        try:
            value = self._redis.get(key)
            if value is None:
                return None

            # Deserialize JSON
            return json.loads(value)

        except Exception as e:
            logger.error(f"Redis get failed for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in Redis with TTL"""
        if not self._available:
            return False

        try:
            # Serialize to JSON
            serialized = json.dumps(value)

            # Set with TTL
            self._redis.setex(key, ttl, serialized)
            return True

        except Exception as e:
            logger.error(f"Redis set failed for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from Redis"""
        if not self._available:
            return False

        try:
            self._redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete failed for key {key}: {e}")
            return False

    def clear(self) -> bool:
        """Clear entire cache (use with caution!)"""
        if not self._available:
            return False

        try:
            self._redis.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis clear failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        if not self._available:
            return {"available": False}

        try:
            info = self._redis.info("stats")
            return {
                "available": True,
                "total_commands": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate_percent": self._calculate_hit_rate(info)
            }
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            return {"available": False, "error": str(e)}

    @staticmethod
    def _calculate_hit_rate(info: Dict) -> float:
        """Calculate cache hit rate from Redis info"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses

        if total == 0:
            return 0.0

        return round((hits / total) * 100, 2)


class CacheService:
    """
    Unified cache service with automatic backend selection

    Automatically uses Redis if available, otherwise falls back to in-memory.
    """

    def __init__(self):
        """Initialize cache service"""
        from config.settings import settings

        self._backend_type = settings.CACHE_BACKEND
        self._enabled = settings.CACHE_ENABLED
        self._default_ttl = settings.CACHE_TTL_SECONDS

        # Initialize backend
        if self._backend_type == "redis" and settings.REDIS_URL:
            self._backend = RedisCache(settings.REDIS_URL)
        else:
            self._backend = InMemoryCache()
            logger.info("Using in-memory cache")

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if not self._enabled:
            return None

        return self._backend.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: from config)

        Returns:
            bool: True if successful
        """
        if not self._enabled:
            return False

        if ttl is None:
            ttl = self._default_ttl

        return self._backend.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """
        Delete value from cache

        Args:
            key: Cache key

        Returns:
            bool: True if successful
        """
        if not self._enabled:
            return False

        return self._backend.delete(key)

    def clear(self) -> bool:
        """
        Clear entire cache

        Use with caution!

        Returns:
            bool: True if successful
        """
        if not self._enabled:
            return False

        return self._backend.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            dict: Cache statistics including hit rate, size, etc.
        """
        return self._backend.get_stats()

    def generate_key(self, *parts: Any) -> str:
        """
        Generate a cache key from parts

        Args:
            *parts: Key components

        Returns:
            str: Cache key

        Example:
            key = cache_service.generate_key("quota", user_id, date)
            # Returns: "quota:123:2024-01-15"
        """
        key_parts = [str(part) for part in parts]
        return ":".join(key_parts)

    def generate_hash_key(self, prefix: str, data: Any) -> str:
        """
        Generate a hash-based cache key

        Useful for caching based on complex data structures.

        Args:
            prefix: Key prefix
            data: Data to hash (must be JSON serializable)

        Returns:
            str: Cache key with hash

        Example:
            key = cache_service.generate_hash_key("prompt", {
                "text": "AI article",
                "style": "modern"
            })
            # Returns: "prompt:a3f2b8c9..."
        """
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()[:12]
        return f"{prefix}:{data_hash}"

    def cached(self, key: str, ttl: Optional[int] = None):
        """
        Decorator for caching function results

        Args:
            key: Cache key (can include {arg} placeholders)
            ttl: Time to live in seconds

        Example:
            @cache_service.cached("user:{user_id}:profile", ttl=600)
            def get_user_profile(user_id: int):
                # Expensive operation
                return fetch_from_db(user_id)
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Format key with arguments
                cache_key = key.format(**kwargs)

                # Try to get from cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached_value

                # Cache miss - execute function
                logger.debug(f"Cache MISS: {cache_key}")
                result = func(*args, **kwargs)

                # Store in cache
                self.set(cache_key, result, ttl)

                return result

            return wrapper
        return decorator


# Singleton instance
cache_service = CacheService()


# ========================================================================
# HELPER FUNCTIONS
# ========================================================================

def get_cache_service() -> CacheService:
    """
    Get cache service instance (for dependency injection)

    Usage:
        from services.cache_service import get_cache_service

        def endpoint(cache: CacheService = Depends(get_cache_service)):
            quota = cache.get("user:123:quota")
    """
    return cache_service
