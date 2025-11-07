"""
Threads Publisher - Publish content to Threads (Meta) using OAuth
"""
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from .exceptions import AuthenticationException, RateLimitException, PublishingException


class ThreadsPublisher:
    """Publishes content to Threads (Meta) platform using OAuth"""

    def __init__(self):
        """Initialize Threads publisher"""
        self.api_base = "https://graph.threads.net/v1.0"

    async def publish(self, content: str, access_token: str, metadata: dict = None) -> dict:
        """
        Publish content to Threads using OAuth access token.

        Threads publishing is a 2-step process:
        1. Create media container
        2. Publish container

        Args:
            content: Post content (max 500 characters)
            access_token: OAuth access token (decrypted)
            metadata: Optional metadata (images, links, etc.)

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
            # Truncate content to 500 characters
            truncated_content = content[:500]

            async with httpx.AsyncClient() as client:
                # Step 1: Get user ID
                me_response = await client.get(
                    f"{self.api_base}/me",
                    params={"fields": "id,username", "access_token": access_token},
                )

                if me_response.status_code == 401:
                    raise AuthenticationException("Threads token invalid or expired")
                elif me_response.status_code == 429:
                    raise RateLimitException("Threads rate limit exceeded", 3600)

                me_response.raise_for_status()
                user_data = me_response.json()
                user_id = user_data["id"]
                username = user_data.get("username", "unknown")

                # Step 2: Create media container
                container_response = await client.post(
                    f"{self.api_base}/{user_id}/threads",
                    data={
                        "media_type": "TEXT",
                        "text": truncated_content,
                        "access_token": access_token,
                    },
                )

                if container_response.status_code == 401:
                    raise AuthenticationException("Threads token invalid or expired")
                elif container_response.status_code == 429:
                    raise RateLimitException("Threads rate limit exceeded", 3600)

                container_response.raise_for_status()
                container_id = container_response.json()["id"]

                # Step 3: Publish container
                publish_response = await client.post(
                    f"{self.api_base}/{user_id}/threads_publish",
                    data={"creation_id": container_id, "access_token": access_token},
                )

                if publish_response.status_code == 401:
                    raise AuthenticationException("Threads token invalid or expired")
                elif publish_response.status_code == 429:
                    raise RateLimitException("Threads rate limit exceeded", 3600)

                publish_response.raise_for_status()
                thread_id = publish_response.json()["id"]

                logger.info(f"Successfully published to Threads: {thread_id}")

                return {
                    "success": True,
                    "platform_post_id": thread_id,
                    "platform_url": f"https://www.threads.net/@{username}/post/{thread_id}",
                    "published_at": datetime.utcnow().isoformat(),
                }

        except (AuthenticationException, RateLimitException):
            raise
        except Exception as e:
            logger.error(f"Failed to publish to Threads: {str(e)}")
            raise PublishingException(f"Failed to publish to Threads: {str(e)}")

    async def validate_token(self, access_token: str) -> bool:
        """
        Validate Threads access token by making a test API call.

        Args:
            access_token: OAuth access token to validate

        Returns:
            True if token is valid, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/me", params={"fields": "id", "access_token": access_token}
                )
                return response.status_code == 200
        except Exception:
            return False
