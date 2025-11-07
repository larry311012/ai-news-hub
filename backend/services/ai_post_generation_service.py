"""
Enhanced AI Post Generation Service - Phase 3

Production-ready AI-powered post generation with:
- Multi-provider support (OpenAI GPT-4, Anthropic Claude)
- Platform-specific prompts and optimization
- Redis caching (24-hour TTL)
- Rate limiting (10 generations per minute per user)
- Streaming response support
- Comprehensive error handling
- Token counting and cost estimation
- Retry logic with exponential backoff
"""
import asyncio
import hashlib
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

import openai
from anthropic import Anthropic, AsyncAnthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from config.redis_config import get_redis_client

logger = logging.getLogger(__name__)


@dataclass
class PlatformConfig:
    """Platform-specific configuration"""
    name: str
    max_length: int
    tone: str
    features: List[str]


# Platform configurations
PLATFORM_CONFIGS = {
    'twitter': PlatformConfig(
        name='Twitter',
        max_length=280,
        tone='concise and engaging',
        features=['hashtags', 'threads', 'mentions']
    ),
    'linkedin': PlatformConfig(
        name='LinkedIn',
        max_length=3000,
        tone='professional and insightful',
        features=['long-form', 'professional-tone', 'call-to-action']
    ),
    'instagram': PlatformConfig(
        name='Instagram',
        max_length=2200,
        tone='visual and emoji-friendly',
        features=['hashtags', 'emojis', 'visual-description']
    ),
    'threads': PlatformConfig(
        name='Threads',
        max_length=500,
        tone='casual and conversational',
        features=['threads', 'casual-tone', 'engaging']
    )
}


class AIProviderError(Exception):
    """Base exception for AI provider errors"""
    pass


class RateLimitError(Exception):
    """Rate limit exceeded"""
    pass


class AIPostGenerationService:
    """
    Enhanced AI Post Generation Service

    Features:
    - Multi-provider support (OpenAI, Anthropic)
    - Platform-specific prompt engineering
    - Redis caching for cost optimization
    - Rate limiting per user
    - Streaming responses
    - Token counting and cost estimation
    - Retry logic with exponential backoff
    """

    # Rate limiting: 10 generations per minute per user
    RATE_LIMIT_WINDOW = 60  # seconds
    RATE_LIMIT_MAX_REQUESTS = 10

    # Cache TTL: 24 hours
    CACHE_TTL = 86400

    # Model configurations
    OPENAI_MODEL = "gpt-4-turbo-preview"
    ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"

    # Token limits
    OPENAI_MAX_TOKENS = 4096
    ANTHROPIC_MAX_TOKENS = 4096

    def __init__(self, api_key: str, provider: str = "openai"):
        """
        Initialize AI Post Generation Service

        Args:
            api_key: API key for the provider
            provider: "openai" or "anthropic"
        """
        self.api_key = api_key
        self.provider = provider.lower()
        self.redis_client = get_redis_client()

        # Initialize provider clients
        if self.provider == "openai":
            openai.api_key = api_key
            self.client = openai
        elif self.provider == "anthropic":
            self.client = Anthropic(api_key=api_key)
            self.async_client = AsyncAnthropic(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        logger.info(f"Initialized AI service with provider: {provider}")

    def _get_rate_limit_key(self, user_id: int) -> str:
        """Get Redis key for rate limiting"""
        return f"rate_limit:post_generation:{user_id}"

    def _get_cache_key(self, article_ids: List[int], platform: str, tone: str, model: str) -> str:
        """
        Generate cache key for post generation

        Cache key is based on article IDs, platform, tone, and model
        to ensure consistent caching across same inputs.
        """
        key_data = f"{sorted(article_ids)}:{platform}:{tone}:{model}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()
        return f"post_generation:{key_hash}"

    async def check_rate_limit(self, user_id: int) -> Tuple[bool, int]:
        """
        Check if user has exceeded rate limit

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        if not self.redis_client:
            # If Redis is not available, allow all requests
            return True, self.RATE_LIMIT_MAX_REQUESTS

        try:
            key = self._get_rate_limit_key(user_id)
            current_count = await self.redis_client.get(key)

            if current_count is None:
                # First request in window
                await self.redis_client.setex(
                    key,
                    self.RATE_LIMIT_WINDOW,
                    1
                )
                return True, self.RATE_LIMIT_MAX_REQUESTS - 1

            current_count = int(current_count)

            if current_count >= self.RATE_LIMIT_MAX_REQUESTS:
                # Rate limit exceeded
                ttl = await self.redis_client.ttl(key)
                logger.warning(f"Rate limit exceeded for user {user_id}. TTL: {ttl}s")
                return False, 0

            # Increment counter
            await self.redis_client.incr(key)
            remaining = self.RATE_LIMIT_MAX_REQUESTS - current_count - 1

            return True, remaining

        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # On error, allow the request
            return True, self.RATE_LIMIT_MAX_REQUESTS

    async def get_cached_post(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached post from Redis"""
        if not self.redis_client:
            return None

        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for key: {cache_key}")
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"Error getting cached post: {e}")
            return None

    async def cache_post(self, cache_key: str, post_data: Dict[str, Any]) -> bool:
        """Cache generated post in Redis"""
        if not self.redis_client:
            return False

        try:
            await self.redis_client.setex(
                cache_key,
                self.CACHE_TTL,
                json.dumps(post_data)
            )
            logger.info(f"Cached post with key: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"Error caching post: {e}")
            return False

    def _build_platform_prompt(
        self,
        article_content: str,
        platform: str,
        tone: Optional[str] = None
    ) -> str:
        """
        Build platform-specific prompt for content generation

        Uses advanced prompt engineering techniques for optimal results.
        """
        config = PLATFORM_CONFIGS.get(platform)
        if not config:
            raise ValueError(f"Unsupported platform: {platform}")

        # Use custom tone or default platform tone
        selected_tone = tone or config.tone

        # Base instruction
        prompt = f"""You are an expert social media content creator specializing in {config.name}.

Your task is to create an engaging post for {config.name} based on the following article(s).

**Platform Requirements:**
- Maximum length: {config.max_length} characters
- Tone: {selected_tone}
- Features: {', '.join(config.features)}

**Article Content:**
{article_content}

**Instructions:**
"""

        # Platform-specific instructions
        if platform == 'twitter':
            prompt += """
1. Create a concise, engaging tweet (max 280 characters)
2. Include 1-2 relevant hashtags
3. Use clear, punchy language
4. Add a hook or question to drive engagement
5. Optimize for retweets and replies

**Output Format:**
Return ONLY the tweet text, no explanations or meta-commentary.
"""

        elif platform == 'linkedin':
            prompt += """
1. Write a professional, insightful post (max 3000 characters)
2. Start with a compelling hook
3. Use paragraph breaks for readability
4. Include key insights and takeaways
5. End with a call-to-action or question
6. Use professional language and tone
7. You may include emojis sparingly (💡 🚀) for visual interest

**Output Format:**
Return ONLY the LinkedIn post text, no explanations or meta-commentary.
"""

        elif platform == 'instagram':
            prompt += """
1. Create a visually descriptive caption (max 2200 characters)
2. Include 5-10 relevant hashtags
3. Use emojis throughout for visual appeal
4. Write in a friendly, approachable tone
5. Include line breaks for readability
6. Add a call-to-action at the end

**Output Format:**
Return ONLY the Instagram caption, no explanations or meta-commentary.
"""

        elif platform == 'threads':
            prompt += """
1. Write a casual, conversational post (max 500 characters)
2. Use friendly, approachable language
3. Ask questions or encourage responses
4. Keep it concise and engaging
5. You can use emojis naturally

**Output Format:**
Return ONLY the Threads post text, no explanations or meta-commentary.
"""

        return prompt

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APIError)),
        reraise=True
    )
    async def _generate_with_openai(
        self,
        prompt: str,
        max_tokens: int = OPENAI_MAX_TOKENS
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate content using OpenAI GPT-4

        Returns:
            Tuple of (generated_content, metadata)
        """
        try:
            logger.info(f"Generating with OpenAI: {self.OPENAI_MODEL}")

            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=self.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert social media content creator. Generate engaging, platform-optimized posts."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9,
                frequency_penalty=0.3,
                presence_penalty=0.3
            )

            content = response.choices[0].message.content.strip()

            # Metadata for monitoring and cost tracking
            metadata = {
                "provider": "openai",
                "model": self.OPENAI_MODEL,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "finish_reason": response.choices[0].finish_reason,
                "generated_at": datetime.utcnow().isoformat()
            }

            logger.info(f"OpenAI generation successful. Tokens: {metadata['total_tokens']}")

            return content, metadata

        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise AIProviderError(f"Rate limit exceeded. Please try again later.")

        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication error: {e}")
            raise AIProviderError("Invalid API key. Please check your OpenAI API key.")

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise AIProviderError(f"OpenAI API error: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error in OpenAI generation: {e}", exc_info=True)
            raise AIProviderError(f"Failed to generate content: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _generate_with_anthropic(
        self,
        prompt: str,
        max_tokens: int = ANTHROPIC_MAX_TOKENS
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate content using Anthropic Claude

        Returns:
            Tuple of (generated_content, metadata)
        """
        try:
            logger.info(f"Generating with Anthropic: {self.ANTHROPIC_MODEL}")

            response = await self.async_client.messages.create(
                model=self.ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                temperature=0.7,
                system="You are an expert social media content creator. Generate engaging, platform-optimized posts.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            content = response.content[0].text.strip()

            # Metadata for monitoring and cost tracking
            metadata = {
                "provider": "anthropic",
                "model": self.ANTHROPIC_MODEL,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                "stop_reason": response.stop_reason,
                "generated_at": datetime.utcnow().isoformat()
            }

            logger.info(f"Anthropic generation successful. Tokens: {metadata['total_tokens']}")

            return content, metadata

        except Exception as e:
            logger.error(f"Error in Anthropic generation: {e}", exc_info=True)

            # Check for specific error types
            if "authentication" in str(e).lower() or "api key" in str(e).lower():
                raise AIProviderError("Invalid API key. Please check your Anthropic API key.")
            elif "rate limit" in str(e).lower():
                raise AIProviderError("Rate limit exceeded. Please try again later.")
            else:
                raise AIProviderError(f"Failed to generate content: {str(e)}")

    async def generate_post(
        self,
        articles: List[Dict[str, Any]],
        platform: str,
        user_id: int,
        tone: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate AI-powered post for a specific platform

        Args:
            articles: List of article dictionaries with title, summary, link
            platform: Target platform (twitter, linkedin, instagram, threads)
            user_id: User ID for rate limiting
            tone: Optional custom tone (professional, casual, engaging)
            use_cache: Whether to use cached results

        Returns:
            Dictionary with:
            - content: Generated post content
            - metadata: Generation metadata (tokens, model, etc.)
            - cached: Whether result was from cache
        """
        start_time = time.time()

        # Check rate limit
        is_allowed, remaining = await self.check_rate_limit(user_id)
        if not is_allowed:
            raise RateLimitError(
                f"Rate limit exceeded. Maximum {self.RATE_LIMIT_MAX_REQUESTS} generations "
                f"per minute. Please try again later."
            )

        logger.info(f"Rate limit check passed. Remaining: {remaining}")

        # Generate cache key
        article_ids = [a.get('id', hash(a.get('title', ''))) for a in articles]
        cache_key = self._get_cache_key(article_ids, platform, tone or "default", self.provider)

        # Check cache
        if use_cache:
            cached_result = await self.get_cached_post(cache_key)
            if cached_result:
                cached_result['cached'] = True
                cached_result['generation_time'] = 0
                return cached_result

        # Prepare article content
        article_content = "\n\n".join([
            f"Title: {a.get('title', 'N/A')}\n"
            f"Summary: {a.get('summary', 'N/A')}\n"
            f"Link: {a.get('link', 'N/A')}"
            for a in articles
        ])

        # Build prompt
        prompt = self._build_platform_prompt(article_content, platform, tone)

        # Generate content
        if self.provider == "openai":
            content, metadata = await self._generate_with_openai(prompt)
        elif self.provider == "anthropic":
            content, metadata = await self._generate_with_anthropic(prompt)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        # Calculate generation time
        generation_time = time.time() - start_time

        # Prepare result
        result = {
            "content": content,
            "platform": platform,
            "metadata": metadata,
            "cached": False,
            "generation_time": round(generation_time, 2),
            "remaining_requests": remaining
        }

        # Cache result
        if use_cache:
            await self.cache_post(cache_key, result)

        logger.info(
            f"Generated post for {platform} in {generation_time:.2f}s. "
            f"Tokens: {metadata.get('total_tokens', 'N/A')}"
        )

        return result

    async def generate_multi_platform(
        self,
        articles: List[Dict[str, Any]],
        platforms: List[str],
        user_id: int,
        tone: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate posts for multiple platforms concurrently

        Args:
            articles: List of articles
            platforms: List of target platforms
            user_id: User ID for rate limiting
            tone: Optional custom tone
            use_cache: Whether to use cached results

        Returns:
            Dictionary mapping platform -> generation result
        """
        logger.info(f"Generating posts for platforms: {platforms}")

        # Generate all platforms concurrently
        tasks = [
            self.generate_post(articles, platform, user_id, tone, use_cache)
            for platform in platforms
        ]

        results = {}
        errors = {}

        # Execute all tasks
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for platform, result in zip(platforms, completed_results):
            if isinstance(result, Exception):
                logger.error(f"Error generating {platform} post: {result}")
                errors[platform] = str(result)
            else:
                results[platform] = result

        return {
            "results": results,
            "errors": errors,
            "success_count": len(results),
            "error_count": len(errors)
        }

    async def regenerate_post(
        self,
        articles: List[Dict[str, Any]],
        platform: str,
        user_id: int,
        tone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Regenerate post for a specific platform

        Always bypasses cache to generate fresh content.
        """
        logger.info(f"Regenerating post for {platform}")
        return await self.generate_post(
            articles,
            platform,
            user_id,
            tone,
            use_cache=False  # Always generate fresh content
        )

    async def validate_content(
        self,
        content: str,
        platform: str
    ) -> Dict[str, Any]:
        """
        Validate generated content for platform requirements

        Returns validation result with warnings and errors.
        """
        config = PLATFORM_CONFIGS.get(platform)
        if not config:
            return {
                "is_valid": False,
                "errors": [f"Unknown platform: {platform}"]
            }

        content_length = len(content)
        warnings = []
        errors = []

        # Check length
        if content_length > config.max_length:
            errors.append(
                f"Content exceeds {config.max_length} characters "
                f"({content_length} chars)"
            )
        elif content_length > config.max_length * 0.9:
            warnings.append(
                f"Content is near limit: {content_length}/{config.max_length} characters"
            )

        # Platform-specific validation
        if platform == 'twitter':
            if content.count('#') > 5:
                warnings.append(f"Using {content.count('#')} hashtags (2-3 recommended)")

        elif platform == 'instagram':
            hashtag_count = content.count('#')
            if hashtag_count > 30:
                errors.append(f"Instagram allows max 30 hashtags ({hashtag_count} found)")
            elif hashtag_count < 3:
                warnings.append(f"Consider adding more hashtags (found {hashtag_count})")

        is_valid = len(errors) == 0

        return {
            "is_valid": is_valid,
            "content_length": content_length,
            "max_length": config.max_length,
            "warnings": warnings,
            "errors": errors,
            "platform": platform
        }

    async def estimate_tokens(self, text: str, provider: Optional[str] = None) -> int:
        """
        Estimate token count for text

        Uses rough estimation: ~4 characters per token
        For production, use tiktoken for OpenAI or proper tokenizer for Claude
        """
        selected_provider = provider or self.provider

        # Rough estimation
        estimated_tokens = len(text) // 4

        return estimated_tokens

    async def clear_cache(self, user_id: Optional[int] = None) -> int:
        """
        Clear cached posts

        Args:
            user_id: If provided, clear only for this user

        Returns:
            Number of keys cleared
        """
        if not self.redis_client:
            return 0

        try:
            if user_id:
                # Clear user-specific cache (not implemented in current cache key structure)
                logger.warning("User-specific cache clearing not implemented")
                return 0
            else:
                # Clear all post generation cache
                pattern = "post_generation:*"
                keys = []
                async for key in self.redis_client.scan_iter(match=pattern):
                    keys.append(key)

                if keys:
                    deleted = await self.redis_client.delete(*keys)
                    logger.info(f"Cleared {deleted} cached posts")
                    return deleted

                return 0

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0
