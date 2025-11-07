"""
AI Content Cache - Reduce AI API costs by caching generated content

This module caches AI-generated social media posts to avoid re-generating
identical content, saving on AI API costs and improving response times.

Cost Savings Example:
- Without cache: Generate 10 posts from same articles = 10 API calls = $0.20
- With cache: Generate 10 posts from same articles = 1 API call + 9 cache hits = $0.02
- Savings: 90% reduction in AI API costs
"""
import hashlib
from typing import Optional, List
from loguru import logger

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.cache_manager import cache
from config.redis_config import RedisConfig


class AIContentCache:
    """
    Cache for AI-generated content to reduce API costs.

    Uses content-based hashing to identify identical generation requests
    and return cached results instead of making expensive AI API calls.
    """

    @staticmethod
    def _content_hash(articles: List[dict], platforms: List[str]) -> str:
        """
        Create deterministic hash from articles and platforms.

        Args:
            articles: List of article dictionaries
            platforms: List of platform names

        Returns:
            SHA256 hash (first 16 chars) for cache key
        """
        # Sort articles by title for consistency
        article_titles = sorted([a.get('title', '') for a in articles])

        # Sort platforms for consistency
        sorted_platforms = sorted(platforms)

        # Create content signature
        content = f"{article_titles}:{sorted_platforms}"

        # Hash it
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @staticmethod
    async def get_cached_content(
        articles: List[dict],
        platforms: List[str]
    ) -> Optional[dict]:
        """
        Get cached AI-generated content if available.

        Args:
            articles: List of article dictionaries
            platforms: List of platform names to generate for

        Returns:
            Dictionary of cached content per platform, or None if not cached

        Example:
            >>> cached = await AIContentCache.get_cached_content(articles, ["twitter", "linkedin"])
            >>> if cached:
            ...     twitter_post = cached["twitter"]
            ...     linkedin_post = cached["linkedin"]
        """
        cache_key = f"ai_content:{AIContentCache._content_hash(articles, platforms)}"

        cached = await cache.get(cache_key)

        if cached:
            logger.info(f"AI content cache HIT - saved API call for {len(platforms)} platforms")
        else:
            logger.debug(f"AI content cache MISS - will generate new content")

        return cached

    @staticmethod
    async def cache_content(
        articles: List[dict],
        platforms: List[str],
        content: dict
    ) -> bool:
        """
        Cache AI-generated content for future reuse.

        Args:
            articles: List of article dictionaries used for generation
            platforms: List of platform names
            content: Dictionary of generated content per platform

        Returns:
            True if caching successful

        Example:
            >>> content = {
            ...     "twitter": "AI advances in 2024...",
            ...     "linkedin": "Exciting developments in AI..."
            ... }
            >>> await AIContentCache.cache_content(articles, ["twitter", "linkedin"], content)
        """
        cache_key = f"ai_content:{AIContentCache._content_hash(articles, platforms)}"

        # Cache for 24 hours - AI content can be reused for a day
        success = await cache.set(
            cache_key,
            content,
            ttl=RedisConfig.CACHE_TTL_VERY_LONG  # 24 hours
        )

        if success:
            logger.info(f"Cached AI content for {len(platforms)} platforms (24h TTL)")

        return success

    @staticmethod
    async def invalidate_for_articles(article_ids: List[int]) -> int:
        """
        Invalidate all cached AI content that includes specific articles.

        Useful when articles are updated or deleted.

        Args:
            article_ids: List of article IDs to invalidate

        Returns:
            Number of cache entries invalidated
        """
        # This is a simple implementation - could be enhanced with article ID tracking
        # For now, we'll just log the invalidation request
        logger.info(f"AI content invalidation requested for articles: {article_ids}")

        # In a more sophisticated implementation, we'd track which cache entries
        # correspond to which articles, then delete only those entries
        # For simplicity, we're not implementing this now, but the pattern is here

        return 0


class AIImageCache:
    """
    Cache for AI-generated images (Instagram/social media).

    Similar to AIContentCache but for images with different TTL and storage.
    """

    @staticmethod
    def _image_prompt_hash(prompt: str, model: str, size: str) -> str:
        """
        Create hash from image generation parameters.

        Args:
            prompt: Image generation prompt
            model: AI model name (e.g., "dall-e-3")
            size: Image size (e.g., "1024x1024")

        Returns:
            SHA256 hash for cache key
        """
        content = f"{prompt}:{model}:{size}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @staticmethod
    async def get_cached_image_url(
        prompt: str,
        model: str = "dall-e-3",
        size: str = "1024x1024"
    ) -> Optional[str]:
        """
        Get cached image URL if same prompt was generated before.

        Args:
            prompt: Image generation prompt
            model: AI model name
            size: Image size

        Returns:
            Cached image URL or None
        """
        cache_key = f"ai_image:{AIImageCache._image_prompt_hash(prompt, model, size)}"

        cached = await cache.get(cache_key)

        if cached:
            logger.info(f"AI image cache HIT - saved image generation API call")
            return cached.get("url")

        logger.debug(f"AI image cache MISS - will generate new image")
        return None

    @staticmethod
    async def cache_image_url(
        prompt: str,
        image_url: str,
        model: str = "dall-e-3",
        size: str = "1024x1024"
    ) -> bool:
        """
        Cache generated image URL.

        Args:
            prompt: Image generation prompt
            image_url: URL of generated image
            model: AI model name
            size: Image size

        Returns:
            True if caching successful
        """
        cache_key = f"ai_image:{AIImageCache._image_prompt_hash(prompt, model, size)}"

        # Cache for 7 days - images are expensive to generate
        success = await cache.set(
            cache_key,
            {"url": image_url, "prompt": prompt, "model": model, "size": size},
            ttl=RedisConfig.CACHE_TTL_VERY_LONG * 7  # 7 days
        )

        if success:
            logger.info(f"Cached AI image URL (7 days TTL)")

        return success
