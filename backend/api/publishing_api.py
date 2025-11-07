"""
Publishing API Endpoints (Phase 4 - Task 4.1, 4.2, 4.3)

API endpoints for multi-platform social media publishing with:
- Single platform publishing
- Multi-platform batch publishing
- Publishing history tracking
- Status checking
- Retry mechanism
- Error handling

All endpoints are iOS-optimized with mobile-friendly responses.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from database import get_db, Post, User
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.error_responses import (
    ErrorCode,
    create_error_response,
    create_error_exception
)
from services.publishing_service import PublishingService
from middleware.rate_limiting import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class PublishToPlatformRequest(BaseModel):
    """Request to publish to a single platform"""
    content: Optional[str] = Field(None, max_length=10000, description="Override post content")
    media_urls: Optional[List[str]] = Field(None, max_items=10, description="Media URLs to publish")

    @field_validator("media_urls")
    @classmethod
    def validate_media_urls(cls, v):
        """Validate media URLs"""
        if v:
            for url in v:
                if not url.startswith(("http://", "https://")):
                    raise ValueError(f"Invalid media URL: {url}")
        return v


class PublishToMultipleRequest(BaseModel):
    """Request to publish to multiple platforms"""
    platforms: List[str] = Field(..., min_items=1, max_items=4, description="Platforms to publish to")
    content_map: Optional[Dict[str, str]] = Field(
        None,
        description="Platform-specific content overrides"
    )

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v):
        """Validate platform names"""
        valid_platforms = {"twitter", "linkedin", "instagram", "threads"}
        for platform in v:
            if platform not in valid_platforms:
                raise ValueError(f"Invalid platform: {platform}")
        return v


class PublishResponse(BaseModel):
    """Response from publishing operation"""
    success: bool
    platform: str
    status: str  # success, failed, rate_limited, retrying
    platform_url: Optional[str] = None
    platform_post_id: Optional[str] = None
    published_at: Optional[str] = None
    error: Optional[str] = None
    error_category: Optional[str] = None
    retry_scheduled: bool = False
    next_retry_at: Optional[str] = None


class MultiPublishResponse(BaseModel):
    """Response from multi-platform publishing"""
    post_id: int
    results: Dict[str, Any]
    summary: Dict[str, int]


class PublishingHistoryItem(BaseModel):
    """Publishing history item"""
    id: int
    post_id: int
    platform: str
    status: str
    platform_post_id: Optional[str]
    platform_url: Optional[str]
    error_category: Optional[str]
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    next_retry_at: Optional[str]
    created_at: str
    published_at: Optional[str]


class PublishingHistoryResponse(BaseModel):
    """Response with publishing history"""
    total: int
    limit: int
    offset: int
    items: List[PublishingHistoryItem]


# ============================================================================
# Publishing Endpoints
# ============================================================================


@router.post("/{platform}/publish", response_model=PublishResponse)
@limiter.limit("50/hour")  # Rate limit: 50 requests per hour per user
async def publish_to_single_platform(
    platform: str,
    request: Request,
    publish_req: PublishToPlatformRequest,
    post_id: int = None,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Publish a post to a single platform.

    **Supported Platforms:**
    - twitter
    - linkedin
    - instagram
    - threads

    **Rate Limit:** 50 requests per hour per user

    **iOS Integration:**
    ```swift
    let request = PublishToPlatformRequest(
        content: customContent,  // Optional override
        media_urls: ["https://..."]  // Optional media
    )

    let response = await api.post(
        "/api/social-media/twitter/publish?post_id=123",
        body: request
    )

    if response.success {
        print("Published: \\(response.platform_url)")
    }
    ```

    Args:
        platform: Platform name (twitter, linkedin, instagram, threads)
        request: FastAPI request
        publish_req: Publishing request data
        post_id: Post ID to publish (query parameter)
        user: Current authenticated user
        db: Database session

    Returns:
        Publishing result with status and URLs

    Raises:
        400: Invalid post_id or platform
        401: Not authenticated
        404: Post not found
        429: Rate limit exceeded
        500: Publishing error
    """
    try:
        # Validate post_id
        if not post_id:
            raise create_error_exception(
                code=ErrorCode.VALIDATION_MISSING_FIELD,
                message="post_id query parameter is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Validate platform
        valid_platforms = ["twitter", "linkedin", "instagram", "threads"]
        if platform not in valid_platforms:
            raise create_error_exception(
                code=ErrorCode.VALIDATION_INVALID_INPUT,
                message=f"Invalid platform: {platform}. Must be one of {', '.join(valid_platforms)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Get post
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user.id
        ).first()

        if not post:
            raise create_error_exception(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Post not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Get content (use provided or from post)
        content = publish_req.content
        if not content:
            # Get platform-specific content from post
            content_map = {
                "twitter": post.twitter_content,
                "linkedin": post.linkedin_content,
                "instagram": post.instagram_caption,
                "threads": post.threads_content
            }
            content = content_map.get(platform)

        if not content:
            raise create_error_exception(
                code=ErrorCode.VALIDATION_INVALID_INPUT,
                message=f"No content available for {platform}. Generate content first.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Get media URLs
        media_urls = publish_req.media_urls
        if not media_urls and platform == "instagram":
            # Instagram requires image
            if post.instagram_image_url:
                media_urls = [post.instagram_image_url]
            else:
                raise create_error_exception(
                    code=ErrorCode.VALIDATION_INVALID_INPUT,
                    message="Instagram requires an image. Generate Instagram image first.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        # Initialize publishing service
        publishing_service = PublishingService(db)

        # Publish
        result = await publishing_service.publish_to_platform(
            post_id=post_id,
            user_id=user.id,
            platform=platform,
            content=content,
            media_urls=media_urls
        )

        logger.info(f"Published post {post_id} to {platform} for user {user.id}: {result['status']}")

        return PublishResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in publish_to_single_platform: {str(e)}", exc_info=True)
        raise create_error_exception(
            code=ErrorCode.SERVER_INTERNAL_ERROR,
            message=f"Failed to publish: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/{post_id}/publish", response_model=MultiPublishResponse)
@limiter.limit("30/hour")  # Rate limit: 30 multi-publish requests per hour
async def publish_to_multiple_platforms(
    post_id: int,
    request: Request,
    publish_req: PublishToMultipleRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Publish a post to multiple platforms simultaneously.

    **Rate Limit:** 30 requests per hour per user

    **iOS Integration:**
    ```swift
    let request = PublishToMultipleRequest(
        platforms: ["twitter", "linkedin", "instagram"],
        content_map: [
            "twitter": "Short tweet",
            "linkedin": "Longer professional post",
            "instagram": "Visual caption"
        ]
    )

    let response = await api.post(
        "/api/posts/123/publish",
        body: request
    )

    print("Published to \\(response.summary.successful) platforms")
    ```

    Args:
        post_id: Post ID to publish
        request: FastAPI request
        publish_req: Publishing request with platforms
        user: Current authenticated user
        db: Database session

    Returns:
        {
            "post_id": 123,
            "results": {
                "twitter": { "success": true, ... },
                "linkedin": { "success": false, ... }
            },
            "summary": {
                "total": 2,
                "successful": 1,
                "failed": 1,
                "rate_limited": 0
            }
        }

    Raises:
        400: Invalid request
        401: Not authenticated
        404: Post not found
        429: Rate limit exceeded
    """
    try:
        # Get post
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user.id
        ).first()

        if not post:
            raise create_error_exception(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Post not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Initialize publishing service
        publishing_service = PublishingService(db)

        # Publish to multiple platforms
        result = await publishing_service.publish_to_multiple(
            post_id=post_id,
            user_id=user.id,
            platforms=publish_req.platforms,
            content_map=publish_req.content_map
        )

        logger.info(
            f"Multi-publish post {post_id} to {len(publish_req.platforms)} platforms: "
            f"{result['summary']['successful']} succeeded, {result['summary']['failed']} failed"
        )

        return MultiPublishResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in publish_to_multiple_platforms: {str(e)}", exc_info=True)
        raise create_error_exception(
            code=ErrorCode.SERVER_INTERNAL_ERROR,
            message=f"Failed to publish: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# History and Status Endpoints
# ============================================================================


@router.get("/history", response_model=PublishingHistoryResponse)
@limiter.limit("100/minute")
async def get_publishing_history(
    request: Request,
    post_id: Optional[int] = None,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get publishing history with optional filters.

    **iOS Integration:**
    ```swift
    // Get all history
    let history = await api.get("/api/publishing/history")

    // Filter by post
    let postHistory = await api.get(
        "/api/publishing/history?post_id=123"
    )

    // Filter by platform
    let twitterHistory = await api.get(
        "/api/publishing/history?platform=twitter&limit=20"
    )
    ```

    Args:
        request: FastAPI request
        post_id: Optional filter by post ID
        platform: Optional filter by platform
        status: Optional filter by status
        limit: Maximum results (1-100, default 50)
        offset: Pagination offset
        user: Current authenticated user
        db: Database session

    Returns:
        Paginated list of publishing history

    Raises:
        400: Invalid filters
        401: Not authenticated
    """
    try:
        # Validate limit
        if limit < 1 or limit > 100:
            raise create_error_exception(
                code=ErrorCode.VALIDATION_INVALID_INPUT,
                message="limit must be between 1 and 100",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Initialize publishing service
        publishing_service = PublishingService(db)

        # Get history
        result = publishing_service.get_publishing_history(
            user_id=user.id,
            post_id=post_id,
            platform=platform,
            status=status,
            limit=limit,
            offset=offset
        )

        return PublishingHistoryResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting publishing history: {str(e)}", exc_info=True)
        raise create_error_exception(
            code=ErrorCode.SERVER_INTERNAL_ERROR,
            message=f"Failed to get history: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/status/{publish_id}", response_model=PublishingHistoryItem)
@limiter.limit("200/minute")
async def get_publishing_status(
    publish_id: int,
    request: Request,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get status of a specific publishing attempt.

    **iOS Integration:**
    ```swift
    // Poll for publishing status
    let status = await api.get("/api/publishing/status/456")

    if status.status == "success" {
        showSuccess(url: status.platform_url)
    } else if status.status == "failed" {
        showError(status.error_message)
    }
    ```

    Args:
        publish_id: Publishing history ID
        request: FastAPI request
        user: Current authenticated user
        db: Database session

    Returns:
        Publishing history details

    Raises:
        404: Publishing record not found
        401: Not authenticated
    """
    try:
        # Initialize publishing service
        publishing_service = PublishingService(db)

        # Get status
        result = publishing_service.get_publishing_status(
            publish_id=publish_id,
            user_id=user.id
        )

        if not result:
            raise create_error_exception(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Publishing record not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return PublishingHistoryItem(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting publishing status: {str(e)}", exc_info=True)
        raise create_error_exception(
            code=ErrorCode.SERVER_INTERNAL_ERROR,
            message=f"Failed to get status: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/retry/{publish_id}", response_model=PublishResponse)
@limiter.limit("20/hour")  # Rate limit: 20 retries per hour
async def retry_failed_publish(
    publish_id: int,
    request: Request,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Retry a failed publishing attempt.

    **Rate Limit:** 20 retries per hour per user

    **iOS Integration:**
    ```swift
    // Retry failed publish
    let result = await api.post("/api/publishing/retry/456")

    if result.success {
        print("Retry successful!")
    } else if result.error_category == "rate_limited" {
        print("Rate limited, retry at: \\(result.next_retry_at)")
    }
    ```

    Args:
        publish_id: Publishing history ID to retry
        request: FastAPI request
        user: Current authenticated user
        db: Database session

    Returns:
        New publishing result

    Raises:
        404: Publishing record not found
        400: Already published or max retries exceeded
        401: Not authenticated
        429: Rate limit exceeded
    """
    try:
        # Initialize publishing service
        publishing_service = PublishingService(db)

        # Retry publish
        result = await publishing_service.retry_failed_publish(
            publish_id=publish_id,
            user_id=user.id
        )

        if not result.get("success") and "error" in result:
            # Check error type
            error_msg = result["error"]

            if "not found" in error_msg.lower():
                raise create_error_exception(
                    code=ErrorCode.RESOURCE_NOT_FOUND,
                    message=error_msg,
                    status_code=status.HTTP_404_NOT_FOUND
                )
            else:
                raise create_error_exception(
                    code=ErrorCode.VALIDATION_INVALID_INPUT,
                    message=error_msg,
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        return PublishResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying publish: {str(e)}", exc_info=True)
        raise create_error_exception(
            code=ErrorCode.SERVER_INTERNAL_ERROR,
            message=f"Failed to retry: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# Connection Management Endpoints
# ============================================================================


@router.delete("/{platform}/disconnect")
@limiter.limit("10/hour")
async def disconnect_platform(
    platform: str,
    request: Request,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Disconnect a social media platform.

    **iOS Integration:**
    ```swift
    // Disconnect Twitter
    await api.delete("/api/social-media/twitter/disconnect")
    ```

    Args:
        platform: Platform to disconnect
        request: FastAPI request
        user: Current authenticated user
        db: Database session

    Returns:
        {
            "success": true,
            "message": "Twitter disconnected successfully"
        }

    Raises:
        404: Platform not connected
        401: Not authenticated
    """
    try:
        from database_social_media import SocialMediaConnection

        # Find connection
        connection = db.query(SocialMediaConnection).filter(
            SocialMediaConnection.user_id == user.id,
            SocialMediaConnection.platform == platform
        ).first()

        if not connection:
            raise create_error_exception(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message=f"{platform.title()} is not connected",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Delete connection
        db.delete(connection)
        db.commit()

        logger.info(f"Disconnected {platform} for user {user.id}")

        return {
            "success": True,
            "message": f"{platform.title()} disconnected successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting platform: {str(e)}", exc_info=True)
        db.rollback()
        raise create_error_exception(
            code=ErrorCode.SERVER_INTERNAL_ERROR,
            message=f"Failed to disconnect: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
