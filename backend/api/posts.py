"""
Posts API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import asyncio
import json

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from database import get_db, Post, Article, Settings, User, UserApiKey, AdminSettings
from database_social_media import SocialMediaConnection, SocialMediaPost
from src.summarizers import AISummarizer
from src.generators import ContentGenerator
from src.publishers import TwitterPublisher, LinkedInPublisher, ThreadsPublisher
from src.publishers.exceptions import (
    AuthenticationException,
    RateLimitException,
    PublishingException,
)
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.encryption import decrypt_api_key
from utils.social_connection_manager import SocialConnectionManager
from utils.posts_cache import posts_cache, PostsCache

# QUOTA MANAGEMENT: Import quota checker
from middleware.quota_checker import QuotaManager, check_quota_dependency, increment_user_quota

# SECURITY: Import input sanitization utilities
from utils.input_sanitization import (
    sanitize_twitter_content,
    sanitize_linkedin_content,
    sanitize_threads_content,
    sanitize_instagram_caption,
    sanitize_url,
    detect_xss_attempt,
)

# Import AI error handling
try:
    from src.utils.ai_exceptions import AIProviderError
except ImportError:
    # Fallback if module not found
    class AIProviderError(Exception):
        def __init__(self, *args, **kwargs):
            super().__init__(*args)
            self.error_details = kwargs.get('error_details', {})

import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# Pydantic models
class GenerateRequest(BaseModel):
    article_ids: List[int]
    platforms: List[str]  # twitter, linkedin, threads


class PostResponse(BaseModel):
    id: int
    article_title: Optional[str]
    twitter_content: Optional[str]
    linkedin_content: Optional[str]
    threads_content: Optional[str]
    platforms: List[str]
    status: str
    created_at: datetime
    published_at: Optional[datetime]

    class Config:
        from_attributes = True


class PublishRequest(BaseModel):
    post_id: int
    platforms: List[str]


class ErrorDetail(BaseModel):
    """Structured error information for frontend"""
    type: str
    message: str
    provider: Optional[str] = None
    action: Optional[str] = None
    documentation: Optional[str] = None
    retry_after: Optional[int] = None


class GenerateStatusResponse(BaseModel):
    post_id: int
    status: str
    progress: int  # 0-100
    current_step: str
    content: dict
    error: Optional[str] = None
    error_details: Optional[ErrorDetail] = None  # NEW: Structured error info


class ConnectionCheckResponse(BaseModel):
    """Response for connection status check"""

    platform: str
    connected: bool
    username: Optional[str] = None
    needs_reconnection: bool = False
    error: Optional[str] = None


# In-memory store for generation jobs (in production, use Redis)
generation_jobs = {}


# =========================================================================
# HELPER FUNCTIONS FOR generate_post_async (Function 3 Refactoring)
# =========================================================================

def _prepare_articles_data(db: Session, article_ids: List[int]) -> Optional[List[dict]]:
    """
    Fetch and prepare articles for summarization.

    Returns:
        List of article dicts, or None if no articles found
    """
    articles = db.query(Article).filter(Article.id.in_(article_ids)).all()

    if not articles:
        return None

    return [
        {
            "title": a.title,
            "link": a.link,
            "summary": a.summary or "",
            "source": a.source,
            "published": a.published,
        }
        for a in articles
    ]


def _configure_api_key(api_key: str, ai_provider: str):
    """Set API key in environment based on provider."""
    if ai_provider == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
    elif ai_provider == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = api_key
    elif ai_provider == "deepseek":
        os.environ["DEEPSEEK_API_KEY"] = api_key


def _build_platform_config(platforms: List[str]) -> dict:
    """Build platform configuration for content generation."""
    return {
        "twitter": {"enabled": "twitter" in platforms, "max_length": 280},
        "linkedin": {"enabled": "linkedin" in platforms, "max_length": 3000},
        "threads": {"enabled": "threads" in platforms, "max_length": 500},
        "instagram": {"enabled": "instagram" in platforms, "max_length": 2200},
    }


def _update_job_status(
    post_id: int,
    status: str,
    progress: int,
    step: str,
    error: Optional[str] = None,
    error_details: Optional[Dict[str, Any]] = None
):
    """Update generation job status with optional structured error details."""
    if post_id in generation_jobs:
        generation_jobs[post_id]["status"] = status
        generation_jobs[post_id]["progress"] = progress
        generation_jobs[post_id]["current_step"] = step
        if error:
            generation_jobs[post_id]["error"] = error
        if error_details:
            generation_jobs[post_id]["error_details"] = error_details


def _update_generation_progress(post_id: int, completed_count: int, total_count: int):
    """Update progress during platform-specific generation."""
    if post_id not in generation_jobs:
        return

    progress = 50 + (completed_count / total_count * 40)
    generation_jobs[post_id]["progress"] = int(progress)


async def _generate_platform_content(
    summary: dict,
    platform_config: dict,
    post_id: int
) -> dict:
    """
    Generate content for all enabled platforms in parallel.

    Returns:
        Dictionary mapping platform names to generated content
    """
    async def generate_single_platform(platform, config):
        if not config.get("enabled"):
            return platform, None

        generator = ContentGenerator(None, {platform: config})
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, generator.generate_posts, summary)

        return platform, result.get(platform, "")

    tasks = [
        generate_single_platform(platform, config)
        for platform, config in platform_config.items()
        if config.get("enabled")
    ]

    platform_results = await asyncio.gather(*tasks)

    # Build content dictionary
    posts_content = {}
    enabled_count = sum(1 for c in platform_config.values() if c.get("enabled"))

    for platform, content in platform_results:
        if content:
            # Handle Instagram dict vs string
            if platform == "instagram" and isinstance(content, dict):
                posts_content[platform] = content.get("caption", "")
                generation_jobs[post_id]["content"][platform] = content.get("caption", "")
            else:
                posts_content[platform] = content
                generation_jobs[post_id]["content"][platform] = content

            # Update progress
            completed_count = len([c for c in generation_jobs[post_id]["content"].values() if c])
            _update_generation_progress(post_id, completed_count, enabled_count)

    return posts_content


def _update_post_with_content(post: Post, content: dict, summary: dict, db: Session):
    """Update post record with generated content."""
    post.twitter_content = content.get("twitter", "")
    post.linkedin_content = content.get("linkedin", "")
    post.threads_content = content.get("threads", "")

    # Handle Instagram dict content
    instagram_content = content.get("instagram", "")
    if isinstance(instagram_content, dict):
        post.instagram_caption = instagram_content.get("caption", "")
        if hasattr(post, "instagram_image_prompt"):
            post.instagram_image_prompt = instagram_content.get("image_prompt", "")
    else:
        post.instagram_caption = instagram_content

    post.ai_summary = summary.get("summary", "")
    post.status = "draft"

    db.commit()
    db.refresh(post)


def _save_error_to_post(post_id: int, error_message: str, error_details: Optional[Dict], db: Session):
    """Save error information to post record in database."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if post:
        post.status = "failed"
        post.error_message = error_message
        if error_details:
            post.error_details = error_details  # Save structured error as JSON
        db.commit()


async def generate_post_async(
    post_id: int,
    article_ids: List[int],
    platforms: List[str],
    user_id: int,
    api_key: str,
    ai_provider: str,
    db: Session,
):
    """Background task to generate posts with progress tracking and detailed error handling"""
    try:
        # Initialize job
        generation_jobs[post_id] = {
            "status": "processing",
            "progress": 10,
            "current_step": "Fetching articles",
            "content": {},
            "error": None,
            "error_details": None,
        }

        # Configure API
        _configure_api_key(api_key, ai_provider)

        # Get articles
        articles_data = _prepare_articles_data(db, article_ids)
        if not articles_data:
            error_msg = "No articles found"
            _update_job_status(post_id, "failed", 0, "Failed", error_msg)
            _save_error_to_post(post_id, error_msg, None, db)
            return

        # Generate summary with AI error handling
        _update_job_status(post_id, "processing", 25, "Generating AI summary")
        try:
            summarizer = AISummarizer(provider=ai_provider)
            summary = summarizer.summarize_articles(articles_data, user_id=user_id)
        except AIProviderError as e:
            # Structured AI error
            error_details = e.to_dict() if hasattr(e, 'to_dict') else {
                "type": getattr(e, 'error_type', 'unknown_error'),
                "message": str(e),
                "provider": ai_provider,
                "action": getattr(e, 'action', "Please try again"),
                "help_url": getattr(e, 'help_url', None),
            }

            logger.error(f"AI error generating summary for post {post_id}: {error_details}")

            _update_job_status(
                post_id,
                "failed",
                25,
                "AI Error",
                error_details.get("message"),
                error_details
            )
            _save_error_to_post(post_id, error_details.get("message"), error_details, db)
            return
        except Exception as e:
            # Unexpected error
            error_msg = f"Failed to generate summary: {str(e)}"
            logger.error(f"Unexpected error in summarization for post {post_id}: {e}")

            _update_job_status(post_id, "failed", 25, "Error", error_msg)
            _save_error_to_post(post_id, error_msg, None, db)
            return

        # Generate platform content
        _update_job_status(post_id, "processing", 50, "Generating platform posts")
        try:
            platform_config = _build_platform_config(platforms)
            posts_content = await _generate_platform_content(summary, platform_config, post_id)
        except Exception as e:
            error_msg = f"Failed to generate platform content: {str(e)}"
            logger.error(f"Error generating platform content for post {post_id}: {e}")

            _update_job_status(post_id, "failed", 50, "Error", error_msg)
            _save_error_to_post(post_id, error_msg, None, db)
            return

        # Save to database
        _update_job_status(post_id, "processing", 95, "Saving post")
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            _update_post_with_content(post, posts_content, summary, db)

            # Clear any previous errors
            post.error_message = None
            post.error_details = None
            db.commit()

            # Complete
            _update_job_status(post_id, "completed", 100, "Complete")
            generation_jobs[post_id]["content"] = {
                "twitter": post.twitter_content,
                "linkedin": post.linkedin_content,
                "threads": post.threads_content,
                "instagram": post.instagram_caption,
                "summary": summary.get("summary", ""),
            }

    except Exception as e:
        import traceback
        traceback.print_exc()

        error_msg = str(e) if str(e) else "Unknown error occurred"
        logger.error(f"Unexpected error in generate_post_async for post {post_id}: {e}")

        _update_job_status(post_id, "failed", 0, "Failed", error_msg)
        _save_error_to_post(post_id, error_msg, None, db)


@router.post("/generate")
async def generate_post(
    request: GenerateRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Generate social media posts from selected articles (optimized with async processing)

    This endpoint now returns immediately with a post_id and status.
    Use GET /api/posts/{post_id}/status to poll for completion, or
    use GET /api/posts/generate/stream for real-time progress updates via SSE.

    Enforces quota limits based on user tier:
    - Guest users: 1 post (uses admin default API key)
    - Free users: 2 posts per day
    - Paid users: 100 posts per day
    """
    try:
        # Get API key
        user_api_keys = db.query(UserApiKey).filter(UserApiKey.user_id == user.id).all()

        available_keys = {key.provider: key.encrypted_key for key in user_api_keys}

        api_key = None
        ai_provider = None

        # Priority order: OpenAI first, then Anthropic, then DeepSeek
        for provider in ["openai", "anthropic", "deepseek"]:
            if provider in available_keys:
                try:
                    api_key = decrypt_api_key(available_keys[provider])
                    if api_key:
                        ai_provider = provider
                        break
                except Exception as e:
                    print(f"Failed to decrypt {provider} key: {e}")
                    continue

        # Fallback to Settings table
        if not api_key:
            ai_provider_setting = db.query(Settings).filter(Settings.key == "ai_provider").first()
            api_key_setting = db.query(Settings).filter(Settings.key == "api_key").first()

            if api_key_setting and api_key_setting.value:
                ai_provider = ai_provider_setting.value if ai_provider_setting else "openai"
                from cryptography.fernet import Fernet

                ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
                cipher_suite = Fernet(ENCRYPTION_KEY.encode())
                try:
                    api_key = cipher_suite.decrypt(api_key_setting.value.encode()).decode()
                except Exception as decrypt_error:
                    print(f"Failed to decrypt Settings API key: {decrypt_error}")

        # Fallback to admin default API key for guest users
        if not api_key and user.user_tier == "guest":
            admin_api_key_setting = db.query(AdminSettings).filter(
                AdminSettings.key == "admin_default_api_key"
            ).first()
            admin_provider_setting = db.query(AdminSettings).filter(
                AdminSettings.key == "default_ai_provider"
            ).first()

            if admin_api_key_setting and admin_api_key_setting.value:
                ai_provider = admin_provider_setting.value if admin_provider_setting else "openai"

                # Decrypt if encrypted
                if admin_api_key_setting.encrypted:
                    from cryptography.fernet import Fernet
                    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
                    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
                    try:
                        api_key = cipher_suite.decrypt(admin_api_key_setting.value.encode()).decode()
                    except Exception as decrypt_error:
                        logger.error(f"Failed to decrypt admin API key: {decrypt_error}")
                else:
                    api_key = admin_api_key_setting.value

                logger.info(f"Using admin default {ai_provider} API key for guest user {user.id}")

        if not api_key:
            error_message = "No API key configured. Please add your OpenAI, Anthropic, or DeepSeek API key in your Profile settings."
            if user.user_tier == "guest":
                error_message = "No admin default API key configured. Please contact support or create an account."

            raise HTTPException(
                status_code=400,
                detail=error_message,
            )

        # Get articles
        articles = db.query(Article).filter(Article.id.in_(request.article_ids)).all()

        if not articles:
            raise HTTPException(status_code=404, detail="No articles found")

        # QUOTA CHECK: Ensure user has quota remaining
        quota_manager = QuotaManager(db)
        has_quota, quota_info = quota_manager.check_quota(user)

        if not has_quota:
            logger.warning(f"Quota exceeded for user {user.id} ({user.user_tier})")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "quota_exceeded",
                    "message": f"Daily quota exceeded. You have used {quota_info['used']}/{quota_info['limit']} posts today.",
                    "quota": quota_info,
                    "upgrade_message": "Upgrade to a paid plan for unlimited posts." if user.user_tier == "free" else None,
                },
            )

        logger.info(f"Quota check passed for user {user.id}: {quota_info['used']}/{quota_info['limit']} used")

        # Create post record immediately with "processing" status
        post = Post(
            user_id=user.id,
            article_id=articles[0].id if len(articles) == 1 else None,  # FIX: Link to source article
            article_title=articles[0].title if len(articles) == 1 else f"{len(articles)} articles",
            twitter_content="",
            linkedin_content="",
            threads_content="",
            platforms=request.platforms,
            status="processing",
            ai_summary="",
        )

        db.add(post)
        db.commit()
        db.refresh(post)

        # Increment quota after successful post creation
        try:
            increment_user_quota(user, db)
            logger.info(f"Incremented quota for user {user.id} after post {post.id} creation")
        except Exception as e:
            logger.error(f"Failed to increment quota for user {user.id}: {e}")
            # Don't fail the request if quota increment fails

        # Invalidate user's post list cache (new post added)
        await PostsCache.invalidate_user_posts(user.id)

        # Initialize job status
        generation_jobs[post.id] = {
            "status": "queued",
            "progress": 0,
            "current_step": "Queued",
            "content": {},
            "error": None,
            "error_details": None,
        }

        # Start background task (create a new session for thread safety)
        from database import SessionLocal

        background_db = SessionLocal()

        # Fire and forget the async task
        asyncio.create_task(
            generate_post_async(
                post.id,
                request.article_ids,
                request.platforms,
                user.id,
                api_key,
                ai_provider,
                background_db,
            )
        )

        # Get updated quota info
        _, updated_quota = quota_manager.check_quota(user)

        # Return immediately
        return {
            "success": True,
            "post_id": post.id,
            "status": "processing",
            "message": "Post generation started. Poll /api/posts/{post_id}/status for progress or use SSE stream.",
            "quota": updated_quota,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        error_detail = str(e) if str(e) else "Unknown error occurred"
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/generate/stream")
async def generate_post_stream(
    article_ids: str,  # comma-separated
    platforms: str,  # comma-separated
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Generate social media posts with real-time progress via Server-Sent Events (SSE)

    Example usage:
    GET /api/posts/generate/stream?article_ids=1,2,3&platforms=twitter,linkedin
    """

    async def event_generator():
        try:
            # Parse parameters
            article_id_list = [int(x.strip()) for x in article_ids.split(",")]
            platform_list = [x.strip() for x in platforms.split(",")]

            # Send initial event
            yield f"data: {json.dumps({'status': 'started', 'progress': 0, 'step': 'Initializing'})}\n\n"

            # Get API key (same logic as before)
            user_api_keys = db.query(UserApiKey).filter(UserApiKey.user_id == user.id).all()

            available_keys = {key.provider: key.encrypted_key for key in user_api_keys}
            api_key = None
            ai_provider = None

            for provider in ["openai", "anthropic", "deepseek"]:
                if provider in available_keys:
                    try:
                        api_key = decrypt_api_key(available_keys[provider])
                        if api_key:
                            ai_provider = provider
                            break
                    except Exception as e:
                        continue

            if not api_key:
                yield f"data: {json.dumps({'status': 'error', 'error': 'No API key configured'})}\n\n"
                return

            # Set API key
            _configure_api_key(api_key, ai_provider)

            # Get articles
            yield f"data: {json.dumps({'status': 'processing', 'progress': 10, 'step': 'Fetching articles'})}\n\n"

            articles = db.query(Article).filter(Article.id.in_(article_id_list)).all()

            if not articles:
                yield f"data: {json.dumps({'status': 'error', 'error': 'No articles found'})}\n\n"
                return

            articles_data = [
                {
                    "title": a.title,
                    "link": a.link,
                    "summary": a.summary or "",
                    "source": a.source,
                    "published": a.published,
                }
                for a in articles
            ]

            # Generate summary
            yield f"data: {json.dumps({'status': 'processing', 'progress': 25, 'step': 'Generating AI summary'})}\n\n"

            summarizer = AISummarizer(provider=ai_provider)
            summary = summarizer.summarize_articles(articles_data)

            # Generate platform posts
            yield f"data: {json.dumps({'status': 'processing', 'progress': 50, 'step': 'Generating platform posts'})}\n\n"

            platform_config = {
                "twitter": {"enabled": "twitter" in platform_list, "max_length": 280},
                "linkedin": {"enabled": "linkedin" in platform_list, "max_length": 3000},
                "threads": {"enabled": "threads" in platform_list, "max_length": 500},
            }

            posts_content = {}
            enabled_platforms = [p for p, c in platform_config.items() if c.get("enabled")]

            for i, platform in enumerate(enabled_platforms):
                config = platform_config[platform]
                generator = ContentGenerator(summarizer, {platform: config})
                result = generator.generate_posts(summary)
                posts_content[platform] = result.get(platform, "")

                # Send progress update
                progress = 50 + ((i + 1) / len(enabled_platforms) * 40)
                yield f"data: {json.dumps({'status': 'processing', 'progress': int(progress), 'step': f'Generated {platform} post', 'content': {platform: posts_content[platform]}})}\n\n"

            # Save to database
            yield f"data: {json.dumps({'status': 'processing', 'progress': 95, 'step': 'Saving post'})}\n\n"

            post = Post(
                user_id=user.id,
                article_id=articles[0].id if len(articles) == 1 else None,  # FIX: Link to source article
                article_title=articles[0].title
                if len(articles) == 1
                else f"{len(articles)} articles",
                twitter_content=posts_content.get("twitter", ""),
                linkedin_content=posts_content.get("linkedin", ""),
                threads_content=posts_content.get("threads", ""),
                platforms=platform_list,
                status="draft",
                ai_summary=summary.get("summary", ""),
            )

            db.add(post)
            db.commit()
            db.refresh(post)

            # Send completion event
            yield f"data: {json.dumps({'status': 'completed', 'progress': 100, 'step': 'Complete', 'post_id': post.id, 'content': {'twitter': post.twitter_content, 'linkedin': post.linkedin_content, 'threads': post.threads_content, 'summary': summary.get('summary', '')}})}\n\n"

        except Exception as e:
            import traceback

            traceback.print_exc()
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# =========================================================================
# HELPER FUNCTIONS FOR get_post_generation_status (Function 1 Refactoring)
# =========================================================================

def _determine_platform_status(content: dict, platform: str, progress: int) -> dict:
    """
    Determine status for a single platform based on content availability and progress.

    Args:
        content: Dictionary of generated content
        platform: Platform name (twitter, linkedin, threads, instagram)
        progress: Current generation progress (0-100)

    Returns:
        Dict with 'status' and 'message' keys
    """
    # Platform-specific progress thresholds
    thresholds = {
        'twitter': 25,
        'linkedin': 40,
        'threads': 55,
        'instagram': 70
    }

    threshold = thresholds.get(platform, 25)
    has_content = bool(content.get(platform))

    if has_content:
        return {'status': 'complete', 'message': 'Ready'}
    elif progress > threshold:
        return {'status': 'processing', 'message': 'Generating...'}
    else:
        return {'status': 'pending', 'message': 'Waiting...'}


def _get_post_content_dict(post: Post) -> dict:
    """Extract all platform content from post model into a dict."""
    return {
        'twitter': post.twitter_content or '',
        'linkedin': post.linkedin_content or '',
        'threads': post.threads_content or '',
        'instagram': post.instagram_caption or '',
        'summary': post.ai_summary or ''
    }


def _build_platform_statuses(content: dict, progress: int) -> dict:
    """
    Build platform status dictionary for all platforms.

    Args:
        content: Dictionary of generated content
        progress: Current generation progress

    Returns:
        Dictionary mapping platform names to status dicts
    """
    platforms = ['twitter', 'linkedin', 'threads', 'instagram']
    return {
        platform: _determine_platform_status(content, platform, progress)
        for platform in platforms
    }


def _handle_in_progress_job(post_id: int, post: Post, db: Session) -> dict:
    """Handle response for jobs currently in progress."""
    job_status = generation_jobs[post_id]

    if job_status["status"] == "completed":
        db.refresh(post)
        del generation_jobs[post_id]
        content = _get_post_content_dict(post)
        platforms_status = _build_platform_statuses(content, 100)

        return {
            "post_id": post_id,
            "status": "completed",
            "progress": 100,
            "current_step": "Complete",
            "content": content,
            "platforms": platforms_status,
            "error": None,
            "error_details": None,
        }

    # Still processing or failed
    content = job_status["content"]
    platforms_status = _build_platform_statuses(content, job_status["progress"])

    response = {
        "post_id": post_id,
        "status": job_status["status"],
        "progress": job_status["progress"],
        "current_step": job_status["current_step"],
        "content": content,
        "platforms": platforms_status,
        "error": job_status.get("error"),
    }

    # Add structured error details if available
    if job_status.get("error_details"):
        response["error_details"] = job_status["error_details"]

    return response


def _handle_completed_job(post: Post) -> dict:
    """Handle response for completed or not-started jobs."""
    content = _get_post_content_dict(post)
    progress = 100 if post.status == "draft" else 0
    platforms_status = _build_platform_statuses(content, progress)

    response = {
        "post_id": post.id,
        "status": post.status,
        "progress": progress,
        "current_step": "Complete" if post.status == "draft" else "Not started",
        "content": content,
        "platforms": platforms_status,
        "error": post.error_message,
    }

    # Add structured error details if available (from database)
    if post.error_details:
        response["error_details"] = post.error_details

    return response


@router.get("/{post_id}/status")
async def get_post_generation_status(
    post_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get the generation status of a post (for polling approach)

    Returns structured error information if generation failed.
    """
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user.id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check if job is in progress
    if post_id in generation_jobs:
        return _handle_in_progress_job(post_id, post, db)

    # Job completed or not started
    return _handle_completed_job(post)


@router.get("/{post_id}/connections", response_model=List[ConnectionCheckResponse])
async def check_post_connections(
    post_id: int, user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Check which platforms are connected for a specific post.

    Returns connection status for each platform in the post.
    """
    # Verify post belongs to user
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user.id).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    manager = SocialConnectionManager(db)
    connection_statuses = []

    # Check each platform
    for platform in post.platforms:
        status_info = manager.get_connection_status(user.id, platform)

        connection_statuses.append(
            ConnectionCheckResponse(
                platform=platform,
                connected=status_info["connected"],
                username=status_info.get("username"),
                needs_reconnection=status_info["is_expired"],
                error=status_info.get("error"),
            )
        )

    return connection_statuses


@router.get("", response_model=List[PostResponse])
async def get_posts(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Get posts with filtering and caching.

    Caching: Enabled for unfiltered requests (status=None).
    Cache TTL: 1 minute (frequently changing data).
    """
    # Use cache only for unfiltered requests
    if status is None:
        cached_posts = await PostsCache.get_user_posts(db, user.id, skip, limit)
        return cached_posts

    # Filtered requests bypass cache
    query = db.query(Post).filter(Post.user_id == user.id)
    query = query.filter(Post.status == status)
    query = query.order_by(Post.created_at.desc())
    posts = query.offset(skip).limit(limit).all()

    return posts


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int, user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Get a single post with caching.

    Cache TTL: 5 minutes (moderate traffic, infrequent updates).
    """
    cached_post = await PostsCache.get_single_post(db, post_id, user.id)
    if not cached_post:
        raise HTTPException(status_code=404, detail="Post not found")
    return cached_post


# =========================================================================
# HELPER FUNCTIONS FOR publish_post (Function 2 Refactoring)
# =========================================================================

def _validate_platform_connections(
    platforms: List[str],
    user_id: int,
    manager: SocialConnectionManager
) -> tuple[list, dict]:
    """
    Validate that all platforms have active connections.

    Returns:
        Tuple of (missing_connections list, errors dict)
    """
    missing = []
    errors = {}

    for platform in platforms:
        status_info = manager.get_connection_status(user_id, platform)
        if not status_info["connected"]:
            missing.append(platform)
            errors[platform] = f"No {platform} connection found. Please connect your account in Settings."

    return missing, errors


def _get_platform_publisher(platform: str):
    """Get the appropriate publisher instance for a platform."""
    publishers = {
        'linkedin': LinkedInPublisher(),
        'twitter': TwitterPublisher(),
        'threads': ThreadsPublisher()
    }
    return publishers.get(platform)


def _get_platform_content(post: Post, platform: str) -> Optional[str]:
    """Get content for a specific platform from post."""
    content_map = {
        'linkedin': post.linkedin_content,
        'twitter': post.twitter_content,
        'threads': post.threads_content
    }
    return content_map.get(platform)


def _create_social_media_post_record(
    post_id: int, user_id: int, connection_id: Optional[int],
    platform: str, content: str, status: str, result: Optional[dict],
    db: Session, error: Optional[str] = None
):
    """Create a social media post record in database."""
    social_post = SocialMediaPost(
        post_id=post_id,
        user_id=user_id,
        connection_id=connection_id,
        platform=platform,
        content=content,
        status=status,
        platform_post_id=result.get("platform_post_id") if result else None,
        platform_url=result.get("platform_url") if result else None,
        published_at=datetime.utcnow() if status == "published" else None,
        error_message=error,
        created_at=datetime.utcnow()
    )
    db.add(social_post)


def _update_post_platform_url(post: Post, platform: str, url: Optional[str]):
    """Update platform-specific URL field on post."""
    if not url:
        return

    url_map = {
        'linkedin': 'linkedin_url',
        'twitter': 'twitter_url',
        'threads': 'threads_url'
    }

    if platform in url_map:
        setattr(post, url_map[platform], url)


async def _publish_to_single_platform(
    platform: str,
    post: Post,
    user: User,
    manager: SocialConnectionManager,
    db: Session
) -> tuple[Optional[dict], Optional[str]]:
    """
    Publish to a single platform.

    Returns:
        Tuple of (result dict, error string)
    """
    connection = None
    content = None

    try:
        # Get connection
        connection = manager.get_connection(user.id, platform, auto_refresh=True)
        if not connection:
            return None, f"No {platform} connection found. Please connect your account first."

        # Get token
        access_token = manager.get_decrypted_token(connection)
        if not access_token:
            return None, f"Failed to decrypt {platform} token"

        # Get content and publisher
        content = _get_platform_content(post, platform)
        if not content:
            return None, f"No content generated for {platform}"

        publisher = _get_platform_publisher(platform)
        if not publisher:
            return None, f"No publisher available for {platform}"

        # Publish
        result = await publisher.publish(content, access_token)

        # Record success
        _create_social_media_post_record(
            post.id, user.id, connection.id, platform,
            content, "published", result, db
        )

        _update_post_platform_url(post, platform, result.get("platform_url"))

        logger.info(f"Published post {post.id} to {platform} for user {user.id}")

        return {
            "success": True,
            "platform": platform,
            "message": f"Published to {platform}",
            "platform_url": result.get("platform_url")
        }, None

    except (AuthenticationException, RateLimitException, PublishingException) as e:
        logger.error(f"Error publishing to {platform}: {str(e)}")
        # Record failure
        _create_social_media_post_record(
            post.id, user.id, connection.id if connection else None,
            platform, content if content else '', "failed", None, db, error=str(e)
        )
        return None, str(e)

    except Exception as e:
        logger.error(f"Unexpected error publishing to {platform}: {str(e)}")
        return None, str(e)


def _update_post_publish_status(post: Post, results: dict, errors: dict):
    """Update post status based on publishing results."""
    if results and not errors:
        post.status = "published"
        post.published_at = datetime.utcnow()
    elif errors and not results:
        post.status = "failed"
        post.error_message = "; ".join([f"{k}: {v}" for k, v in errors.items()])
    else:
        post.status = "partially_published"


def _validate_post_and_platforms(
    post_id: int,
    user_id: int,
    platforms: List[str],
    db: Session
) -> Post:
    """
    Validate post exists and platforms are valid.

    Returns:
        Post object if valid

    Raises:
        HTTPException if validation fails
    """
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    valid_platforms = ["linkedin", "twitter", "threads"]
    invalid = [p for p in platforms if p not in valid_platforms]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid platforms: {', '.join(invalid)}")

    return post


async def _publish_to_platforms(
    platforms: List[str],
    post: Post,
    user: User,
    manager: SocialConnectionManager,
    db: Session
) -> tuple[dict, dict]:
    """
    Publish to all requested platforms.

    Returns:
        Tuple of (results dict, errors dict)
    """
    results = {}
    errors = {}

    for platform in platforms:
        result, error = await _publish_to_single_platform(platform, post, user, manager, db)
        if result:
            results[platform] = result
        if error:
            errors[platform] = error

    return results, errors


def _build_publish_response(results: dict, errors: dict) -> dict:
    """Build the final response for publishing."""
    return {
        "success": bool(results),
        "message": "Publishing complete" if results else "Publishing failed",
        "results": results,
        "errors": errors if errors else None
    }


@router.post("/publish")
async def publish_post(
    request: PublishRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """Publish post to social media platforms using OAuth connections."""
    try:
        # Validate post and platforms
        post = _validate_post_and_platforms(request.post_id, user.id, request.platforms, db)

        manager = SocialConnectionManager(db)

        # Validate connections
        missing, errors = _validate_platform_connections(request.platforms, user.id, manager)
        if missing:
            return {
                "success": False,
                "message": "Some platforms are not connected",
                "missing_connections": missing,
                "results": {},
                "errors": errors
            }

        # Publish to platforms
        results, errors = await _publish_to_platforms(request.platforms, post, user, manager, db)

        # Update post status
        _update_post_publish_status(post, results, errors)
        db.commit()

        return _build_publish_response(results, errors)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing post: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{post_id}")
async def update_post(
    post_id: int,
    twitter_content: Optional[str] = None,
    linkedin_content: Optional[str] = None,
    threads_content: Optional[str] = None,
    instagram_caption: Optional[str] = None,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Update post content with input sanitization to prevent XSS attacks
    """
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user.id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # SECURITY: Sanitize all user inputs before saving to database
    if twitter_content is not None:
        # Detect XSS attempts
        if detect_xss_attempt(twitter_content):
            raise HTTPException(
                status_code=400,
                detail="Invalid content: Potentially malicious code detected in Twitter content",
            )
        post.twitter_content = sanitize_twitter_content(twitter_content)

    if linkedin_content is not None:
        if detect_xss_attempt(linkedin_content):
            raise HTTPException(
                status_code=400,
                detail="Invalid content: Potentially malicious code detected in LinkedIn content",
            )
        post.linkedin_content = sanitize_linkedin_content(linkedin_content)

    if threads_content is not None:
        if detect_xss_attempt(threads_content):
            raise HTTPException(
                status_code=400,
                detail="Invalid content: Potentially malicious code detected in Threads content",
            )
        post.threads_content = sanitize_threads_content(threads_content)

    if instagram_caption is not None:
        if detect_xss_attempt(instagram_caption):
            raise HTTPException(
                status_code=400,
                detail="Invalid content: Potentially malicious code detected in Instagram caption",
            )
        post.instagram_caption = sanitize_instagram_caption(instagram_caption)

    db.commit()
    logger.info(f"Post {post_id} updated with sanitized content by user {user.id}")

    # Invalidate cache for updated post and user's post list
    await PostsCache.invalidate_post_and_list(post_id, user.id)

    return {"success": True}


@router.delete("/{post_id}")
async def delete_post(
    post_id: int, user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """Delete a post and invalidate cache"""
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user.id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    db.delete(post)
    db.commit()

    # Invalidate cache for deleted post and user's post list
    await PostsCache.invalidate_post_and_list(post_id, user.id)

    return {"success": True}
