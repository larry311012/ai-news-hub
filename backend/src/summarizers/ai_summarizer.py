import os
from typing import List, Dict, Optional
from loguru import logger
from src.utils import retry_with_backoff
from src.utils.ai_exceptions import AIProviderError, RateLimitError
from src.utils.ai_error_handler import AIErrorHandler


class AISummarizer:
    """Summarizes news articles using AI/LLM APIs"""

    def __init__(self, provider: str = "openai", model: Optional[str] = None):
        """
        Initialize AI summarizer

        Args:
            provider: AI provider (openai, anthropic)
            model: Model name (optional, uses defaults)
        """
        self.provider = provider.lower()
        self.model = model or self._get_default_model()
        self.client = self._initialize_client()
        self.error_handler = AIErrorHandler()

    def _get_default_model(self) -> str:
        """Get default model for provider"""
        defaults = {"openai": "gpt-4-turbo-preview", "anthropic": "claude-3-5-sonnet-20241022"}
        return defaults.get(self.provider, "gpt-4-turbo-preview")

    def _initialize_client(self):
        """Initialize the appropriate AI client"""
        try:
            if self.provider == "openai":
                from openai import OpenAI

                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY environment variable not set")
                return OpenAI(api_key=api_key)

            elif self.provider == "anthropic":
                from anthropic import Anthropic

                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY environment variable not set")
                return Anthropic(api_key=api_key)

            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            logger.error(f"Failed to initialize {self.provider} client: {e}")
            raise

    def summarize_articles(
        self,
        articles: List[Dict],
        max_articles: int = 10,
        user_id: Optional[int] = None,
    ) -> Dict:
        """
        Summarize multiple articles into key insights

        Args:
            articles: List of article dictionaries
            max_articles: Maximum articles to process
            user_id: User ID for context (optional)

        Returns:
            Dictionary with summary and key insights

        Raises:
            AIProviderError: If AI provider call fails with user-friendly message
        """
        if not articles:
            return {"summary": "", "insights": [], "topics": []}

        # Sort by date and take most recent
        sorted_articles = sorted(articles, key=lambda x: x.get("published", ""), reverse=True)[
            :max_articles
        ]

        # Create context from articles
        context = self._build_context(sorted_articles)

        # Generate summary with error handling
        prompt = self._create_summary_prompt(context)

        try:
            summary = self._call_llm(
                prompt,
                context={
                    "user_id": user_id,
                    "operation": "summarize_articles",
                    "num_articles": len(sorted_articles),
                },
            )

            return {
                "summary": summary,
                "articles_processed": len(sorted_articles),
                "sources": list(set(a["source"] for a in sorted_articles)),
            }

        except AIProviderError as e:
            # Re-raise our custom exceptions with context
            self.error_handler.log_error(e, user_id=user_id)
            raise

        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error in summarize_articles: {e}")
            raise

    def _build_context(self, articles: List[Dict]) -> str:
        """Build context string from articles"""
        context_parts = []

        for i, article in enumerate(articles, 1):
            context_parts.append(
                f"{i}. {article['title']}\n"
                f"   Source: {article['source']}\n"
                f"   Summary: {article.get('summary', 'N/A')[:200]}\n"
                f"   Link: {article['link']}\n"
            )

        return "\n".join(context_parts)

    def _create_summary_prompt(self, context: str) -> str:
        """Create prompt for summarization"""
        return f"""You are an AI news analyst. Review these recent AI-related news articles and create a concise summary.

Articles:
{context}

Please provide:
1. A brief overview of the main themes and developments (2-3 sentences)
2. 3-5 key insights or trends emerging from these articles
3. Why these developments matter for the AI industry

Keep the tone informative yet engaging, suitable for social media."""

    def _call_llm(self, prompt: str, context: Optional[Dict] = None, max_retries: int = 3) -> str:
        """
        Call the LLM API with retry logic and comprehensive error handling

        Args:
            prompt: The prompt to send
            context: Additional context for error logging
            max_retries: Maximum number of retry attempts

        Returns:
            Generated text from the LLM

        Raises:
            AIProviderError: Structured error with user-friendly message
        """
        context = context or {}

        for attempt in range(max_retries):
            try:
                if self.provider == "openai":
                    return self._call_openai(prompt)
                elif self.provider == "anthropic":
                    return self._call_anthropic(prompt)

            except Exception as e:
                # Map to our custom exception
                if self.provider == "openai":
                    ai_error = self.error_handler.handle_openai_error(e, context)
                elif self.provider == "anthropic":
                    ai_error = self.error_handler.handle_anthropic_error(e, context)
                else:
                    ai_error = self.error_handler.handle_generic_error(e, self.provider, context)

                # Determine if we should retry
                should_retry = self.error_handler.should_retry(ai_error, attempt, max_retries)

                if should_retry and attempt < max_retries - 1:
                    # Calculate retry delay
                    delay = self.error_handler.get_retry_delay(attempt)

                    logger.warning(
                        f"Retrying {self.provider} call (attempt {attempt + 1}/{max_retries}) "
                        f"after {delay:.1f}s due to: {ai_error.error_type.value}"
                    )

                    import time

                    time.sleep(delay)
                    continue
                else:
                    # No more retries or non-retryable error
                    raise ai_error

        # Should not reach here, but just in case
        raise AIProviderError(
            provider=self.provider,
            error_type="unknown_error",
            message=f"Failed to call {self.provider} after {max_retries} attempts",
            context=context,
        )

    def _call_openai(self, prompt: str) -> str:
        """
        Call OpenAI API

        Args:
            prompt: The prompt to send

        Returns:
            Generated text

        Raises:
            OpenAI exceptions (will be caught and mapped by _call_llm)
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert AI news analyst."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
            timeout=30.0,
        )
        return response.choices[0].message.content

    def _call_anthropic(self, prompt: str) -> str:
        """
        Call Anthropic API

        Args:
            prompt: The prompt to send

        Returns:
            Generated text

        Raises:
            Anthropic exceptions (will be caught and mapped by _call_llm)
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
            timeout=30.0,
        )
        return response.content[0].text

    def generate_headline(self, summary: str, user_id: Optional[int] = None) -> str:
        """
        Generate an attention-grabbing headline

        Args:
            summary: The summary text
            user_id: User ID for context (optional)

        Returns:
            Generated headline

        Raises:
            AIProviderError: If AI provider call fails
        """
        prompt = f"""Based on this AI news summary, create a short, engaging headline (max 10 words) that would work well on social media:

{summary[:500]}

Headline:"""

        try:
            return self._call_llm(
                prompt,
                context={
                    "user_id": user_id,
                    "operation": "generate_headline",
                },
            ).strip()

        except AIProviderError as e:
            self.error_handler.log_error(e, user_id=user_id)
            raise

        except Exception as e:
            logger.error(f"Unexpected error in generate_headline: {e}")
            # Return fallback headline
            return "Latest AI News Update"
