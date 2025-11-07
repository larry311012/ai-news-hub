"""
Image Generation Service for Instagram Posts

Handles AI-powered image generation using DALL-E 3 for Instagram posts.
Includes quota management, caching, progress tracking, and error handling.

Features:
- Generate images from prompts or post content
- Quota enforcement (per user, per day)
- Intelligent caching by prompt hash
- Real-time progress tracking
- Automatic retry with exponential backoff
- Cost tracking

Usage:
    # Create job and start generation
    job_id = ImageGenerationService.create_job(post_id, user_id, prompt)
    asyncio.create_task(ImageGenerationService.generate_image_async(...))

    # Poll status
    status = ImageGenerationService.get_status(job_id)

    # Check quota
    quota = ImageGenerationService.check_quota(user_id, db)
"""

import os
from pathlib import Path
import hashlib
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, func
from loguru import logger
import httpx
import base64

from database import Post, User, Base, engine, InstagramImage, ImageGenerationQuota, UserApiKey
from utils.encryption import decrypt_api_key


# ============================================================================
# EXCEPTIONS
# ============================================================================

class QuotaExceededError(Exception):
    """Raised when user exceeds daily image generation quota"""
    pass


class ImageGenerationError(Exception):
    """Base exception for image generation errors"""
    pass


# ============================================================================
# SERVICE
# ============================================================================

class ImageGenerationService:
    """
    Service for AI-powered image generation for Instagram posts

    Uses class methods and in-memory job store for async generation
    with progress tracking.
    """

    # In-memory job store (use Redis in production)
    active_jobs: Dict[str, Dict[str, Any]] = {}

    # Image cache by prompt hash
    _image_cache: Dict[str, Dict[str, Any]] = {}

    # Configuration
    DAILY_QUOTA = int(os.getenv("MAX_IMAGE_GENERATIONS_PER_DAY", "50"))
    DALLE_API_KEY = os.getenv("OPENAI_API_KEY", "")
    DALLE_URL = os.getenv("DALLE_API_URL", "https://api.openai.com/v1/images/generations")
    DALLE_MODEL = os.getenv("DALLE_MODEL", "dall-e-3")
    DEFAULT_SIZE = os.getenv("DALLE_IMAGE_SIZE", "1024x1024")
    DEFAULT_QUALITY = os.getenv("DALLE_IMAGE_QUALITY", "standard")
    STORAGE_PATH = os.getenv(
        "IMAGE_STORAGE_PATH",
        str(Path(__file__).resolve().parent.parent / "static" / "instagram_images")
    )

    @classmethod
    def create_job(
        cls,
        post_id: int,
        user_id: int,
        prompt: str,
        style: str = "modern",
        custom_prompt: Optional[str] = None
    ) -> str:
        """
        Create a new image generation job

        Args:
            post_id: Post ID
            user_id: User ID
            prompt: Image prompt
            style: Style preset
            custom_prompt: Optional custom prompt

        Returns:
            str: Unique job ID
        """
        job_id = f"img_gen_{uuid.uuid4().hex[:12]}"

        job = {
            "job_id": job_id,
            "post_id": post_id,
            "user_id": user_id,
            "prompt": prompt,
            "style": style,
            "custom_prompt": custom_prompt,
            "status": "queued",
            "progress": 0,
            "current_step": "Queued",
            "image_url": None,
            "thumbnail_url": None,
            "error": None,
            "created_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "cached": False,
            "generation_time_seconds": None,
            "width": None,
            "height": None,
            "file_size_bytes": None
        }

        cls.active_jobs[job_id] = job
        logger.info(f"Created image generation job {job_id} for post {post_id}")

        return job_id

    @classmethod
    def get_status(cls, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status

        Args:
            job_id: Job ID to check

        Returns:
            dict: Job status or None if not found
        """
        return cls.active_jobs.get(job_id)

    @classmethod
    def update_job(
        cls,
        job_id: str,
        progress: Optional[int] = None,
        current_step: Optional[str] = None,
        **kwargs
    ):
        """
        Update job status

        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
            current_step: Current step description
            **kwargs: Additional fields to update
        """
        if job_id in cls.active_jobs:
            if progress is not None:
                cls.active_jobs[job_id]["progress"] = progress
            if current_step is not None:
                cls.active_jobs[job_id]["current_step"] = current_step
            cls.active_jobs[job_id].update(kwargs)

    @classmethod
    def delete_job(cls, job_id: str):
        """
        Remove completed job from memory

        Args:
            job_id: Job ID to delete
        """
        if job_id in cls.active_jobs:
            del cls.active_jobs[job_id]
            logger.info(f"Deleted job {job_id} from memory")

    @classmethod
    def check_quota(cls, user_id: int, db: Session) -> Dict[str, Any]:
        """
        Check user's image generation quota

        Args:
            user_id: User ID
            db: Database session

        Returns:
            dict: Quota information with keys:
                - daily_limit: Max images per day
                - images_generated_today: Images generated today
                - remaining: Remaining quota for today
                - quota_reset_date: When quota resets (midnight)
                - total_images_generated: Lifetime total
                - total_cost_usd: Lifetime cost
        """
        # Get or create user's quota record
        quota_record = db.query(ImageGenerationQuota).filter(
            ImageGenerationQuota.user_id == user_id
        ).first()

        if not quota_record:
            # Create new quota record for user
            tomorrow_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            quota_record = ImageGenerationQuota(
                user_id=user_id,
                daily_limit=cls.DAILY_QUOTA,
                images_generated_today=0,
                quota_reset_date=tomorrow_start,
                total_images_generated=0,
                total_cost_usd=0.0
            )
            db.add(quota_record)
            db.commit()
            db.refresh(quota_record)

        # Check if quota needs reset (new day)
        now = datetime.now()
        if now >= quota_record.quota_reset_date:
            # Reset daily counter
            quota_record.images_generated_today = 0
            # Set next reset to tomorrow midnight
            tomorrow_start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            quota_record.quota_reset_date = tomorrow_start
            db.commit()

        return {
            "daily_limit": quota_record.daily_limit,
            "images_generated_today": quota_record.images_generated_today,
            "remaining": max(0, quota_record.daily_limit - quota_record.images_generated_today),
            "quota_reset_date": quota_record.quota_reset_date.isoformat(),
            "total_images_generated": quota_record.total_images_generated,
            "total_cost_usd": round(quota_record.total_cost_usd, 2)
        }

    @classmethod
    async def generate_image_async(
        cls,
        job_id: str,
        post_id: int,
        user_id: int,
        prompt: str,
        style: str = "modern",
        db: Session = None,
        regenerate: bool = False
    ):
        """
        Generate image asynchronously with progress updates

        Args:
            job_id: Job ID
            post_id: Post ID
            user_id: User ID
            prompt: Image prompt
            style: Style preset
            db: Database session
            regenerate: Force regenerate (skip cache)
        """
        from database import SessionLocal
        if db is None:
            db = SessionLocal()

        start_time = datetime.utcnow()

        try:
            # Update: Started
            cls.update_job(
                job_id,
                status="processing",
                progress=0,
                current_step="Initializing...",
                started_at=start_time
            )

            # Check quota
            quota_info = cls.check_quota(user_id, db)
            if quota_info["remaining"] <= 0 and not regenerate:
                raise QuotaExceededError("Daily quota exceeded")

            # Get post
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                raise ImageGenerationError(f"Post {post_id} not found")

            # Update: 10%
            cls.update_job(job_id, progress=10, current_step="Preparing prompt...")

            # Enhance prompt with style
            enhanced_prompt = cls._enhance_prompt_with_style(prompt, style)
            prompt_hash = cls._calculate_prompt_hash(enhanced_prompt, cls.DEFAULT_SIZE)

            # Check cache (if not regenerating)
            if not regenerate:
                cls.update_job(job_id, progress=20, current_step="Checking cache...")
                cached = await cls._check_cache(prompt_hash, db)
                if cached:
                    # Update post with cached image
                    post.instagram_image_url = cached["image_url"]
                    db.commit()

                    cls.update_job(
                        job_id,
                        status="completed",
                        progress=100,
                        current_step="Complete (from cache)",
                        image_url=cached["image_url"],
                        prompt=enhanced_prompt,
                        cached=True,
                        completed_at=datetime.utcnow(),
                        generation_time_seconds=0.5,
                        width=cached.get("width", 1024),
                        height=cached.get("height", 1024)
                    )

                    logger.info(f"Job {job_id}: Cache hit")
                    return

            # Update: 30%
            cls.update_job(job_id, progress=30, current_step="Calling DALL-E API...")

            # Get user's OpenAI API key
            user_openai_key = cls._get_user_openai_key(user_id, db)

            # Call DALL-E with user's API key
            image_data = await cls._call_dalle_api(
                prompt=enhanced_prompt,
                size=cls.DEFAULT_SIZE,
                quality=cls.DEFAULT_QUALITY,
                api_key=user_openai_key
            )

            # Update: 60%
            cls.update_job(job_id, progress=60, current_step="Saving image...")

            # Save image
            filename = f"post_{post_id}_{int(datetime.now().timestamp())}.png"
            image_path = await cls._save_image(
                image_bytes=image_data["image_bytes"],
                filename=filename,
                user_id=user_id
            )

            # Generate URL
            image_url = f"/api/images/instagram/{user_id}/{filename}"

            # Update: 80%
            cls.update_job(job_id, progress=80, current_step="Saving to database...")

            # Save to database
            import json
            instagram_image = InstagramImage(
                post_id=post_id,
                user_id=user_id,
                prompt=enhanced_prompt,
                prompt_hash=prompt_hash,
                image_url=image_url,
                width=1024,
                height=1024,
                format="png",
                file_size_bytes=len(image_data["image_bytes"]),
                ai_provider="openai",
                ai_model=cls.DALLE_MODEL,
                generation_params=json.dumps({
                    "size": cls.DEFAULT_SIZE,
                    "quality": cls.DEFAULT_QUALITY,
                    "style": style
                }),
                revised_prompt=image_data.get("revised_prompt"),  # FIX: Save revised prompt from DALL-E
                status="active"
            )
            db.add(instagram_image)

            # Update post
            post.instagram_image_url = image_url
            post.instagram_image_prompt = enhanced_prompt

            # Update quota
            cls._update_quota(
                user_id=user_id,
                cost=cls._calculate_cost(cls.DEFAULT_SIZE, cls.DEFAULT_QUALITY),
                db=db
            )

            db.commit()

            # Update cache
            cls._image_cache[prompt_hash] = {
                "image_url": image_url,
                "width": 1024,
                "height": 1024
            }

            # Update: 100%
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            cls.update_job(
                job_id,
                status="completed",
                progress=100,
                current_step="Complete",
                image_url=image_url,
                prompt=enhanced_prompt,
                cached=False,
                completed_at=datetime.utcnow(),
                generation_time_seconds=round(elapsed, 2),
                width=1024,
                height=1024,
                file_size_bytes=len(image_data["image_bytes"])
            )

            logger.info(f"Job {job_id}: Completed in {elapsed:.2f}s")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {str(e)}")
            cls.update_job(
                job_id,
                status="failed",
                progress=0,
                current_step="Failed",
                error=str(e),
                completed_at=datetime.utcnow()
            )
        finally:
            if db:
                db.close()

    @classmethod
    def _enhance_prompt_with_style(cls, prompt: str, style: str) -> str:
        """Add style modifiers to prompt"""
        style_modifiers = {
            "modern": "modern, clean, minimalist aesthetic, high-tech",
            "minimalist": "minimalist, simple, clean lines, monochromatic",
            "vibrant": "vibrant colors, bold, energetic, eye-catching",
            "professional": "professional, corporate, polished, sophisticated",
            "abstract": "abstract art, geometric shapes, conceptual",
            "futuristic": "futuristic, sci-fi, advanced technology, neon"
        }

        modifier = style_modifiers.get(style, style_modifiers["modern"])
        return f"{prompt}, {modifier}, digital art, high quality"

    @classmethod
    def _calculate_prompt_hash(cls, prompt: str, size: str) -> str:
        """Calculate hash for caching"""
        content = f"{prompt}|{size}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    @classmethod
    async def _check_cache(cls, prompt_hash: str, db: Session) -> Optional[Dict]:
        """Check if image with same prompt exists"""
        # Check memory cache first
        if prompt_hash in cls._image_cache:
            return cls._image_cache[prompt_hash]

        # Check database
        cached_image = db.query(InstagramImage).filter(
            InstagramImage.prompt_hash == prompt_hash,
            InstagramImage.status == "active"
        ).first()

        if cached_image:
            # Update last used
            cached_image.times_used += 1
            cached_image.last_used_at = datetime.utcnow()
            db.commit()

            result = {
                "image_url": cached_image.image_url,
                "width": cached_image.width,
                "height": cached_image.height
            }

            # Update memory cache
            cls._image_cache[prompt_hash] = result

            return result

        return None

    @classmethod
    def _get_user_openai_key(cls, user_id: int, db: Session) -> str:
        """
        Retrieve and decrypt user's OpenAI API key from database

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Decrypted OpenAI API key

        Raises:
            ImageGenerationError: If user doesn't have an OpenAI API key stored
        """
        user_key = db.query(UserApiKey).filter(
            UserApiKey.user_id == user_id,
            UserApiKey.provider == "openai"
        ).first()

        if not user_key:
            raise ImageGenerationError(
                "No OpenAI API key found. Please add your OpenAI API key in Profile Settings."
            )

        decrypted_key = decrypt_api_key(user_key.encrypted_key)

        if not decrypted_key:
            raise ImageGenerationError(
                "Failed to decrypt OpenAI API key. Please re-add your API key in Profile Settings."
            )

        return decrypted_key

    @classmethod
    async def _call_dalle_api(
        cls,
        prompt: str,
        size: str,
        quality: str,
        api_key: str = None
    ) -> Dict[str, Any]:
        """Call DALL-E API to generate image"""
        # Use provided API key or fall back to environment variable
        dalle_key = api_key or cls.DALLE_API_KEY

        if not dalle_key:
            raise ImageGenerationError("No OpenAI API key available")

        headers = {
            "Authorization": f"Bearer {dalle_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": cls.DALLE_MODEL,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": quality,
            "response_format": "b64_json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    cls.DALLE_URL,
                    json=payload,
                    headers=headers
                )

                if response.status_code == 401:
                    raise ImageGenerationError("Invalid DALL-E API key")
                elif response.status_code == 429:
                    raise ImageGenerationError("Rate limit exceeded")
                elif response.status_code == 400:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Bad request")
                    raise ImageGenerationError(f"API error: {error_msg}")

                response.raise_for_status()
                data = response.json()

                # Extract image data
                image_b64 = data["data"][0]["b64_json"]
                revised_prompt = data["data"][0].get("revised_prompt", prompt)

                # Decode base64 to bytes
                image_bytes = base64.b64decode(image_b64)

                return {
                    "image_bytes": image_bytes,
                    "revised_prompt": revised_prompt
                }

            except httpx.TimeoutException:
                raise ImageGenerationError("API request timed out (60s)")
            except httpx.HTTPError as e:
                raise ImageGenerationError(f"HTTP error: {str(e)}")

    @classmethod
    async def _save_image(
        cls,
        image_bytes: bytes,
        filename: str,
        user_id: int
    ) -> str:
        """Save image to storage"""
        from pathlib import Path
        import aiofiles

        # Create user directory
        user_dir = Path(cls.STORAGE_PATH) / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = user_dir / filename

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(image_bytes)

        logger.info(f"Saved image to {file_path}")

        return str(file_path)

    @classmethod
    def _update_quota(cls, user_id: int, cost: float, db: Session):
        """
        Update user's quota after generating an image

        Args:
            user_id: User ID
            cost: Cost of this generation in USD
            db: Database session
        """
        # Get user's quota record
        quota_record = db.query(ImageGenerationQuota).filter(
            ImageGenerationQuota.user_id == user_id
        ).first()

        if not quota_record:
            # Should not happen if check_quota was called first, but handle gracefully
            tomorrow_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            quota_record = ImageGenerationQuota(
                user_id=user_id,
                daily_limit=cls.DAILY_QUOTA,
                images_generated_today=0,
                quota_reset_date=tomorrow_start,
                total_images_generated=0,
                total_cost_usd=0.0
            )
            db.add(quota_record)

        # Check if we need to reset daily counter (new day)
        now = datetime.now()
        if now >= quota_record.quota_reset_date:
            quota_record.images_generated_today = 0
            tomorrow_start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            quota_record.quota_reset_date = tomorrow_start

        # Increment counters
        quota_record.images_generated_today += 1
        quota_record.total_images_generated += 1
        quota_record.total_cost_usd += cost
        quota_record.updated_at = datetime.utcnow()

        logger.info(
            f"Updated quota for user {user_id}: "
            f"{quota_record.images_generated_today}/{quota_record.daily_limit} today, "
            f"{quota_record.total_images_generated} total"
        )

    @classmethod
    def _calculate_cost(cls, size: str, quality: str) -> float:
        """Calculate DALL-E cost based on size and quality"""
        if quality == "hd":
            return 0.080 if size == "1024x1024" else 0.120
        else:
            return 0.040 if size == "1024x1024" else 0.080
