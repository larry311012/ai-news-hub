"""
LinkedIn Publisher - Publish content to LinkedIn using OAuth
"""
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from .exceptions import AuthenticationException, RateLimitException, PublishingException


class LinkedInPublisher:
    """Publishes content to LinkedIn using OAuth"""

    def __init__(self):
        """Initialize LinkedIn publisher"""
        self.api_base = "https://api.linkedin.com/v2"

    async def publish(self, content: str, access_token: str, metadata: dict = None) -> dict:
        """
        Publish content to LinkedIn using OAuth access token.

        Args:
            content: Post content
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
            async with httpx.AsyncClient() as client:
                # Get person ID from OpenID Connect userinfo endpoint
                # This works with the new 'openid' and 'profile' scopes
                profile_response = await client.get(
                    "https://api.linkedin.com/v2/userinfo",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )

                if profile_response.status_code == 401:
                    raise AuthenticationException("LinkedIn token invalid or expired")
                elif profile_response.status_code == 429:
                    retry_after = profile_response.headers.get("retry-after", 3600)
                    raise RateLimitException("LinkedIn rate limit exceeded", retry_after)

                profile_response.raise_for_status()
                # OpenID Connect returns 'sub' which is the LinkedIn member ID
                person_id = profile_response.json()["sub"]

                # Create post
                post_data = {
                    "author": f"urn:li:person:{person_id}",
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": content},
                            "shareMediaCategory": "NONE",
                        }
                    },
                    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
                }

                response = await client.post(
                    f"{self.api_base}/ugcPosts",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                    json=post_data,
                )

                if response.status_code == 401:
                    raise AuthenticationException("LinkedIn token invalid or expired")
                elif response.status_code == 429:
                    retry_after = response.headers.get("retry-after", 3600)
                    raise RateLimitException("LinkedIn rate limit exceeded", retry_after)

                response.raise_for_status()
                result = response.json()

                post_id = result.get("id", "")

                logger.info(f"Successfully published to LinkedIn: {post_id}")

                return {
                    "success": True,
                    "platform_post_id": post_id,
                    "platform_url": f"https://www.linkedin.com/feed/update/{post_id}/",
                    "published_at": datetime.utcnow().isoformat(),
                }

        except (AuthenticationException, RateLimitException):
            raise
        except Exception as e:
            logger.error(f"Failed to publish to LinkedIn: {str(e)}")
            raise PublishingException(f"Failed to publish to LinkedIn: {str(e)}")

    async def validate_token(self, access_token: str) -> bool:
        """
        Validate LinkedIn access token by making a test API call.

        Args:
            access_token: OAuth access token to validate

        Returns:
            True if token is valid, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                # Use OpenID Connect userinfo endpoint for validation
                response = await client.get(
                    "https://api.linkedin.com/v2/userinfo",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )
                return response.status_code == 200
        except Exception:
            return False
