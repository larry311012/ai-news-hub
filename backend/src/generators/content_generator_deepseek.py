from typing import Dict, List, Optional
import re
from loguru import logger
from src.utils.ai_exceptions import AIProviderError
from src.utils.ai_error_handler import AIErrorHandler

# Import DeepSeek client
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "web" / "backend"))

from utils.deepseek_client import (
    DeepSeekClient,
    DeepSeekError,
    DeepSeekAuthenticationError,
    DeepSeekRateLimitError,
    DeepSeekTimeout,
)


class ContentGeneratorWithDeepSeek:
    """Generates platform-specific social media content with DeepSeek support"""

    def __init__(self, ai_client, platform_config: Dict):
        """
        Initialize content generator

        Args:
            ai_client: AI client (from summarizer - OpenAI, Anthropic, or DeepSeek)
            platform_config: Platform configurations
        """
        self.ai_client = ai_client
        self.platform_config = platform_config
        self.error_handler = AIErrorHandler()

    def generate_posts(
        self, summary: Dict, user_id: Optional[int] = None, post_id: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Generate posts for all enabled platforms

        Args:
            summary: Summary dictionary from AI summarizer
            user_id: User ID for context (optional)
            post_id: Post ID for context (optional)

        Returns:
            Dictionary mapping platform names to post content
            For Instagram, returns dict with 'caption', 'image_prompt', 'hashtags'
        """
        posts = {}

        for platform, config in self.platform_config.items():
            if config.get("enabled", False):
                try:
                    if platform == "instagram":
                        # Special handling for Instagram - generates caption + image prompt
                        instagram_content = self._generate_instagram_content(
                            summary, config, user_id=user_id, post_id=post_id
                        )
                        posts[platform] = instagram_content
                    else:
                        # Standard text post generation
                        post = self._generate_platform_post(
                            platform, summary, config, user_id=user_id, post_id=post_id
                        )
                        posts[platform] = post
                    logger.info(f"Generated post for {platform}")

                except AIProviderError as e:
                    # Log structured AI errors with context
                    self.error_handler.log_error(
                        e,
                        user_id=user_id,
                        additional_context={
                            "platform": platform,
                            "post_id": post_id,
                            "operation": "generate_post",
                        },
                    )
                    logger.error(f"AI error generating post for {platform}: {e.message}")
                    # Continue with other platforms even if one fails

                except Exception as e:
                    logger.error(f"Unexpected error generating post for {platform}: {e}")
                    # Continue with other platforms

        return posts

    def _generate_platform_post(
        self,
        platform: str,
        summary: Dict,
        config: Dict,
        user_id: Optional[int] = None,
        post_id: Optional[int] = None,
    ) -> str:
        """
        Generate a post for a specific platform

        Args:
            platform: Platform name
            summary: Article summary
            config: Platform config
            user_id: User ID for context
            post_id: Post ID for context

        Returns:
            Generated post content

        Raises:
            AIProviderError: If AI call fails
        """
        prompt = self._create_platform_prompt(platform, summary, config)
        max_length = config.get("max_length", 280)

        # Use the AI client to generate the post
        try:
            generated_content = ""
            provider = getattr(self.ai_client, "provider", None)

            if provider == "openai":
                try:
                    response = self.ai_client.client.chat.completions.create(
                        model=self.ai_client.model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a social media content creator. You must strictly respect character limits.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.8,
                        max_tokens=500,
                        timeout=30.0,
                    )
                    generated_content = response.choices[0].message.content.strip()

                except Exception as e:
                    ai_error = self.error_handler.handle_openai_error(
                        e, {"user_id": user_id, "platform": platform}
                    )
                    self.error_handler.log_error(ai_error, user_id=user_id)
                    raise ai_error

            elif provider == "anthropic":
                try:
                    response = self.ai_client.client.messages.create(
                        model=self.ai_client.model,
                        max_tokens=500,
                        temperature=0.8,
                        timeout=30.0,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    generated_content = response.content[0].text.strip()

                except Exception as e:
                    ai_error = self.error_handler.handle_anthropic_error(
                        e, {"user_id": user_id, "platform": platform}
                    )
                    self.error_handler.log_error(ai_error, user_id=user_id)
                    raise ai_error

            elif provider == "deepseek":
                try:
                    response = self.ai_client.client.chat_completion(
                        model=self.ai_client.model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a social media content creator. You must strictly respect character limits.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.8,
                        max_tokens=500,
                        timeout=30.0,
                    )
                    generated_content = response["choices"][0]["message"]["content"].strip()

                except Exception as e:
                    ai_error = self._handle_deepseek_error(
                        e, {"user_id": user_id, "platform": platform}
                    )
                    self.error_handler.log_error(ai_error, user_id=user_id)
                    raise ai_error

            # Enforce character limit (truncate if AI ignored instructions)
            if len(generated_content) > max_length:
                logger.warning(
                    f"{platform} content exceeded {max_length} chars ({len(generated_content)}), truncating"
                )
                # Truncate at last complete sentence before limit
                truncated = generated_content[:max_length]
                # Try to end at sentence boundary
                last_period = truncated.rfind(".")
                last_exclaim = truncated.rfind("!")
                last_question = truncated.rfind("?")
                last_sentence = max(last_period, last_exclaim, last_question)

                if last_sentence > max_length * 0.7:  # Only use if we keep at least 70%
                    generated_content = truncated[: last_sentence + 1]
                else:
                    # Just truncate and add ellipsis
                    generated_content = truncated[: max_length - 3].rstrip() + "..."

                logger.info(f"Truncated {platform} content to {len(generated_content)} chars")

            return generated_content

        except AIProviderError:
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            logger.error(f"Unexpected error in _generate_platform_post: {e}")
            raise

    def _create_platform_prompt(self, platform: str, summary: Dict, config: Dict) -> str:
        """Create platform-specific prompt"""

        max_length = config.get("max_length", 280)
        # Validate max_length
        if not isinstance(max_length, int) or max_length <= 0:
            logger.warning(f"Invalid max_length {max_length}, using default 280")
            max_length = 280

        # Apply safety margin for platforms with strict limits
        safety_margins = {
            "twitter": 20,  # Target 260 instead of 280 (emojis can be 2-4 bytes)
            "threads": 20,  # Target 480 instead of 500 (strict enforcement)
            "linkedin": 100,  # Target 2900 instead of 3000
        }
        target_length = max_length - safety_margins.get(platform, 20)

        tone = config.get("tone", "casual")
        hashtags = config.get("hashtags", [])

        base_prompt = f"""Create a {platform} post about this AI news summary:

{summary.get('summary', '')}

Requirements:
- STRICT character limit: {target_length} characters (absolute maximum: {max_length})
- Your post MUST be under {target_length} characters
- Count your characters carefully before responding
- Tone: {tone}
- Make it engaging and informative
- {f"Include these hashtags: {' '.join(hashtags)}" if hashtags else "Include relevant hashtags"}
"""

        # Platform-specific instructions
        platform_instructions = {
            "twitter": "Keep it punchy and conversational. Target 260 characters to be safe.",
            "linkedin": "Professional tone. Focus on business implications and insights. Use paragraphs. Target 2900 characters.",
            "threads": "CRITICAL: Must be under 480 characters. Be concise and punchy. Short paragraphs. This is non-negotiable - count your characters!",
            "instagram": "Visual-first mindset. Engaging caption that encourages interaction.",
        }

        instruction = platform_instructions.get(platform, "")
        if instruction:
            base_prompt += f"\n\nPlatform-specific guidance: {instruction}"

        base_prompt += "\n\nPost:"

        return base_prompt

    def _generate_instagram_content(
        self,
        summary: Dict,
        config: Dict,
        user_id: Optional[int] = None,
        post_id: Optional[int] = None,
    ) -> Dict:
        """
        Generate Instagram-specific content (caption + image prompt + hashtags)

        Args:
            summary: Article summary
            config: Instagram configuration
            user_id: User ID for context (optional)
            post_id: Post ID for context (optional)

        Returns:
            dict: {'caption': str, 'image_prompt': str, 'hashtags': list[str]}

        Raises:
            AIProviderError: If AI call fails with user-friendly message
        """
        try:
            # Generate caption
            caption = self._call_ai(
                self._create_instagram_caption_prompt(summary),
                max_tokens=400,
                context={"user_id": user_id, "post_id": post_id, "operation": "generate_instagram_caption"},
            )

            # Generate image prompt for DALL-E
            image_prompt = self._call_ai(
                self._create_instagram_image_prompt(summary),
                max_tokens=150,
                context={"user_id": user_id, "post_id": post_id, "operation": "generate_image_prompt"},
            )

            # Extract hashtags from caption
            hashtags = self._extract_hashtags(caption)

            return {"caption": caption, "image_prompt": image_prompt, "hashtags": hashtags}

        except AIProviderError as e:
            logger.error(f"AI error in Instagram content generation: {e.message}")
            raise

        except Exception as e:
            logger.error(f"Failed to generate Instagram content: {e}")
            # Return fallback content
            return {
                "caption": f"{summary.get('title', 'AI News')} #AI #Tech",
                "image_prompt": "Modern abstract AI technology visualization",
                "hashtags": ["AI", "Tech", "Innovation"],
            }

    def _create_instagram_caption_prompt(self, summary: Dict) -> str:
        """Create prompt for Instagram caption"""
        return f"""Create an engaging Instagram caption for this AI/tech news:

Title: {summary.get('title', '')}
Summary: {summary.get('summary', '')}

Requirements:
- Target 300-500 characters (strict maximum: 2200 characters)
- Conversational and engaging tone
- Use 2-3 relevant emojis appropriately
- Include 5-8 relevant hashtags at the end
- Add a call-to-action or question to encourage engagement
- Use line breaks for readability

Caption:"""

    def _create_instagram_image_prompt(self, summary: Dict) -> str:
        """Create prompt for Instagram image generation"""
        return f"""Create a DALL-E image prompt for this AI/tech article:

Title: {summary.get('title', '')}
Summary: {summary.get('summary', '')}

Requirements:
- Max 400 characters
- Describe a visually striking image
- Tech/AI aesthetic (modern, futuristic, or abstract)
- NO text, faces, or branded elements in the image
- Instagram-friendly (vibrant, engaging composition)

Image Prompt:"""

    def _extract_hashtags(self, caption: str) -> List[str]:
        """Extract hashtags from caption"""
        hashtags = re.findall(r"#(\w+)", caption)
        if len(hashtags) > 30:
            logger.warning(f"Too many hashtags ({len(hashtags)}), keeping first 30")
            hashtags = hashtags[:30]
        return hashtags

    def _call_ai(
        self, prompt: str, max_tokens: int = 500, context: Optional[Dict] = None
    ) -> str:
        """
        Call AI client to generate content with comprehensive error handling

        Args:
            prompt: Prompt for AI
            max_tokens: Maximum tokens to generate
            context: Additional context for error logging

        Returns:
            str: Generated content

        Raises:
            AIProviderError: If AI call fails with user-friendly message
        """
        context = context or {}
        provider = getattr(self.ai_client, "provider", None)

        try:
            if provider == "openai":
                try:
                    response = self.ai_client.client.chat.completions.create(
                        model=self.ai_client.model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an expert social media content creator.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.8,
                        max_tokens=max_tokens,
                        timeout=30.0,
                    )
                    return response.choices[0].message.content.strip()

                except Exception as e:
                    ai_error = self.error_handler.handle_openai_error(e, context)
                    raise ai_error

            elif provider == "anthropic":
                try:
                    response = self.ai_client.client.messages.create(
                        model=self.ai_client.model,
                        max_tokens=max_tokens,
                        temperature=0.8,
                        timeout=30.0,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    return response.content[0].text.strip()

                except Exception as e:
                    ai_error = self.error_handler.handle_anthropic_error(e, context)
                    raise ai_error

            elif provider == "deepseek":
                try:
                    response = self.ai_client.client.chat_completion(
                        model=self.ai_client.model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an expert social media content creator.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.8,
                        max_tokens=max_tokens,
                        timeout=30.0,
                    )
                    return response["choices"][0]["message"]["content"].strip()

                except Exception as e:
                    ai_error = self._handle_deepseek_error(e, context)
                    raise ai_error

            return ""

        except AIProviderError:
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            logger.error(f"Unexpected error in _call_ai: {e}")
            # Map to generic AI error
            ai_error = self.error_handler.handle_generic_error(e, provider or "unknown", context)
            raise ai_error

    def _handle_deepseek_error(self, error: Exception, context: Dict) -> AIProviderError:
        """
        Handle DeepSeek-specific errors and map to AIProviderError

        Args:
            error: Original DeepSeek exception
            context: Error context

        Returns:
            AIProviderError with user-friendly message
        """
        if isinstance(error, DeepSeekAuthenticationError):
            return AIProviderError(
                provider="deepseek",
                error_type="authentication_error",
                message="Invalid DeepSeek API key",
                user_message="Your DeepSeek API key is invalid. Please update it in your profile.",
                action="Update your API key in Profile > API Keys",
                retryable=False,
                context=context,
            )

        elif isinstance(error, DeepSeekRateLimitError):
            retry_after = getattr(error, "retry_after", None)
            return AIProviderError(
                provider="deepseek",
                error_type="rate_limit_error",
                message="DeepSeek rate limit exceeded",
                user_message="Too many requests. Please try again in a few moments.",
                action="Wait a moment and try again",
                retryable=True,
                retry_after=retry_after,
                context=context,
            )

        elif isinstance(error, DeepSeekTimeout):
            return AIProviderError(
                provider="deepseek",
                error_type="timeout_error",
                message="DeepSeek API request timed out",
                user_message="The request took too long. Please try again.",
                action="Try again",
                retryable=True,
                context=context,
            )

        elif isinstance(error, DeepSeekError):
            return AIProviderError(
                provider="deepseek",
                error_type="api_error",
                message=f"DeepSeek API error: {error.message}",
                user_message="An error occurred with DeepSeek. Please try again.",
                action="Try again or contact support if the issue persists",
                retryable=True,
                context=context,
            )

        else:
            return self.error_handler.handle_generic_error(error, "deepseek", context)
