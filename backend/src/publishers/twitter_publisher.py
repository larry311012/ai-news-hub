"""
Twitter Publisher - Publish content to Twitter using OAuth
"""
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from .exceptions import AuthenticationException, RateLimitException, PublishingException

# Constants
DEFAULT_TWEET_MAX_LENGTH = 280
THREAD_TWEET_MAX_LENGTH = 270  # Leave room for thread indicators


class TwitterPublisher:
    """Publishes content to Twitter using OAuth"""

    def __init__(self):
        """Initialize Twitter publisher"""
        self.api_base = "https://api.twitter.com/2"

    async def publish(self, content: str, access_token: str, metadata: dict = None) -> dict:
        """
        Publish tweet to Twitter using OAuth access token.

        Args:
            content: Tweet content (max 280 characters)
            access_token: OAuth access token (decrypted)
            metadata: Optional metadata (images, polls, etc.)

        Returns:
            {
                "success": True,
                "platform_post_id": "...",
                "platform_url": "...",
                "published_at": "..."
            }

        Raises:
            AuthenticationException: Token is invalid
            RateLimitException: Rate limit exceeded
            PublishingException: Generic publishing error
        """
        try:
            # Truncate content to 280 characters
            truncated_content = content[:DEFAULT_TWEET_MAX_LENGTH]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/tweets",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json={"text": truncated_content},
                )

                if response.status_code == 401:
                    raise AuthenticationException("Twitter token invalid or expired")
                elif response.status_code == 429:
                    # Twitter uses x-rate-limit-reset header
                    reset_time = response.headers.get("x-rate-limit-reset")
                    retry_after = (
                        int(reset_time) - int(datetime.utcnow().timestamp()) if reset_time else 900
                    )
                    raise RateLimitException("Twitter rate limit exceeded", retry_after)

                response.raise_for_status()
                data = response.json()

                tweet_id = data["data"]["id"]

                logger.info(f"Successfully published to Twitter: {tweet_id}")

                return {
                    "success": True,
                    "platform_post_id": tweet_id,
                    "platform_url": f"https://twitter.com/i/status/{tweet_id}",
                    "published_at": datetime.utcnow().isoformat(),
                }

        except (AuthenticationException, RateLimitException):
            raise
        except Exception as e:
            logger.error(f"Failed to publish to Twitter: {str(e)}")
            raise PublishingException(f"Failed to publish to Twitter: {str(e)}")

    async def publish_thread(self, content: str, access_token: str) -> dict:
        """
        Publish content as a Twitter thread if it exceeds character limit.

        Args:
            content: Long content to split into thread
            access_token: OAuth access token

        Returns:
            Publishing result with first tweet info
        """
        try:
            tweets = self._split_into_tweets(content)
            previous_tweet_id = None
            first_tweet_id = None

            async with httpx.AsyncClient() as client:
                for i, tweet in enumerate(tweets, 1):
                    tweet_data = {"text": tweet}
                    if previous_tweet_id:
                        tweet_data["reply"] = {"in_reply_to_tweet_id": previous_tweet_id}

                    response = await client.post(
                        f"{self.api_base}/tweets",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json",
                        },
                        json=tweet_data,
                    )

                    if response.status_code == 401:
                        raise AuthenticationException("Twitter token invalid or expired")
                    elif response.status_code == 429:
                        reset_time = response.headers.get("x-rate-limit-reset")
                        retry_after = (
                            int(reset_time) - int(datetime.utcnow().timestamp())
                            if reset_time
                            else 900
                        )
                        raise RateLimitException("Twitter rate limit exceeded", retry_after)

                    response.raise_for_status()
                    data = response.json()
                    tweet_id = data["data"]["id"]

                    if i == 1:
                        first_tweet_id = tweet_id

                    previous_tweet_id = tweet_id
                    logger.info(f"Published tweet {i}/{len(tweets)}: {tweet_id}")

            return {
                "success": True,
                "platform_post_id": first_tweet_id,
                "platform_url": f"https://twitter.com/i/status/{first_tweet_id}",
                "published_at": datetime.utcnow().isoformat(),
                "thread_count": len(tweets),
            }

        except (AuthenticationException, RateLimitException):
            raise
        except Exception as e:
            logger.error(f"Failed to publish Twitter thread: {str(e)}")
            raise PublishingException(f"Failed to publish Twitter thread: {str(e)}")

    @staticmethod
    def _split_into_tweets(content: str, max_length: int = THREAD_TWEET_MAX_LENGTH) -> list:
        """Split long content into multiple tweets"""
        if (
            not isinstance(max_length, int)
            or max_length <= 0
            or max_length > DEFAULT_TWEET_MAX_LENGTH
        ):
            logger.warning(
                f"Invalid max_length {max_length}, using default {THREAD_TWEET_MAX_LENGTH}"
            )
            max_length = THREAD_TWEET_MAX_LENGTH

        words = content.split()
        tweets = []
        current_parts = []

        for word in words:
            test_tweet = " ".join(current_parts + [word])
            if len(test_tweet) <= max_length:
                current_parts.append(word)
            else:
                if current_parts:
                    tweets.append(" ".join(current_parts))
                current_parts = [word]

        if current_parts:
            tweets.append(" ".join(current_parts))

        return tweets

    async def validate_token(self, access_token: str) -> bool:
        """
        Validate Twitter access token by making a test API call.

        Args:
            access_token: OAuth access token to validate

        Returns:
            True if token is valid, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/users/me", headers={"Authorization": f"Bearer {access_token}"}
                )
                return response.status_code == 200
        except Exception:
            return False
