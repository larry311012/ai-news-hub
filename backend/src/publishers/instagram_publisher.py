"""
Instagram Publisher - Publish images with captions to Instagram Business accounts

Instagram publishing uses a 2-step process via Facebook Graph API:
1. Create media container with image URL and caption
2. Publish the container after Instagram processes the image

Requirements:
- Instagram Business Account (not personal)
- Image must be publicly accessible via HTTPS
- Caption max 2,200 characters
- Supported formats: JPG, PNG
- Max file size: 8 MB
- Aspect ratio: 4:5 to 1.91:1

API Documentation:
- https://developers.facebook.com/docs/instagram-api/guides/content-publishing
"""

import httpx
import time
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from .exceptions import AuthenticationException, RateLimitException, PublishingException


class InstagramPublisher:
    """Publishes images with captions to Instagram Business accounts using OAuth"""

    def __init__(self):
        """Initialize Instagram publisher"""
        self.api_base = "https://graph.facebook.com/v18.0"
        self.max_retries = 3
        self.container_wait_time = 10  # Wait 10 seconds for Instagram to process image

    async def publish(
        self,
        image_url: str,
        caption: str,
        instagram_account_id: str,
        access_token: str,
        metadata: dict = None
    ) -> dict:
        """
        Publish an image with caption to Instagram.

        This is a 2-step process:
        1. Create media container (Instagram downloads and processes image)
        2. Publish container (make post live)

        Args:
            image_url: Publicly accessible HTTPS URL of image
            caption: Post caption (max 2,200 characters)
            instagram_account_id: Instagram Business Account ID
            access_token: Page access token (not user token)
            metadata: Optional metadata (location, user tags, etc.)

        Returns:
            {
                "success": True,
                "platform_post_id": "...",
                "platform_url": "https://www.instagram.com/p/...",
                "published_at": "...",
                "container_id": "..."
            }

        Raises:
            AuthenticationException: Token is invalid
            RateLimitException: Rate limit exceeded
            PublishingException: Generic publishing error
        """
        try:
            # Validate image URL
            if not image_url.startswith("https://"):
                raise PublishingException("Image URL must be HTTPS")

            # Truncate caption to 2,200 characters
            if len(caption) > 2200:
                caption = caption[:2200]
                logger.warning(f"Caption truncated to 2,200 characters")

            # Step 1: Create media container
            container_id = await self._create_container(
                image_url=image_url,
                caption=caption,
                instagram_account_id=instagram_account_id,
                access_token=access_token,
                metadata=metadata
            )

            if not container_id:
                raise PublishingException("Failed to create media container")

            # Step 2: Wait for Instagram to process the image
            logger.info(f"Waiting {self.container_wait_time}s for Instagram to process image...")
            await self._wait_for_container_ready(
                container_id=container_id,
                access_token=access_token
            )

            # Step 3: Publish container
            media_id = await self._publish_container(
                container_id=container_id,
                instagram_account_id=instagram_account_id,
                access_token=access_token
            )

            if not media_id:
                raise PublishingException("Failed to publish container")

            # Step 4: Get permalink
            permalink = await self._get_permalink(
                media_id=media_id,
                access_token=access_token
            )

            logger.info(f"Successfully published to Instagram: {media_id}")

            return {
                "success": True,
                "platform_post_id": media_id,
                "platform_url": permalink or f"https://www.instagram.com/p/{media_id}/",
                "published_at": datetime.utcnow().isoformat(),
                "container_id": container_id
            }

        except (AuthenticationException, RateLimitException, PublishingException):
            raise
        except Exception as e:
            logger.error(f"Failed to publish to Instagram: {str(e)}")
            raise PublishingException(f"Failed to publish to Instagram: {str(e)}")

    async def _create_container(
        self,
        image_url: str,
        caption: str,
        instagram_account_id: str,
        access_token: str,
        metadata: dict = None
    ) -> Optional[str]:
        """
        Step 1: Create media container.

        Instagram downloads the image from the URL and processes it.
        This can take 5-30 seconds depending on image size.

        Args:
            image_url: HTTPS URL of image
            caption: Post caption
            instagram_account_id: Instagram Business Account ID
            access_token: Page access token
            metadata: Optional metadata (location, user tags)

        Returns:
            Container ID or None if failed
        """
        try:
            # Build request data
            data = {
                "image_url": image_url,
                "caption": caption,
                "access_token": access_token
            }

            # Add optional metadata
            if metadata:
                # Location tagging
                if "location_id" in metadata:
                    data["location_id"] = metadata["location_id"]

                # User tagging
                if "user_tags" in metadata:
                    data["user_tags"] = metadata["user_tags"]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/{instagram_account_id}/media",
                    data=data,
                    timeout=60.0  # Longer timeout for image download
                )

                if response.status_code == 200:
                    result = response.json()
                    container_id = result.get("id")
                    logger.info(f"Created Instagram container: {container_id}")
                    return container_id
                elif response.status_code == 401:
                    raise AuthenticationException("Instagram token invalid or expired")
                elif response.status_code == 429:
                    raise RateLimitException("Instagram rate limit exceeded", 3600)
                else:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(f"Failed to create container: {error_msg}")
                    raise PublishingException(f"Container creation failed: {error_msg}")

        except (AuthenticationException, RateLimitException, PublishingException):
            raise
        except Exception as e:
            logger.error(f"Error creating container: {str(e)}")
            raise PublishingException(f"Container creation error: {str(e)}")

    async def _wait_for_container_ready(
        self,
        container_id: str,
        access_token: str,
        max_wait: int = 60
    ) -> bool:
        """
        Wait for Instagram to finish processing the media container.

        Instagram downloads and processes the image. This can take time.
        We poll the container status until it's ready or timeout.

        Args:
            container_id: Media container ID
            access_token: Access token
            max_wait: Maximum seconds to wait

        Returns:
            True if container is ready, False if timeout/error
        """
        try:
            start_time = time.time()
            wait_interval = 2  # Check every 2 seconds

            while (time.time() - start_time) < max_wait:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.api_base}/{container_id}",
                        params={
                            "fields": "status_code",
                            "access_token": access_token
                        },
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        result = response.json()
                        status = result.get("status_code")

                        if status == "FINISHED":
                            logger.info("Container processing finished")
                            return True
                        elif status == "ERROR":
                            logger.error("Container processing failed")
                            return False
                        elif status == "IN_PROGRESS":
                            logger.debug("Container still processing...")
                            await asyncio.sleep(wait_interval)
                        else:
                            # Unknown status, wait a bit more
                            await asyncio.sleep(wait_interval)
                    else:
                        # Can't check status, proceed anyway
                        logger.warning("Can't check container status, proceeding...")
                        await asyncio.sleep(self.container_wait_time)
                        return True

            # Timeout reached, proceed anyway
            logger.warning(f"Container status check timeout after {max_wait}s, proceeding...")
            return True

        except Exception as e:
            logger.warning(f"Error checking container status: {str(e)}, proceeding anyway...")
            await asyncio.sleep(self.container_wait_time)
            return True

    async def _publish_container(
        self,
        container_id: str,
        instagram_account_id: str,
        access_token: str
    ) -> Optional[str]:
        """
        Step 2: Publish the media container.

        Makes the post live on Instagram.

        Args:
            container_id: Media container ID from creation step
            instagram_account_id: Instagram Business Account ID
            access_token: Page access token

        Returns:
            Media ID (published post ID) or None if failed
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/{instagram_account_id}/media_publish",
                    data={
                        "creation_id": container_id,
                        "access_token": access_token
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    media_id = result.get("id")
                    logger.info(f"Published Instagram media: {media_id}")
                    return media_id
                elif response.status_code == 401:
                    raise AuthenticationException("Instagram token invalid or expired")
                elif response.status_code == 429:
                    raise RateLimitException("Instagram rate limit exceeded", 3600)
                else:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(f"Failed to publish container: {error_msg}")
                    raise PublishingException(f"Container publishing failed: {error_msg}")

        except (AuthenticationException, RateLimitException, PublishingException):
            raise
        except Exception as e:
            logger.error(f"Error publishing container: {str(e)}")
            raise PublishingException(f"Container publishing error: {str(e)}")

    async def _get_permalink(
        self,
        media_id: str,
        access_token: str
    ) -> Optional[str]:
        """
        Get permalink (public URL) for published media.

        Args:
            media_id: Published media ID
            access_token: Access token

        Returns:
            Permalink URL or None if failed
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/{media_id}",
                    params={
                        "fields": "permalink",
                        "access_token": access_token
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("permalink")
                else:
                    logger.warning("Failed to get permalink")
                    return None

        except Exception as e:
            logger.warning(f"Error getting permalink: {str(e)}")
            return None

    async def validate_token(self, instagram_account_id: str, access_token: str) -> bool:
        """
        Validate Instagram access token by making a test API call.

        Args:
            instagram_account_id: Instagram Business Account ID
            access_token: Page access token to validate

        Returns:
            True if token is valid, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/{instagram_account_id}",
                    params={
                        "fields": "id,username",
                        "access_token": access_token
                    },
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception:
            return False

    async def get_media_insights(
        self,
        media_id: str,
        access_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get insights (engagement metrics) for published media.

        Available metrics:
        - engagement: Likes + comments + saves
        - impressions: Total times seen
        - reach: Unique accounts reached
        - saved: Number of saves

        Args:
            media_id: Published media ID
            access_token: Access token

        Returns:
            {
                "engagement": 123,
                "impressions": 456,
                "reach": 234,
                "saved": 12
            }
            Or None if failed
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/{media_id}/insights",
                    params={
                        "metric": "engagement,impressions,reach,saved",
                        "access_token": access_token
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    result = response.json()
                    data = result.get("data", [])

                    insights = {}
                    for item in data:
                        metric_name = item.get("name")
                        values = item.get("values", [])
                        if values:
                            insights[metric_name] = values[0].get("value", 0)

                    return insights
                else:
                    logger.warning("Failed to get media insights")
                    return None

        except Exception as e:
            logger.warning(f"Error getting media insights: {str(e)}")
            return None


# Add asyncio import at top if not already present
import asyncio
