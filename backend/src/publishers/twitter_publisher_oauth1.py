"""
Twitter Publisher with OAuth 1.0a Support

This publisher supports both OAuth 2.0 (Bearer tokens) and OAuth 1.0a (signed requests).
It automatically detects which authentication method to use based on the tokens provided.

OAuth 2.0: Uses Bearer token in Authorization header
OAuth 1.0a: Uses OAuth signatures with consumer key + user tokens
"""

import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from .exceptions import AuthenticationException, RateLimitException, PublishingException

# Constants
DEFAULT_TWEET_MAX_LENGTH = 280
THREAD_TWEET_MAX_LENGTH = 270


class TwitterPublisherOAuth1:
    """
    Publishes content to Twitter using OAuth 1.0a authentication.

    This publisher uses centralized app credentials (API Key + Secret)
    and per-user access tokens to publish tweets on behalf of users.
    """

    def __init__(self):
        """Initialize Twitter publisher with OAuth 1.0a support"""
        self.api_base_v1 = "https://api.twitter.com/1.1"
        self.api_base_v2 = "https://api.twitter.com/2"

    async def publish(
        self, content: str, access_token: str, access_token_secret: str, metadata: dict = None, user_id: int = None
    ) -> dict:
        """
        Publish tweet to Twitter using OAuth 1.0a.

        Args:
            content: Tweet content (max 280 characters)
            access_token: User's OAuth 1.0a access token
            access_token_secret: User's OAuth 1.0a access token secret
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
            # Import OAuth 1.0a utilities
            from utils.twitter_oauth1 import generate_api_auth_header, get_twitter_credentials

            # Truncate content to 280 characters
            truncated_content = content[:DEFAULT_TWEET_MAX_LENGTH]

            # Use Twitter API v2 for posting (better features)
            endpoint_url = f"{self.api_base_v2}/tweets"
            method = "POST"
            post_data = {"text": truncated_content}

            # Get consumer keys from USER's credentials if user_id provided
            if user_id:
                from database import SessionLocal
                from utils.user_oauth_credential_manager import UserOAuthCredentialManager
                db = SessionLocal()
                try:
                    manager = UserOAuthCredentialManager(db, user_id)
                    user_creds = manager.get_credentials("twitter")
                    consumer_key = user_creds.get("api_key") if user_creds else None
                    consumer_secret = user_creds.get("api_secret") if user_creds else None
                    logger.info(f"Using user {user_id}'s Twitter credentials for publishing")
                finally:
                    db.close()
            else:
                # Fallback to admin credentials
                from utils.twitter_oauth1 import get_twitter_credentials
                creds = get_twitter_credentials()
                consumer_key = creds.get("api_key")
                consumer_secret = creds.get("api_secret")

            # Generate OAuth 1.0a signature
            auth_header = generate_api_auth_header(
                method=method,
                url=endpoint_url,
                access_token=access_token,
                access_token_secret=access_token_secret,
                params=None,  # POST body is not included in signature for JSON requests
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint_url,
                    headers={"Authorization": auth_header, "Content-Type": "application/json"},
                    json=post_data,
                )

                if response.status_code == 401:
                    raise AuthenticationException("Twitter OAuth 1.0a token invalid or expired")
                elif response.status_code == 403:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "Permission denied")
                    raise AuthenticationException(f"Twitter API permission denied: {error_detail}")
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

                logger.info(f"Successfully published to Twitter (OAuth 1.0a): {tweet_id}")

                return {
                    "success": True,
                    "platform_post_id": tweet_id,
                    "platform_url": f"https://twitter.com/i/status/{tweet_id}",
                    "published_at": datetime.utcnow().isoformat(),
                    "auth_method": "OAuth 1.0a",
                }

        except (AuthenticationException, RateLimitException):
            raise
        except Exception as e:
            logger.error(f"Failed to publish to Twitter (OAuth 1.0a): {str(e)}")
            raise PublishingException(f"Failed to publish to Twitter: {str(e)}")

    async def publish_thread(
        self, content: str, access_token: str, access_token_secret: str
    ) -> dict:
        """
        Publish content as a Twitter thread if it exceeds character limit.

        Args:
            content: Long content to split into thread
            access_token: User's OAuth 1.0a access token
            access_token_secret: User's OAuth 1.0a access token secret

        Returns:
            Publishing result with first tweet info
        """
        try:
            from utils.twitter_oauth1 import generate_api_auth_header

            tweets = self._split_into_tweets(content)
            previous_tweet_id = None
            first_tweet_id = None

            endpoint_url = f"{self.api_base_v2}/tweets"
            method = "POST"

            async with httpx.AsyncClient() as client:
                for i, tweet in enumerate(tweets, 1):
                    tweet_data = {"text": tweet}
                    if previous_tweet_id:
                        tweet_data["reply"] = {"in_reply_to_tweet_id": previous_tweet_id}

                    # Generate OAuth signature for this specific request
                    auth_header = generate_api_auth_header(
                        method=method,
                        url=endpoint_url,
                        access_token=access_token,
                        access_token_secret=access_token_secret,
                        params=None,
                    )

                    response = await client.post(
                        endpoint_url,
                        headers={"Authorization": auth_header, "Content-Type": "application/json"},
                        json=tweet_data,
                    )

                    if response.status_code == 401:
                        raise AuthenticationException("Twitter OAuth 1.0a token invalid or expired")
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
                    logger.info(f"Published tweet {i}/{len(tweets)} (OAuth 1.0a): {tweet_id}")

            return {
                "success": True,
                "platform_post_id": first_tweet_id,
                "platform_url": f"https://twitter.com/i/status/{first_tweet_id}",
                "published_at": datetime.utcnow().isoformat(),
                "thread_count": len(tweets),
                "auth_method": "OAuth 1.0a",
            }

        except (AuthenticationException, RateLimitException):
            raise
        except Exception as e:
            logger.error(f"Failed to publish Twitter thread (OAuth 1.0a): {str(e)}")
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

        # Handle empty content
        if not content:
            return [""]

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

    async def validate_token(self, access_token: str, access_token_secret: str) -> bool:
        """
        Validate Twitter OAuth 1.0a credentials by making a test API call.

        Args:
            access_token: User's OAuth 1.0a access token
            access_token_secret: User's OAuth 1.0a access token secret

        Returns:
            True if token is valid, False otherwise
        """
        try:
            from utils.twitter_oauth1 import validate_credentials

            return await validate_credentials(access_token, access_token_secret)
        except Exception:
            return False


class TwitterPublisherUnified:
    """
    Unified Twitter publisher that supports both OAuth 2.0 and OAuth 1.0a.

    Automatically detects which authentication method to use based on
    the number of tokens provided:
    - 1 token (access_token only): OAuth 2.0 Bearer token
    - 2 tokens (access_token + access_token_secret): OAuth 1.0a
    """

    def __init__(self):
        """Initialize unified Twitter publisher"""
        self.api_base_v2 = "https://api.twitter.com/2"
        self.oauth2_publisher = None  # Lazy import
        self.oauth1_publisher = TwitterPublisherOAuth1()

    async def publish(
        self,
        content: str,
        access_token: str,
        access_token_secret: Optional[str] = None,
        metadata: dict = None,
        user_id: int = None,
    ) -> dict:
        """
        Publish tweet to Twitter using appropriate OAuth method.

        Args:
            content: Tweet content
            access_token: OAuth access token (2.0 or 1.0a)
            access_token_secret: OAuth 1.0a access token secret (optional)
            metadata: Optional metadata

        Returns:
            Publishing result
        """
        if access_token_secret:
            # OAuth 1.0a: We have both access_token and access_token_secret
            logger.info("Using OAuth 1.0a for Twitter publishing")
            return await self.oauth1_publisher.publish(
                content=content,
                access_token=access_token,
                access_token_secret=access_token_secret,
                metadata=metadata,
                user_id=user_id,
            )
        else:
            # OAuth 2.0: We only have access_token (Bearer token)
            logger.info("Using OAuth 2.0 for Twitter publishing")
            # Lazy import to avoid circular dependency
            if self.oauth2_publisher is None:
                from .twitter_publisher import TwitterPublisher

                self.oauth2_publisher = TwitterPublisher()

            return await self.oauth2_publisher.publish(
                content=content, access_token=access_token, metadata=metadata
            )

    async def publish_thread(
        self, content: str, access_token: str, access_token_secret: Optional[str] = None
    ) -> dict:
        """
        Publish Twitter thread using appropriate OAuth method.

        Args:
            content: Long content to split into thread
            access_token: OAuth access token
            access_token_secret: OAuth 1.0a access token secret (optional)

        Returns:
            Publishing result
        """
        if access_token_secret:
            logger.info("Using OAuth 1.0a for Twitter thread publishing")
            return await self.oauth1_publisher.publish_thread(
                content=content, access_token=access_token, access_token_secret=access_token_secret
            )
        else:
            logger.info("Using OAuth 2.0 for Twitter thread publishing")
            if self.oauth2_publisher is None:
                from .twitter_publisher import TwitterPublisher

                self.oauth2_publisher = TwitterPublisher()

            return await self.oauth2_publisher.publish_thread(
                content=content, access_token=access_token
            )
