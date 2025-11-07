"""
Posts API v2 - Enhanced with improved generation flow

This module provides enhanced endpoints for:
- Async post generation with progress tracking
- Platform status checking
- Content validation
- Publishing with comprehensive error handling
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import asyncio
import logging

from database import get_db, Post, Article, User
from database_social_media import SocialMediaPost
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.social_connection_manager import SocialConnectionManager
from src.publishers import LinkedInPublisher, ThreadsPublisher
from src.publishers.twitter_publisher_oauth1 import TwitterPublisherUnified
from src.publishers.exceptions import AuthenticationException, RateLimitException, PublishingException

# Import schemas
from schemas.posts import (
    GenerateRequest, GenerateResponse, GenerationStatusResponse,
    PostEditResponse, PublishRequest, PublishResponse, PublishResult,
    PostResponse, UpdatePostRequest, ErrorResponse,
    PlatformConnectionStatus, ContentValidation, GenerationStatus
)

# Import services
from services.post_generation_service import PostGenerationService
from services.platform_status_service import PlatformStatusService

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# POST GENERATION ENDPOINTS
# ============================================================================

@router.post("/generate", response_model=GenerateResponse)
async def generate_post(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Start async post generation

    This endpoint immediately returns a post ID and starts generation in the background.
    Use GET /api/posts/generation/{post_id}/status to poll for progress.

    Flow:
    1. Validates article IDs and platforms
    2. Creates post record with 'processing' status
    3. Starts async generation task
    4. Returns post_id for status polling

    Errors:
    - 400: Invalid request (bad article IDs, platforms)
    - 400: No API key configured
    - 404: Articles not found
    """
    try:
        # Get API key from user settings
        api_key, ai_provider = _get_user_api_key(user.id, db)

        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="No API key configured. Please add your OpenAI or Anthropic API key in Profile settings."
            )

        # Validate articles exist
        articles = _validate_articles(request.article_ids, db)

        # Create post record
        post = _create_post_record(user.id, articles, request.platforms, db)

        # Initialize generation job
        PostGenerationService.create_job(post.id)

        # Start background task with new DB session
        from database import SessionLocal
        background_db = SessionLocal()

        asyncio.create_task(
            PostGenerationService.generate_post_async(
                post.id,
                request.article_ids,
                [p.value for p in request.platforms],
                user.id,
                api_key,
                ai_provider,
                background_db
            )
        )

        return GenerateResponse(
            success=True,
            post_id=post.id,
            status=GenerationStatus.PROCESSING,
            message=f"Post generation started. Poll /api/posts/generation/{post.id}/status for progress."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting post generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start generation: {str(e)}"
        )


def _get_user_api_key(user_id: int, db: Session) -> tuple[Optional[str], Optional[str]]:
    """
    Extract user API key retrieval logic

    Returns (api_key, ai_provider) tuple
    """
    from database import UserApiKey, Settings
    from utils.encryption import decrypt_api_key
    import os

    user_api_keys = db.query(UserApiKey).filter(
        UserApiKey.user_id == user_id
    ).all()

    available_keys = {key.provider: key.encrypted_key for key in user_api_keys}

    api_key = None
    ai_provider = None

    # Priority order: OpenAI first, then Anthropic
    for provider in ['openai', 'anthropic']:
        if provider in available_keys:
            try:
                api_key = decrypt_api_key(available_keys[provider])
                if api_key:
                    ai_provider = provider
                    break
            except Exception as e:
                logger.error(f"Failed to decrypt {provider} key: {e}")
                continue

    # Fallback to global settings
    if not api_key:
        api_key, ai_provider = _get_global_api_key(db)

    return api_key, ai_provider


def _get_global_api_key(db: Session) -> tuple[Optional[str], Optional[str]]:
    """Get API key from global Settings table"""
    from database import Settings
    from cryptography.fernet import Fernet
    import os

    ai_provider_setting = db.query(Settings).filter(
        Settings.key == 'ai_provider'
    ).first()
    api_key_setting = db.query(Settings).filter(
        Settings.key == 'api_key'
    ).first()

    if api_key_setting and api_key_setting.value:
        ai_provider = ai_provider_setting.value if ai_provider_setting else 'openai'
        ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())
        cipher_suite = Fernet(ENCRYPTION_KEY.encode())
        try:
            api_key = cipher_suite.decrypt(api_key_setting.value.encode()).decode()
            return api_key, ai_provider
        except Exception as decrypt_error:
            logger.error(f"Failed to decrypt Settings API key: {decrypt_error}")

    return None, None


def _validate_articles(article_ids: List[int], db: Session) -> List[Article]:
    """Validate that articles exist and return them"""
    articles = db.query(Article).filter(
        Article.id.in_(article_ids)
    ).all()

    if not articles:
        raise HTTPException(
            status_code=404,
            detail="No articles found with provided IDs"
        )

    if len(articles) != len(article_ids):
        found_ids = {a.id for a in articles}
        missing_ids = set(article_ids) - found_ids
        raise HTTPException(
            status_code=404,
            detail=f"Articles not found: {missing_ids}"
        )

    return articles


def _create_post_record(user_id: int, articles: List[Article], platforms: List, db: Session) -> Post:
    """Create initial post record with 'processing' status"""
    post = Post(
        user_id=user_id,
        article_title=articles[0].title if len(articles) == 1 else f"{len(articles)} articles",
        twitter_content='',
        linkedin_content='',
        threads_content='',
        platforms=[p.value for p in platforms],
        status='processing',
        ai_summary=''
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    return post


@router.get("/generation/{post_id}/status", response_model=GenerationStatusResponse)
async def get_generation_status(
    post_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Poll generation status

    Returns current progress, step, and partial content.
    Poll this endpoint every 1-2 seconds until status is 'completed' or 'failed'.

    Response includes:
    - status: queued, processing, completed, failed
    - progress: 0-100
    - current_step: Human-readable step description
    - content: Partial/complete generated content
    - platforms: Per-platform generation status
    - validations: Content validation results
    - error: Error message if failed
    - estimated_completion_seconds: Estimated time remaining
    """
    # Verify post belongs to user
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.user_id == user.id
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Get status from service
    status = PostGenerationService.get_status(post_id, db)

    if not status:
        raise HTTPException(status_code=404, detail="Generation status not found")

    # Clean up completed jobs
    if status['status'] == GenerationStatus.COMPLETED:
        PostGenerationService.delete_job(post_id)

    return GenerationStatusResponse(
        post_id=post_id,
        status=status['status'],
        progress=status['progress'],
        current_step=status['current_step'],
        content=status.get('content', {}),
        platforms=status.get('platforms', {}),  # FIX: Include platforms field
        validations=status.get('validations', []),
        error=status.get('error'),
        estimated_completion_seconds=status.get('estimated_completion')
    )


# ============================================================================
# POST EDIT ENDPOINTS
# ============================================================================

@router.get("/{post_id}/edit", response_model=PostEditResponse)
async def get_post_for_edit(
    post_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get post with platform status for editing

    Returns:
    - Post content for all platforms
    - Instagram image URL and prompt (for persistence)
    - OAuth connection status for each platform
    - Content validation results
    - Platform readiness to publish

    Use this endpoint to populate the edit page after generation completes.
    The instagram_image_url field ensures generated images are reloaded when
    users return to edit the post later.
    """
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.user_id == user.id
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Get platform statuses
    platform_statuses = PlatformStatusService.get_post_platform_statuses(
        post_id, user.id, db
    )

    # Get content validations
    validations = PlatformStatusService.validate_post_content(post_id, db)

    return PostEditResponse(
        id=post.id,
        article_title=post.article_title,
        created_at=post.created_at,
        status=post.status,
        twitter_content=post.twitter_content,
        linkedin_content=post.linkedin_content,
        threads_content=post.threads_content,
        instagram_caption=post.instagram_caption,
        instagram_image_url=post.instagram_image_url,  # FIX: Include image URL for persistence
        instagram_image_prompt=post.instagram_image_prompt,  # FIX: Include prompt for reference
        platform_statuses=platform_statuses,
        validations=list(validations.values()),
        ai_summary=post.ai_summary,
        platforms=post.platforms or []
    )


@router.patch("/{post_id}", response_model=dict)
async def update_post(
    post_id: int,
    request: UpdatePostRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Update post content and status

    Allows editing of platform-specific content before publishing.
    Validates content length for each platform:
    - Twitter: 280 characters max
    - LinkedIn: 3000 characters max
    - Threads: 500 characters max

    Also supports updating post status (draft, ready, scheduled, published).

    Args:
        post_id: ID of post to update
        request: Update request with optional content and status fields

    Returns:
        Success response with updated status

    Raises:
        404: Post not found or doesn't belong to user
        422: Validation error (content exceeds platform limits)
    """
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.user_id == user.id
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Track what was updated for logging
    updated_fields = []

    # Update content
    if request.twitter_content is not None:
        post.twitter_content = request.twitter_content
        updated_fields.append(f"twitter({len(request.twitter_content)} chars)")

    if request.linkedin_content is not None:
        post.linkedin_content = request.linkedin_content
        updated_fields.append(f"linkedin({len(request.linkedin_content)} chars)")

    if request.threads_content is not None:
        post.threads_content = request.threads_content
        updated_fields.append(f"threads({len(request.threads_content)} chars)")

    if request.instagram_caption is not None:
        post.instagram_caption = request.instagram_caption
        updated_fields.append(f"instagram({len(request.instagram_caption)} chars)")

    # Update status if provided
    if request.status is not None:
        post.status = request.status
        updated_fields.append(f"status={request.status}")

    db.commit()

    # Log successful update
    logger.info(
        f"Post {post_id} updated by user {user.id}: {', '.join(updated_fields)}"
    )

    return {
        "success": True,
        "message": "Post updated successfully",
        "status": post.status
    }


# ============================================================================
# PLATFORM STATUS ENDPOINTS
# ============================================================================

@router.get("/{post_id}/platform-status", response_model=List[PlatformConnectionStatus])
async def get_post_platform_status(
    post_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get platform connection status for a post

    Returns OAuth connection status, token validity, and publish readiness
    for each platform associated with the post.

    Use this to check if user needs to reconnect before publishing.
    """
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.user_id == user.id
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    statuses = PlatformStatusService.get_post_platform_statuses(
        post_id, user.id, db
    )

    return statuses


# ============================================================================
# PUBLISHING ENDPOINTS
# ============================================================================

@router.post("/publish", response_model=PublishResponse)
async def publish_post(
    request: PublishRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Publish post to selected platforms

    This endpoint:
    1. Validates platform connections
    2. Checks content for each platform
    3. Publishes to each platform
    4. Tracks success/failure per platform
    5. Updates post status

    Handles partial failures gracefully - if Twitter succeeds but LinkedIn fails,
    the post will be marked as 'partially_published' with detailed error info.

    Returns:
    - success: Overall success (true if at least one platform succeeded)
    - results: Publishing results per platform
    - errors: Error messages per platform
    - missing_connections: Platforms that need OAuth connection
    """
    try:
        post = _verify_post_ownership(request.post_id, user.id, db)
        platforms = [p.value for p in request.platforms]

        # Check publish readiness
        readiness_check = _check_publish_readiness(user.id, platforms, db)
        if not readiness_check['ready']:
            return readiness_check['response']

        # Get publishing errors (validation, etc)
        validation_errors = PlatformStatusService.get_publishing_errors(
            user.id, request.post_id, platforms, db
        )

        if validation_errors:
            return PublishResponse(
                success=False,
                message="Content validation failed",
                errors=validation_errors
            )

        # Publish to each platform
        results, errors = await _publish_to_platforms(post, platforms, user.id, db)

        # Update post status
        _update_post_status_after_publish(post, results, errors, db)

        return PublishResponse(
            success=bool(results),
            message=f"Published to {len(results)} platform(s)" if results else "Publishing failed",
            results=results,
            errors=errors if errors else None,
            published_count=len(results),
            failed_count=len(errors)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in publish endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _verify_post_ownership(post_id: int, user_id: int, db: Session) -> Post:
    """Verify post exists and belongs to user"""
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.user_id == user_id
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return post


def _check_publish_readiness(user_id: int, platforms: List[str], db: Session) -> dict:
    """
    Check if user can publish to requested platforms

    Returns dict with 'ready' flag and optional 'response' for early return
    """
    readiness = PlatformStatusService.check_publish_readiness(
        user_id, platforms, db
    )

    if not readiness['ready']:
        return {
            'ready': False,
            'response': PublishResponse(
                success=False,
                message="Cannot publish: missing or expired connections",
                missing_connections=readiness['missing_connections'],
                errors={
                    **{p: "Connection required" for p in readiness['missing_connections']},
                    **{p: "Token expired" for p in readiness['expired_connections']}
                }
            )
        }

    return {'ready': True}


async def _publish_to_platforms(
    post: Post,
    platforms: List[str],
    user_id: int,
    db: Session
) -> tuple[dict, dict]:
    """
    Publish to each platform and track results

    Returns (results, errors) tuple
    """
    manager = SocialConnectionManager(db)
    results = {}
    errors = {}

    for platform in platforms:
        try:
            # Get connection with auto-refresh
            connection = manager.get_connection(user_id, platform, auto_refresh=True)

            if not connection:
                errors[platform] = f"No {platform} connection found"
                continue

            # Get decrypted token
            access_token = manager.get_decrypted_token(connection)
            if not access_token:
                errors[platform] = f"Failed to decrypt {platform} token"
                continue

            # Get content and publisher
            content, publisher = _get_content_and_publisher(platform, post)

            if not content:
                errors[platform] = f"No content for {platform}"
                continue

            # Get access token secret for Twitter OAuth 1.0a
            access_token_secret = _get_twitter_token_secret(platform, connection) if platform == "twitter" else None

            # Publish to platform
            result = await _publish_single_platform(
                platform, publisher, content, access_token, access_token_secret, user_id
            )

            # Record success
            _record_publish_success(post, platform, connection, content, result, db)
            results[platform] = PublishResult(
                success=True,
                platform=platform,
                message=f"Published successfully",
                platform_url=result.get("platform_url"),
                platform_post_id=result.get("platform_post_id")
            )

            logger.info(f"Published post {post.id} to {platform}")

        except (AuthenticationException, RateLimitException, PublishingException) as e:
            logger.error(f"Publishing error on {platform}: {e}")
            error_message = _format_platform_error(platform, e)
            errors[platform] = error_message

            # Record failure
            _record_publish_failure(post, platform, connection, content, error_message, db)

        except Exception as e:
            logger.error(f"Unexpected error publishing to {platform}: {e}", exc_info=True)
            errors[platform] = f"Unexpected error: {str(e)}"

    return results, errors


def _get_content_and_publisher(platform: str, post: Post) -> tuple[Optional[str], Optional[object]]:
    """Get content and publisher for a specific platform"""
    if platform == "linkedin":
        return post.linkedin_content, LinkedInPublisher()
    elif platform == "twitter":
        return post.twitter_content, TwitterPublisherUnified()
    elif platform == "threads":
        return post.threads_content, ThreadsPublisher()

    return None, None


def _get_twitter_token_secret(platform: str, connection) -> Optional[str]:
    """Get OAuth 1.0a access token secret for Twitter"""
    if platform == "twitter" and connection.encrypted_refresh_token:
        from utils.encryption import decrypt_value
        access_token_secret = decrypt_value(connection.encrypted_refresh_token)
        if access_token_secret:
            logger.info(f"Retrieved OAuth 1.0a credentials for Twitter publishing")
        else:
            logger.warning(f"Failed to decrypt access_token_secret for Twitter")
        return access_token_secret
    return None


async def _publish_single_platform(
    platform: str,
    publisher,
    content: str,
    access_token: str,
    access_token_secret: Optional[str],
    user_id: int
) -> dict:
    """Publish to a single platform"""
    if platform == "twitter":
        # TwitterPublisherUnified auto-detects OAuth version based on parameters
        return await publisher.publish(content, access_token, access_token_secret, user_id=user_id)
    else:
        return await publisher.publish(content, access_token)


def _format_platform_error(platform: str, exception: Exception) -> str:
    """Format platform-specific error messages"""
    error_message = str(exception)

    if platform == "twitter" and isinstance(exception, AuthenticationException):
        if "403" in error_message or "Forbidden" in error_message:
            return "Twitter authentication failed. Please reconnect your Twitter account."

    return error_message


def _record_publish_success(
    post: Post,
    platform: str,
    connection,
    content: str,
    result: dict,
    db: Session
):
    """Record successful publish to database"""
    social_post = SocialMediaPost(
        post_id=post.id,
        user_id=post.user_id,
        connection_id=connection.id,
        platform=platform,
        content=content,
        status="published",
        platform_post_id=result.get("platform_post_id"),
        platform_url=result.get("platform_url"),
        published_at=datetime.utcnow()
    )
    db.add(social_post)

    # Update post URLs
    if platform == "linkedin":
        post.linkedin_url = result.get("platform_url")
    elif platform == "twitter":
        post.twitter_url = result.get("platform_url")
    elif platform == "threads":
        post.threads_url = result.get("platform_url")


def _record_publish_failure(
    post: Post,
    platform: str,
    connection,
    content: str,
    error_message: str,
    db: Session
):
    """Record failed publish attempt to database"""
    social_post = SocialMediaPost(
        post_id=post.id,
        user_id=post.user_id,
        connection_id=connection.id if connection else None,
        platform=platform,
        content=content or "",
        status="failed",
        error_message=error_message,
        created_at=datetime.utcnow()
    )
    db.add(social_post)


def _update_post_status_after_publish(post: Post, results: dict, errors: dict, db: Session):
    """Update post status based on publish results"""
    if results and not errors:
        post.status = "published"
        post.published_at = datetime.utcnow()
    elif errors and not results:
        post.status = "failed"
        post.error_message = "; ".join([f"{k}: {v}" for k, v in errors.items()])
    else:
        post.status = "partially_published"
        post.error_message = "; ".join([f"{k}: {v}" for k, v in errors.items()])

    db.commit()


# ============================================================================
# BASIC CRUD ENDPOINTS
# ============================================================================

@router.get("", response_model=List[PostResponse])
async def get_posts(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get user's posts with filtering"""
    query = db.query(Post).filter(Post.user_id == user.id)

    if status:
        query = query.filter(Post.status == status)

    query = query.order_by(Post.created_at.desc())
    posts = query.offset(skip).limit(limit).all()

    return posts


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get a single post"""
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.user_id == user.id
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return post


@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Delete a post"""
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.user_id == user.id
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    db.delete(post)
    db.commit()

    return {"success": True, "message": "Post deleted"}
