"""
Instagram Publishing Endpoint

This module extends posts.py with Instagram-specific publishing functionality.
Integrates with the Instagram OAuth system and InstagramPublisher.

Import and include in main.py:
```python
from api.posts_instagram_publish import router as instagram_publish_router
app.include_router(instagram_publish_router, prefix="/api/posts", tags=["posts"])
```
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import logging

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from database import get_db, Post, User
from database_social_media import SocialMediaConnection, SocialMediaPost
from src.publishers.instagram_publisher import InstagramPublisher
from src.publishers.exceptions import AuthenticationException, RateLimitException, PublishingException
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.social_connection_manager import SocialConnectionManager

router = APIRouter()
logger = logging.getLogger(__name__)


class InstagramPublishRequest(BaseModel):
    """Request model for Instagram publishing"""
    post_id: int


@router.post("/{post_id}/publish/instagram")
async def publish_to_instagram(
    post_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Publish post to Instagram.

    Requirements:
    - User has Instagram Business Account connected
    - Post has Instagram image URL and caption
    - Image must be publicly accessible via HTTPS

    Flow:
    1. Verify post belongs to user
    2. Check Instagram content exists
    3. Get Instagram OAuth connection
    4. Create media container on Instagram
    5. Wait for Instagram to process image
    6. Publish container
    7. Update post with Instagram URL

    Args:
        post_id: Post ID to publish
        user: Current authenticated user
        db: Database session

    Returns:
        {
            "success": true,
            "platform": "instagram",
            "message": "Published to Instagram",
            "platform_url": "https://www.instagram.com/p/...",
            "platform_post_id": "...",
            "published_at": "..."
        }

    Raises:
        HTTPException 404: Post not found
        HTTPException 400: Missing Instagram content or not connected
        HTTPException 500: Publishing failed
    """
    try:
        # Get post
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user.id
        ).first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Verify Instagram content exists
        if not post.instagram_image_url:
            raise HTTPException(
                status_code=400,
                detail="Post is missing Instagram image. Please generate an Instagram image first."
            )

        if not post.instagram_caption:
            raise HTTPException(
                status_code=400,
                detail="Post is missing Instagram caption. Please add a caption."
            )

        # Get Instagram connection
        manager = SocialConnectionManager(db)
        connection = manager.get_connection(user.id, "instagram", auto_refresh=True)

        if not connection:
            raise HTTPException(
                status_code=400,
                detail="Instagram not connected. Please connect your Instagram Business Account in Settings."
            )

        # Get decrypted access token (page access token)
        access_token = manager.get_decrypted_token(connection)

        if not access_token:
            raise HTTPException(
                status_code=500,
                detail="Failed to decrypt Instagram access token"
            )

        # Get Instagram account ID from metadata
        instagram_account_id = None
        if connection.platform_metadata:
            instagram_account_id = connection.platform_metadata.get("instagram_account_id")

        if not instagram_account_id:
            instagram_account_id = connection.platform_user_id

        if not instagram_account_id:
            raise HTTPException(
                status_code=400,
                detail="Instagram account ID not found. Please reconnect your Instagram account."
            )

        # Build full image URL
        image_url = post.instagram_image_url
        if not image_url.startswith("http"):
            # If relative URL, build absolute URL
            # You'll need to configure your domain
            base_url = os.getenv("APP_URL", "http://localhost:8000")
            image_url = f"{base_url}{image_url}"

        # Ensure image URL is HTTPS (Instagram requirement)
        if not image_url.startswith("https://"):
            raise HTTPException(
                status_code=400,
                detail="Instagram requires HTTPS image URLs. Please configure SSL or use a CDN."
            )

        # Initialize publisher
        publisher = InstagramPublisher()

        # Prepare caption with hashtags
        caption = post.instagram_caption
        if post.instagram_hashtags:
            # Parse hashtags (stored as JSON string)
            import json
            try:
                hashtags = json.loads(post.instagram_hashtags) if isinstance(post.instagram_hashtags, str) else post.instagram_hashtags
                if hashtags:
                    caption += "\n\n" + " ".join([f"#{tag}" for tag in hashtags])
            except:
                pass

        # Publish to Instagram (2-step process)
        try:
            result = await publisher.publish(
                image_url=image_url,
                caption=caption,
                instagram_account_id=instagram_account_id,
                access_token=access_token
            )

            if result["success"]:
                # Create social media post record
                social_post = SocialMediaPost(
                    post_id=post.id,
                    user_id=user.id,
                    connection_id=connection.id,
                    platform="instagram",
                    content=caption,
                    status="published",
                    platform_post_id=result.get("platform_post_id"),
                    platform_url=result.get("platform_url"),
                    published_at=datetime.utcnow(),
                    post_metadata={
                        "image_url": image_url,
                        "container_id": result.get("container_id")
                    }
                )
                db.add(social_post)

                # Update post with Instagram URL
                post.instagram_url = result.get("platform_url")
                post.instagram_post_id = result.get("platform_post_id")

                # Update post status
                post.status = "published" if post.status == "draft" else post.status
                post.published_at = datetime.utcnow()

                db.commit()

                logger.info(f"Published post {post_id} to Instagram for user {user.id}")

                return {
                    "success": True,
                    "platform": "instagram",
                    "message": "Published to Instagram",
                    "platform_url": result.get("platform_url"),
                    "platform_post_id": result.get("platform_post_id"),
                    "published_at": result.get("published_at")
                }
            else:
                raise PublishingException("Instagram publish returned unsuccessful status")

        except AuthenticationException as e:
            logger.error(f"Instagram authentication error: {str(e)}")

            # Create failed social media post record
            social_post = SocialMediaPost(
                post_id=post.id,
                user_id=user.id,
                connection_id=connection.id,
                platform="instagram",
                content=caption,
                status="failed",
                error_message=f"Authentication error: {str(e)}",
                created_at=datetime.utcnow()
            )
            db.add(social_post)
            db.commit()

            raise HTTPException(
                status_code=401,
                detail=f"Instagram authentication failed: {str(e)}. Please reconnect your Instagram account."
            )

        except RateLimitException as e:
            logger.error(f"Instagram rate limit exceeded: {str(e)}")

            # Create failed social media post record
            social_post = SocialMediaPost(
                post_id=post.id,
                user_id=user.id,
                connection_id=connection.id,
                platform="instagram",
                content=caption,
                status="failed",
                error_message=f"Rate limit exceeded: {str(e)}",
                created_at=datetime.utcnow()
            )
            db.add(social_post)
            db.commit()

            raise HTTPException(
                status_code=429,
                detail=f"Instagram rate limit exceeded: {str(e)}. Please try again later."
            )

        except PublishingException as e:
            logger.error(f"Instagram publishing error: {str(e)}")

            # Create failed social media post record
            social_post = SocialMediaPost(
                post_id=post.id,
                user_id=user.id,
                connection_id=connection.id,
                platform="instagram",
                content=caption,
                status="failed",
                error_message=str(e),
                created_at=datetime.utcnow()
            )
            db.add(social_post)
            db.commit()

            raise HTTPException(
                status_code=500,
                detail=f"Failed to publish to Instagram: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing to Instagram: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while publishing to Instagram: {str(e)}"
        )


@router.post("/{post_id}/instagram/validate")
async def validate_instagram_publish(
    post_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Validate post is ready for Instagram publishing.

    Checks:
    - Post exists
    - Instagram image URL exists
    - Instagram caption exists
    - Image URL is HTTPS
    - User has Instagram connected
    - Token is valid

    Args:
        post_id: Post ID to validate
        user: Current authenticated user
        db: Database session

    Returns:
        {
            "ready": true,
            "checks": {
                "post_exists": true,
                "has_image": true,
                "has_caption": true,
                "https_url": true,
                "instagram_connected": true,
                "token_valid": true
            },
            "errors": []
        }
    """
    try:
        checks = {
            "post_exists": False,
            "has_image": False,
            "has_caption": False,
            "https_url": False,
            "instagram_connected": False,
            "token_valid": False
        }
        errors = []

        # Check post exists
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user.id
        ).first()

        if post:
            checks["post_exists"] = True

            # Check image exists
            if post.instagram_image_url:
                checks["has_image"] = True

                # Check HTTPS
                image_url = post.instagram_image_url
                if not image_url.startswith("http"):
                    base_url = os.getenv("APP_URL", "http://localhost:8000")
                    image_url = f"{base_url}{image_url}"

                if image_url.startswith("https://"):
                    checks["https_url"] = True
                else:
                    errors.append("Image URL must be HTTPS for Instagram")
            else:
                errors.append("Post is missing Instagram image")

            # Check caption exists
            if post.instagram_caption:
                checks["has_caption"] = True
            else:
                errors.append("Post is missing Instagram caption")
        else:
            errors.append("Post not found")

        # Check Instagram connection
        manager = SocialConnectionManager(db)
        connection = manager.get_connection(user.id, "instagram", auto_refresh=False)

        if connection:
            checks["instagram_connected"] = True

            # Validate token
            access_token = manager.get_decrypted_token(connection)
            if access_token:
                instagram_account_id = None
                if connection.platform_metadata:
                    instagram_account_id = connection.platform_metadata.get("instagram_account_id")
                if not instagram_account_id:
                    instagram_account_id = connection.platform_user_id

                if instagram_account_id:
                    publisher = InstagramPublisher()
                    is_valid = await publisher.validate_token(instagram_account_id, access_token)
                    if is_valid:
                        checks["token_valid"] = True
                    else:
                        errors.append("Instagram token is invalid. Please reconnect.")
                else:
                    errors.append("Instagram account ID not found")
            else:
                errors.append("Failed to decrypt Instagram token")
        else:
            errors.append("Instagram not connected")

        ready = all(checks.values())

        return {
            "ready": ready,
            "checks": checks,
            "errors": errors if errors else None
        }

    except Exception as e:
        logger.error(f"Error validating Instagram publish: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error validating Instagram publish: {str(e)}"
        )


import os
