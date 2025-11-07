"""
AI Post Generation API - Phase 3

Enhanced endpoints for AI-powered post generation with:
- Multi-platform generation
- Streaming responses
- Platform-specific regeneration
- Draft management
- Cache control
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum
import asyncio
import json
import logging

from database import get_db, User, Post, Article, UserApiKey
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.encryption import decrypt_api_key
from services.ai_post_generation_service import (
    AIPostGenerationService,
    AIProviderError,
    RateLimitError,
    PLATFORM_CONFIGS
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# SCHEMAS
# ============================================================================

class PlatformEnum(str, Enum):
    """Supported platforms"""
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    THREADS = "threads"


class ToneEnum(str, Enum):
    """Content tone options"""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ENGAGING = "engaging"
    FRIENDLY = "friendly"
    AUTHORITATIVE = "authoritative"


class GeneratePostRequest(BaseModel):
    """Request to generate AI posts"""
    article_ids: List[int] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="Article IDs to generate posts from (1-10)"
    )
    platforms: List[PlatformEnum] = Field(
        ...,
        min_items=1,
        description="Target platforms"
    )
    tone: Optional[ToneEnum] = Field(
        None,
        description="Content tone (defaults to platform-specific tone)"
    )
    use_cache: bool = Field(
        True,
        description="Use cached results if available"
    )

    @validator('article_ids')
    def validate_article_ids(cls, v):
        if len(set(v)) != len(v):
            raise ValueError("Duplicate article IDs not allowed")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "article_ids": [1, 2, 3],
                "platforms": ["twitter", "linkedin"],
                "tone": "professional",
                "use_cache": True
            }
        }


class RegeneratePostRequest(BaseModel):
    """Request to regenerate post for specific platform"""
    platform: PlatformEnum = Field(..., description="Platform to regenerate")
    tone: Optional[ToneEnum] = Field(None, description="Content tone")

    class Config:
        json_schema_extra = {
            "example": {
                "platform": "twitter",
                "tone": "engaging"
            }
        }


class SaveDraftRequest(BaseModel):
    """Request to save draft post"""
    article_ids: List[int] = Field(..., min_items=1)
    twitter_content: Optional[str] = None
    linkedin_content: Optional[str] = None
    instagram_content: Optional[str] = None
    threads_content: Optional[str] = None
    ai_summary: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "article_ids": [1, 2],
                "twitter_content": "Great insights on AI...",
                "linkedin_content": "In today's rapidly evolving..."
            }
        }


class GenerationResponse(BaseModel):
    """Response from post generation"""
    success: bool
    post_id: int
    results: dict
    errors: dict
    generation_time: float
    cached: bool
    remaining_requests: int


class ValidationResponse(BaseModel):
    """Content validation response"""
    is_valid: bool
    content_length: int
    max_length: int
    warnings: List[str]
    errors: List[str]
    platform: str


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_user_api_key(user_id: int, db: Session) -> tuple:
    """
    Get user's API key and provider

    Returns:
        Tuple of (api_key, provider) or raises HTTPException
    """
    user_api_keys = db.query(UserApiKey).filter(
        UserApiKey.user_id == user_id
    ).all()

    available_keys = {key.provider: key.encrypted_key for key in user_api_keys}

    # Priority: OpenAI first, then Anthropic
    for provider in ['openai', 'anthropic']:
        if provider in available_keys:
            try:
                api_key = decrypt_api_key(available_keys[provider])
                if api_key:
                    return api_key, provider
            except Exception as e:
                logger.error(f"Failed to decrypt {provider} key: {e}")
                continue

    raise HTTPException(
        status_code=400,
        detail="No API key configured. Please add your OpenAI or Anthropic API key in Profile settings."
    )


def _get_articles(article_ids: List[int], db: Session) -> List[dict]:
    """
    Get articles by IDs

    Returns:
        List of article dictionaries
    """
    articles = db.query(Article).filter(
        Article.id.in_(article_ids)
    ).all()

    if not articles:
        raise HTTPException(
            status_code=404,
            detail="No articles found with provided IDs"
        )

    return [
        {
            'id': a.id,
            'title': a.title,
            'summary': a.summary or '',
            'link': a.link,
            'source': a.source,
            'published': a.published.isoformat() if a.published else None
        }
        for a in articles
    ]


def _save_post(
    user_id: int,
    article_ids: List[int],
    results: dict,
    db: Session
) -> Post:
    """
    Save generated post to database

    Returns:
        Created Post object
    """
    # Get articles
    articles = db.query(Article).filter(
        Article.id.in_(article_ids)
    ).all()

    # Create post
    post = Post(
        user_id=user_id,
        twitter_content=results.get('twitter', {}).get('content', ''),
        linkedin_content=results.get('linkedin', {}).get('content', ''),
        threads_content=results.get('threads', {}).get('content', ''),
        instagram_caption=results.get('instagram', {}).get('content', ''),
        ai_summary='',  # Will be set if needed
        status='draft'
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    # Link articles to post
    for article in articles:
        article.post_id = post.id

    db.commit()

    return post


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/generate", response_model=GenerationResponse)
async def generate_posts(
    request: GeneratePostRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Generate AI posts for multiple platforms

    This endpoint:
    1. Validates user API key
    2. Checks rate limits
    3. Generates platform-specific content concurrently
    4. Uses cache if available (24-hour TTL)
    5. Saves to database
    6. Returns generated content with metadata

    Rate Limit: 10 generations per minute per user

    Example:
    ```json
    {
        "article_ids": [1, 2, 3],
        "platforms": ["twitter", "linkedin"],
        "tone": "professional",
        "use_cache": true
    }
    ```
    """
    try:
        # Get user API key
        api_key, provider = _get_user_api_key(user.id, db)

        # Get articles
        articles = _get_articles(request.article_ids, db)

        # Initialize AI service
        ai_service = AIPostGenerationService(api_key, provider)

        # Generate posts for all platforms
        generation_result = await ai_service.generate_multi_platform(
            articles=articles,
            platforms=[p.value for p in request.platforms],
            user_id=user.id,
            tone=request.tone.value if request.tone else None,
            use_cache=request.use_cache
        )

        # Check if any platforms succeeded
        if not generation_result['results']:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate content for all platforms. Errors: {generation_result['errors']}"
            )

        # Save to database
        post = _save_post(
            user_id=user.id,
            article_ids=request.article_ids,
            results=generation_result['results'],
            db=db
        )

        # Calculate metadata
        total_time = sum(
            r.get('generation_time', 0)
            for r in generation_result['results'].values()
        )
        is_cached = any(
            r.get('cached', False)
            for r in generation_result['results'].values()
        )
        remaining = min(
            r.get('remaining_requests', 10)
            for r in generation_result['results'].values()
        )

        logger.info(
            f"Generated {len(generation_result['results'])} posts for user {user.id}. "
            f"Post ID: {post.id}"
        )

        return GenerationResponse(
            success=True,
            post_id=post.id,
            results=generation_result['results'],
            errors=generation_result['errors'],
            generation_time=round(total_time, 2),
            cached=is_cached,
            remaining_requests=remaining
        )

    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))

    except AIProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error generating posts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate posts: {str(e)}"
        )


@router.get("/{post_id}")
async def get_post(
    post_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get post details including all platform content

    Returns:
    - Generated content for each platform
    - Metadata (tokens used, generation time)
    - Status and validation results
    """
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.user_id == user.id
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return {
        "id": post.id,
        "status": post.status,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "content": {
            "twitter": post.twitter_content or "",
            "linkedin": post.linkedin_content or "",
            "threads": post.threads_content or "",
            "instagram": post.instagram_caption or ""
        },
        "ai_summary": post.ai_summary or "",
        "error_message": post.error_message
    }


@router.post("/{post_id}/regenerate")
async def regenerate_platform_post(
    post_id: int,
    request: RegeneratePostRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Regenerate content for specific platform

    This bypasses cache and generates fresh content.
    Other platforms remain unchanged.

    Example:
    ```json
    {
        "platform": "twitter",
        "tone": "casual"
    }
    ```
    """
    try:
        # Get post
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user.id
        ).first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Get articles from post
        articles = db.query(Article).filter(
            Article.post_id == post_id
        ).all()

        if not articles:
            raise HTTPException(
                status_code=400,
                detail="No articles linked to this post"
            )

        # Get user API key
        api_key, provider = _get_user_api_key(user.id, db)

        # Initialize AI service
        ai_service = AIPostGenerationService(api_key, provider)

        # Prepare article data
        article_data = [
            {
                'id': a.id,
                'title': a.title,
                'summary': a.summary or '',
                'link': a.link
            }
            for a in articles
        ]

        # Regenerate for platform
        result = await ai_service.regenerate_post(
            articles=article_data,
            platform=request.platform.value,
            user_id=user.id,
            tone=request.tone.value if request.tone else None
        )

        # Update post in database
        platform = request.platform.value
        content = result['content']

        if platform == 'twitter':
            post.twitter_content = content
        elif platform == 'linkedin':
            post.linkedin_content = content
        elif platform == 'threads':
            post.threads_content = content
        elif platform == 'instagram':
            post.instagram_caption = content

        db.commit()

        logger.info(f"Regenerated {platform} content for post {post_id}")

        return {
            "success": True,
            "platform": platform,
            "content": content,
            "metadata": result['metadata'],
            "generation_time": result['generation_time']
        }

    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))

    except AIProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error regenerating post: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to regenerate post: {str(e)}"
        )


@router.post("/drafts")
async def save_draft(
    request: SaveDraftRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Save draft post manually

    Allows users to save draft posts without AI generation.
    Useful for manual edits or custom content.
    """
    try:
        # Get articles
        articles = db.query(Article).filter(
            Article.id.in_(request.article_ids)
        ).all()

        if not articles:
            raise HTTPException(
                status_code=404,
                detail="No articles found"
            )

        # Create post
        post = Post(
            user_id=user.id,
            twitter_content=request.twitter_content or '',
            linkedin_content=request.linkedin_content or '',
            threads_content=request.threads_content or '',
            instagram_caption=request.instagram_content or '',
            ai_summary=request.ai_summary or '',
            status='draft'
        )

        db.add(post)
        db.commit()
        db.refresh(post)

        # Link articles
        for article in articles:
            article.post_id = post.id

        db.commit()

        logger.info(f"Saved draft post {post.id} for user {user.id}")

        return {
            "success": True,
            "post_id": post.id,
            "message": "Draft saved successfully"
        }

    except Exception as e:
        logger.error(f"Error saving draft: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save draft: {str(e)}"
        )


@router.get("/drafts")
async def get_drafts(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    limit: int = 20,
    offset: int = 0
):
    """
    Get user's draft posts

    Pagination supported via limit and offset.
    """
    drafts = db.query(Post).filter(
        Post.user_id == user.id,
        Post.status == 'draft'
    ).order_by(
        Post.created_at.desc()
    ).limit(limit).offset(offset).all()

    total_count = db.query(Post).filter(
        Post.user_id == user.id,
        Post.status == 'draft'
    ).count()

    return {
        "drafts": [
            {
                "id": draft.id,
                "created_at": draft.created_at.isoformat() if draft.created_at else None,
                "has_twitter": bool(draft.twitter_content),
                "has_linkedin": bool(draft.linkedin_content),
                "has_threads": bool(draft.threads_content),
                "has_instagram": bool(draft.instagram_caption)
            }
            for draft in drafts
        ],
        "total_count": total_count,
        "limit": limit,
        "offset": offset
    }


@router.post("/validate")
async def validate_content(
    platform: PlatformEnum,
    content: str,
    user: User = Depends(get_current_user_dependency)
):
    """
    Validate content for platform requirements

    Checks:
    - Character limits
    - Platform-specific rules
    - Returns warnings and errors
    """
    try:
        # Get user API key (just to initialize service)
        api_key, provider = _get_user_api_key(user.id, Depends(get_db))

        # Initialize AI service
        ai_service = AIPostGenerationService(api_key, provider)

        # Validate content
        validation_result = await ai_service.validate_content(
            content=content,
            platform=platform.value
        )

        return ValidationResponse(**validation_result)

    except Exception as e:
        logger.error(f"Error validating content: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate content: {str(e)}"
        )


@router.get("/platforms")
async def get_platform_configs():
    """
    Get platform configurations

    Returns character limits, features, and tone for each platform.
    """
    return {
        platform: {
            "name": config.name,
            "max_length": config.max_length,
            "tone": config.tone,
            "features": config.features
        }
        for platform, config in PLATFORM_CONFIGS.items()
    }


@router.post("/cache/clear")
async def clear_cache(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Clear cached posts

    Admin users can clear all cache.
    Regular users can clear only their cache (not implemented yet).
    """
    try:
        # Get user API key to initialize service
        api_key, provider = _get_user_api_key(user.id, db)

        # Initialize AI service
        ai_service = AIPostGenerationService(api_key, provider)

        # Clear cache
        if user.is_admin:
            # Clear all cache
            cleared_count = await ai_service.clear_cache()
            message = f"Cleared {cleared_count} cached posts (all users)"
        else:
            # Clear user-specific cache (not implemented)
            cleared_count = await ai_service.clear_cache(user_id=user.id)
            message = f"Cleared {cleared_count} cached posts (your posts)"

        return {
            "success": True,
            "cleared_count": cleared_count,
            "message": message
        }

    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )


# ============================================================================
# STREAMING SUPPORT (FUTURE ENHANCEMENT)
# ============================================================================

@router.post("/generate/stream")
async def generate_posts_stream(
    request: GeneratePostRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Generate posts with streaming response

    THIS IS A PLACEHOLDER FOR FUTURE ENHANCEMENT.
    Currently returns standard response.

    Future: Will stream generation progress in real-time.
    """
    # For now, just call the regular generation endpoint
    return await generate_posts(request, user, db)
