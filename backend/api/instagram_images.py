"""
Instagram Image Generation API Endpoints

Provides RESTful API for:
- Generating Instagram images with DALL-E 3
- Checking generation status (polling)
- Getting image metadata
- Regenerating images
- Checking user quota

All endpoints require authentication via JWT token.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import asyncio
from loguru import logger

from database import get_db, Post, User, InstagramImage
from utils.auth_selector import get_current_user as get_current_user_dependency
from schemas.instagram import (
    GenerateImageRequest,
    GenerateImageResponse,
    ImageStatusResponse,
    RegenerateImageRequest,
    ImageMetadataResponse,
    ImageGenerationQuotaResponse
)
from services.image_generation_service import ImageGenerationService


router = APIRouter()


@router.post("/posts/{post_id}/generate-instagram-image", response_model=GenerateImageResponse)
async def generate_instagram_image(
    post_id: int,
    request: GenerateImageRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Generate Instagram image for a post using DALL-E 3

    This endpoint starts an async background job. Poll the status endpoint
    to check progress.

    Steps:
    1. Validates post ownership
    2. Checks user quota
    3. Generates or uses cached image
    4. Updates post with image URL

    **Returns 202 Accepted** - Generation started
    **Returns 404** - Post not found
    **Returns 429** - Quota exceeded
    """
    try:
        # Verify post exists and belongs to user
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user.id
        ).first()

        if not post:
            raise HTTPException(
                status_code=404,
                detail=f"Post {post_id} not found or you don't have access"
            )

        # Get prompt (custom or from post)
        prompt = request.custom_prompt

        if not prompt:
            # Use post's existing prompt or generate from content
            prompt = post.instagram_image_prompt

        if not prompt:
            # Generate prompt from post content
            if post.instagram_caption:
                # Extract key themes from caption
                prompt = f"Modern abstract visualization of: {post.instagram_caption[:200]}"
            elif post.twitter_content:
                prompt = f"Tech illustration for: {post.twitter_content[:200]}"
            else:
                prompt = "Modern AI and technology abstract art, vibrant colors, professional"

        # Check quota before starting
        quota_info = ImageGenerationService.check_quota(user.id, db)
        if quota_info["remaining"] <= 0:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Daily image generation quota ({quota_info['daily_limit']}) exceeded. "
                    f"Resets at midnight."
                )
            )

        # Create generation job
        job_id = ImageGenerationService.create_job(
            post_id=post_id,
            user_id=user.id,
            prompt=prompt,
            style=request.style.value if request.style else "modern",
            custom_prompt=request.custom_prompt
        )

        # Start background generation
        # Create new DB session for background task
        from database import SessionLocal
        background_db = SessionLocal()

        # Use asyncio.create_task for true async execution
        asyncio.create_task(
            ImageGenerationService.generate_image_async(
                job_id=job_id,
                post_id=post_id,
                user_id=user.id,
                prompt=prompt,
                style=request.style.value if request.style else "modern",
                db=background_db,
                regenerate=request.regenerate
            )
        )

        logger.info(
            f"Started image generation job {job_id} for post {post_id}",
            extra={"user_id": user.id, "regenerate": request.regenerate}
        )

        return GenerateImageResponse(
            success=True,
            message="Image generation started",
            job_id=job_id,
            post_id=post_id,
            estimated_seconds=30,
            status_url=f"/api/posts/{post_id}/instagram-image/status?job_id={job_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start image generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start image generation: {str(e)}"
        )


@router.get("/posts/{post_id}/instagram-image/status", response_model=ImageStatusResponse)
async def get_image_generation_status(
    post_id: int,
    job_id: str = None,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Poll image generation status

    Call this endpoint every 1-2 seconds until status is 'completed' or 'failed'.

    **Statuses:**
    - `queued`: Job created, waiting to start
    - `processing`: Currently generating image
    - `completed`: Image ready (includes URL)
    - `failed`: Generation failed (includes error)

    **Returns 200** - Status info
    **Returns 404** - Post or job not found
    """
    try:
        # Verify post ownership
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user.id
        ).first()

        if not post:
            raise HTTPException(
                status_code=404,
                detail=f"Post {post_id} not found"
            )

        # If job_id provided, use it; otherwise find most recent job for post
        if not job_id:
            # Find active job for this post
            job_id = None
            for jid, job_data in ImageGenerationService.active_jobs.items():
                if job_data["post_id"] == post_id and job_data["user_id"] == user.id:
                    job_id = jid
                    break

            if not job_id:
                # No active job, check if image already exists
                if post.instagram_image_url:
                    return ImageStatusResponse(
                        status="completed",
                        progress=100,
                        current_step="Image already generated",
                        job_id="existing",
                        image_url=post.instagram_image_url,
                        cached=True
                    )
                else:
                    raise HTTPException(
                        status_code=404,
                        detail="No active generation job found for this post"
                    )

        # Get job status
        status = ImageGenerationService.get_status(job_id)

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )

        # Return status info
        return ImageStatusResponse(
            status=status["status"],
            progress=status["progress"],
            current_step=status["current_step"],
            job_id=job_id,
            image_url=status.get("image_url"),
            thumbnail_url=status.get("thumbnail_url"),
            prompt=status.get("prompt"),
            width=status.get("width"),
            height=status.get("height"),
            file_size_bytes=status.get("file_size_bytes"),
            error=status.get("error"),
            generation_time_seconds=status.get("generation_time_seconds"),
            cached=status.get("cached", False)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/posts/{post_id}/instagram-image", response_model=ImageMetadataResponse)
async def get_instagram_image(
    post_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get metadata for post's Instagram image

    Returns full metadata including generation params, usage stats, etc.

    **Returns 200** - Image metadata
    **Returns 404** - Post or image not found
    """
    try:
        # Get post
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user.id
        ).first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Get image from database
        image = db.query(InstagramImage).filter(
            InstagramImage.post_id == post_id,
            InstagramImage.status == 'active'
        ).first()

        if not image:
            raise HTTPException(
                status_code=404,
                detail="No image found for this post"
            )

        # Parse generation params
        import json
        gen_params = None
        if image.generation_params:
            try:
                gen_params = json.loads(image.generation_params)
            except:
                gen_params = {}

        return ImageMetadataResponse(
            image_id=image.id,
            post_id=image.post_id,
            user_id=image.user_id,
            article_id=image.article_id,
            image_url=image.image_url,
            thumbnail_url=image.thumbnail_url,
            prompt=image.prompt,
            prompt_hash=image.prompt_hash,
            width=image.width or 1024,
            height=image.height or 1024,
            format=image.format or "png",
            file_size_bytes=image.file_size_bytes or 0,
            ai_provider=image.ai_provider or "openai",
            ai_model=image.ai_model or "dall-e-3",
            generation_params=gen_params,
            times_used=image.times_used or 1,
            last_used_at=image.last_used_at,
            status=image.status or "active",
            created_at=image.created_at,
            updated_at=image.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get image metadata: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get image metadata: {str(e)}"
        )


@router.post("/posts/{post_id}/regenerate-instagram-image", response_model=GenerateImageResponse)
async def regenerate_instagram_image(
    post_id: int,
    request: RegenerateImageRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Force regenerate image with new parameters

    Bypasses cache and generates a fresh image. Useful for:
    - Trying different styles
    - Custom prompts
    - Unsatisfied with current image

    **Returns 202 Accepted** - Regeneration started
    **Returns 404** - Post not found
    **Returns 429** - Quota exceeded
    """
    try:
        # Verify post ownership
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user.id
        ).first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Check quota
        quota_info = ImageGenerationService.check_quota(user.id, db)
        if quota_info["remaining"] <= 0:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Daily quota ({quota_info['daily_limit']}) exceeded. "
                    f"Resets at midnight."
                )
            )

        # Get prompt
        prompt = request.custom_prompt or post.instagram_image_prompt

        if not prompt:
            prompt = "Modern AI technology illustration, vibrant, professional"

        # Create job with regenerate=True
        job_id = ImageGenerationService.create_job(
            post_id=post_id,
            user_id=user.id,
            prompt=prompt,
            style=request.style.value if request.style else "modern",
            custom_prompt=request.custom_prompt
        )

        # Start background generation
        from database import SessionLocal
        background_db = SessionLocal()

        asyncio.create_task(
            ImageGenerationService.generate_image_async(
                job_id=job_id,
                post_id=post_id,
                user_id=user.id,
                prompt=prompt,
                style=request.style.value if request.style else "modern",
                db=background_db,
                regenerate=True  # Force regenerate
            )
        )

        logger.info(f"Started image regeneration for post {post_id}")

        return GenerateImageResponse(
            success=True,
            message="Image regeneration started",
            job_id=job_id,
            post_id=post_id,
            estimated_seconds=30,
            status_url=f"/api/posts/{post_id}/instagram-image/status?job_id={job_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to regenerate image: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to regenerate image: {str(e)}"
        )


@router.get("/instagram/quota", response_model=ImageGenerationQuotaResponse)
async def get_quota(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get user's image generation quota status

    Returns:
    - Daily limit
    - Images generated today
    - Remaining quota
    - Reset time
    - Total usage and cost

    **Returns 200** - Quota info
    """
    try:
        quota_info = ImageGenerationService.check_quota(user.id, db)

        from datetime import datetime
        reset_date = datetime.fromisoformat(quota_info["quota_reset_date"])

        return ImageGenerationQuotaResponse(
            daily_limit=quota_info["daily_limit"],
            images_generated_today=quota_info["images_generated_today"],
            remaining_today=quota_info["remaining"],
            quota_reset_date=reset_date,
            total_images_generated=quota_info["total_images_generated"],
            total_cost_usd=quota_info["total_cost_usd"]
        )

    except Exception as e:
        logger.error(f"Failed to get quota: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get quota: {str(e)}"
        )


@router.delete("/posts/{post_id}/instagram-image")
async def delete_instagram_image(
    post_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Delete Instagram image for a post

    Removes image from storage and database. Post can then have a new image generated.

    **Returns 200** - Image deleted
    **Returns 404** - Post or image not found
    """
    try:
        # Get post
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user.id
        ).first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Get image
        image = db.query(InstagramImage).filter(
            InstagramImage.post_id == post_id,
            InstagramImage.status == 'active'
        ).first()

        if not image:
            raise HTTPException(status_code=404, detail="No image found")

        # Mark as deleted (soft delete)
        image.status = 'deleted'

        # Clear post's image URL
        post.instagram_image_url = None

        db.commit()

        logger.info(f"Deleted Instagram image for post {post_id}")

        return {
            "success": True,
            "message": "Image deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete image: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete image: {str(e)}"
        )
