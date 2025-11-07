"""
Post Generation Service

This service handles the async generation of social media posts with
progress tracking, error handling, and platform-specific content generation.
"""
import asyncio
import logging
import json
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from database import Article, Post
from src.summarizers import AISummarizer
from src.generators import ContentGenerator
from schemas.posts import GenerationStatus, ContentValidation, PlatformEnum

logger = logging.getLogger(__name__)


class GenerationStep:
    """Generation step definitions with progress weights"""
    INITIALIZE = ("Initializing", 0, 5)
    FETCH_ARTICLES = ("Fetching articles", 5, 15)
    GENERATE_SUMMARY = ("Generating AI summary", 15, 30)
    GENERATE_TWITTER = ("Generating Twitter content", 30, 45)
    GENERATE_LINKEDIN = ("Generating LinkedIn content", 45, 60)
    GENERATE_THREADS = ("Generating Threads content", 60, 75)
    GENERATE_INSTAGRAM = ("Generating Instagram caption", 75, 85)
    SAVE_POST = ("Saving post", 85, 95)
    VALIDATE = ("Validating content", 95, 100)
    COMPLETE = ("Complete", 100, 100)


class PostGenerationService:
    """
    Service for managing post generation lifecycle

    Handles async generation with progress tracking, error handling,
    and content validation.
    """

    # In-memory job store (use Redis in production)
    _jobs: Dict[int, Dict] = {}

    # Platform configuration
    PLATFORM_CONFIG = {
        'twitter': {'max_length': 280, 'name': 'Twitter'},
        'linkedin': {'max_length': 3000, 'name': 'LinkedIn'},
        'threads': {'max_length': 500, 'name': 'Threads'},
        'instagram': {'max_length': 2200, 'name': 'Instagram'}
    }

    @classmethod
    def create_job(cls, post_id: int) -> Dict:
        """Initialize a new generation job"""
        job = {
            "status": GenerationStatus.QUEUED,
            "progress": 0,
            "current_step": "Queued",
            "content": {},
            "validations": [],
            "error": None,
            "platform_errors": {},  # Track individual platform errors
            "started_at": datetime.utcnow(),
            "estimated_completion": None
        }
        cls._jobs[post_id] = job
        return job

    @classmethod
    def get_job(cls, post_id: int) -> Optional[Dict]:
        """Get job status"""
        return cls._jobs.get(post_id)

    @classmethod
    def update_job(cls, post_id: int, **kwargs):
        """Update job status"""
        if post_id in cls._jobs:
            cls._jobs[post_id].update(kwargs)

    @classmethod
    def delete_job(cls, post_id: int):
        """Remove completed job from memory"""
        if post_id in cls._jobs:
            del cls._jobs[post_id]

    @classmethod
    def validate_content(cls, platform: str, content: str) -> ContentValidation:
        """
        Validate generated content for a platform

        Checks character limits and provides warnings/errors
        """
        config = cls.PLATFORM_CONFIG.get(platform, {})
        max_length = config.get('max_length', 280)
        content_length = len(content)

        warnings = []
        errors = []
        is_valid = True

        # Check length
        if content_length > max_length:
            errors.append(f"Content exceeds {max_length} characters ({content_length} chars)")
            is_valid = False
        elif content_length > max_length * 0.9:
            warnings.append(f"Content is {content_length}/{max_length} characters (near limit)")

        # Platform-specific validations
        if platform == 'twitter':
            # Check for URLs
            if 'http://' in content or 'https://' in content:
                warnings.append("URLs count as 23 characters on Twitter")

            # Check for hashtags
            hashtag_count = content.count('#')
            if hashtag_count > 5:
                warnings.append(f"Using {hashtag_count} hashtags (2-3 recommended)")

        elif platform == 'linkedin':
            # Check for proper formatting
            if content.count('\n') > 20:
                warnings.append("Too many line breaks may affect readability")

            # Check for CTAs
            if len(content) > 1000 and 'http' not in content.lower():
                warnings.append("Consider adding a link or CTA for engagement")

        elif platform == 'threads':
            # Check for thread formatting
            if content.count('\n\n') > 10:
                warnings.append("Consider breaking into multiple thread posts")

        elif platform == 'instagram':
            # Check for hashtags
            hashtag_count = content.count('#')
            if hashtag_count > 30:
                errors.append(f"Instagram allows max 30 hashtags ({hashtag_count} found)")
                is_valid = False
            elif hashtag_count < 3:
                warnings.append(f"Consider adding more hashtags (found {hashtag_count}, recommended 5-10)")

            # Check for emojis (basic check)
            if not any(ord(char) > 127 for char in content):
                warnings.append("Consider adding emojis for better Instagram engagement")

        return ContentValidation(
            platform=platform,
            is_valid=is_valid,
            content_length=content_length,
            max_length=max_length,
            warnings=warnings,
            errors=errors
        )

    @classmethod
    async def generate_post_async(
        cls,
        post_id: int,
        article_ids: List[int],
        platforms: List[str],
        user_id: int,
        api_key: str,
        ai_provider: str,
        db: Session
    ):
        """
        Asynchronously generate social media posts with progress tracking

        This is the main generation workflow that:
        1. Fetches articles
        2. Generates AI summary
        3. Generates platform-specific content (Twitter, LinkedIn, Threads, Instagram)
        4. Validates content
        5. Saves to database

        Progress is tracked at each step and can be polled via the status endpoint.
        """
        try:
            # Step 1: Initialize
            cls.update_job(
                post_id,
                status=GenerationStatus.PROCESSING,
                progress=GenerationStep.INITIALIZE[2],
                current_step=GenerationStep.INITIALIZE[0]
            )

            # Set API key for AI provider
            import os
            if ai_provider == 'openai':
                os.environ['OPENAI_API_KEY'] = api_key
            elif ai_provider == 'anthropic':
                os.environ['ANTHROPIC_API_KEY'] = api_key

            # Step 2: Fetch articles
            cls.update_job(
                post_id,
                progress=GenerationStep.FETCH_ARTICLES[1],
                current_step=GenerationStep.FETCH_ARTICLES[0]
            )

            articles = db.query(Article).filter(
                Article.id.in_(article_ids)
            ).all()

            if not articles:
                cls.update_job(
                    post_id,
                    status=GenerationStatus.FAILED,
                    error="No articles found with provided IDs"
                )
                return

            # Convert to dict format
            articles_data = [
                {
                    'title': a.title,
                    'link': a.link,
                    'summary': a.summary or '',
                    'source': a.source,
                    'published': a.published
                }
                for a in articles
            ]

            logger.info(f"Generating post {post_id} from {len(articles)} articles")

            # Step 3: Generate AI summary
            cls.update_job(
                post_id,
                progress=GenerationStep.GENERATE_SUMMARY[1],
                current_step=GenerationStep.GENERATE_SUMMARY[0]
            )

            summarizer = AISummarizer(provider=ai_provider)
            summary = summarizer.summarize_articles(articles_data)

            # Step 4: Generate platform-specific content
            posts_content = {}
            validations = []
            platform_errors = {}  # Track errors per platform

            # Track progress through platforms
            platform_steps = {
                'twitter': GenerationStep.GENERATE_TWITTER,
                'linkedin': GenerationStep.GENERATE_LINKEDIN,
                'threads': GenerationStep.GENERATE_THREADS,
                'instagram': GenerationStep.GENERATE_INSTAGRAM
            }

            # Always generate Instagram caption automatically
            # (image generation remains manual in post-edit page)
            all_platforms = list(set(platforms + ['instagram']))

            for platform in all_platforms:
                step = platform_steps.get(platform)
                if step:
                    cls.update_job(
                        post_id,
                        progress=step[1],
                        current_step=step[0]
                    )

                try:
                    # Generate content for this platform
                    platform_config = {
                        platform: {
                            'enabled': True,
                            'max_length': cls.PLATFORM_CONFIG[platform]['max_length']
                        }
                    }

                    generator = ContentGenerator(summarizer, platform_config)

                    # Run in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        generator.generate_posts,
                        summary
                    )

                    # Handle Instagram special format (dict with caption/hashtags)
                    if platform == 'instagram':
                        instagram_data = result.get(platform, {})
                        if isinstance(instagram_data, dict):
                            content = instagram_data.get('caption', '')
                            posts_content['instagram'] = content

                            # FIX: Convert hashtags list to JSON string for status endpoint
                            # The status endpoint expects Dict[str, str], not Dict[str, Any]
                            hashtags = instagram_data.get('hashtags', [])
                            if isinstance(hashtags, list):
                                posts_content['instagram_hashtags'] = json.dumps(hashtags)
                            else:
                                posts_content['instagram_hashtags'] = hashtags

                            posts_content['instagram_image_prompt'] = instagram_data.get('image_prompt', '')
                        else:
                            # Fallback if format is unexpected
                            content = str(instagram_data) if instagram_data else ''
                            posts_content['instagram'] = content
                    else:
                        content = result.get(platform, '')
                        posts_content[platform] = content

                    # Check if content was actually generated
                    validation_content = posts_content.get('instagram', '') if platform == 'instagram' else content
                    if not validation_content or len(validation_content.strip()) == 0:
                        error_msg = f"No content generated for {platform}"
                        logger.warning(error_msg)
                        platform_errors[platform] = error_msg
                        # Don't fail the whole job, just mark this platform as failed
                        continue

                    # Validate content (use caption for Instagram)
                    if validation_content:
                        validation = cls.validate_content(platform, validation_content)
                        validations.append(validation)

                        # If validation failed, track it
                        if not validation.is_valid:
                            error_msg = f"Validation failed: {', '.join(validation.errors)}"
                            logger.warning(f"{platform} validation failed: {error_msg}")
                            platform_errors[platform] = error_msg

                    # Update job with partial content and errors
                    cls.update_job(
                        post_id,
                        content=posts_content.copy(),
                        platform_errors=platform_errors.copy()
                    )

                    logger.info(f"Generated {platform} content for post {post_id}: {len(validation_content)} chars")

                except Exception as e:
                    # Log the error but continue with other platforms
                    error_msg = str(e)
                    logger.error(f"Error generating {platform} content for post {post_id}: {error_msg}")
                    platform_errors[platform] = error_msg

                    # Update job with the error
                    cls.update_job(
                        post_id,
                        platform_errors=platform_errors.copy()
                    )

                    # Continue to next platform
                    continue

            # Check if at least one platform succeeded
            if not posts_content:
                cls.update_job(
                    post_id,
                    status=GenerationStatus.FAILED,
                    error="Failed to generate content for any platform. Please check your API key and try again."
                )
                return

            # Step 5: Save to database
            cls.update_job(
                post_id,
                progress=GenerationStep.SAVE_POST[1],
                current_step=GenerationStep.SAVE_POST[0]
            )

            post = db.query(Post).filter(Post.id == post_id).first()
            if post:
                post.twitter_content = posts_content.get('twitter', '')
                post.linkedin_content = posts_content.get('linkedin', '')
                post.threads_content = posts_content.get('threads', '')

                # Save Instagram caption
                post.instagram_caption = posts_content.get('instagram', '')

                # Save Instagram metadata (hashtags as JSON string)
                if 'instagram_hashtags' in posts_content:
                    # Already converted to JSON string above
                    post.instagram_hashtags = posts_content['instagram_hashtags']

                # Save image prompt for later use
                if 'instagram_image_prompt' in posts_content:
                    post.instagram_image_prompt = posts_content['instagram_image_prompt']

                post.ai_summary = summary.get('summary', '')
                post.status = 'draft'

                # If there were platform errors, add a note (but don't fail the post)
                if platform_errors:
                    failed_platforms = ', '.join(platform_errors.keys())
                    post.error_message = f"Some platforms failed: {failed_platforms}"

                db.commit()
                db.refresh(post)

            # Step 6: Final validation
            cls.update_job(
                post_id,
                progress=GenerationStep.VALIDATE[1],
                current_step=GenerationStep.VALIDATE[0],
                validations=[v.dict() for v in validations]
            )

            # Complete (even if some platforms failed)
            completion_message = "Complete"
            if platform_errors:
                completion_message = f"Complete (some platforms failed: {', '.join(platform_errors.keys())})"

            cls.update_job(
                post_id,
                status=GenerationStatus.COMPLETED,
                progress=GenerationStep.COMPLETE[1],
                current_step=completion_message
            )

            logger.info(f"Post {post_id} generation completed (including Instagram caption)")
            if platform_errors:
                logger.warning(f"Post {post_id} had platform errors: {platform_errors}")

        except Exception as e:
            import traceback
            error_msg = str(e)
            logger.error(f"Error generating post {post_id}: {error_msg}")
            logger.error(traceback.format_exc())

            cls.update_job(
                post_id,
                status=GenerationStatus.FAILED,
                error=error_msg
            )

    @classmethod
    def get_status(cls, post_id: int, db: Session) -> Dict:
        """
        Get comprehensive generation status

        Returns job status if in progress, or database status if complete
        """
        # Check in-memory job
        job = cls.get_job(post_id)

        if job:
            # Calculate estimated completion
            if job['status'] == GenerationStatus.PROCESSING:
                elapsed = (datetime.utcnow() - job['started_at']).total_seconds()
                progress = job['progress']
                if progress > 0:
                    total_estimated = (elapsed / progress) * 100
                    remaining = max(0, total_estimated - elapsed)
                    job['estimated_completion'] = int(remaining)

            # Add platform statuses based on content availability and errors
            if 'platforms' not in job:
                job['platforms'] = {}
                platform_errors = job.get('platform_errors', {})

                for platform in ['twitter', 'linkedin', 'threads', 'instagram']:
                    # Check if platform failed
                    if platform in platform_errors:
                        job['platforms'][platform] = {
                            'status': 'error',
                            'message': f'Failed: {platform_errors[platform]}'
                        }
                    # Check if platform has content
                    elif platform in job.get('content', {}):
                        job['platforms'][platform] = {
                            'status': 'completed',
                            'message': 'Caption generated' if platform == 'instagram' else 'Content generated'
                        }
                    elif job['status'] == GenerationStatus.PROCESSING:
                        # Check current step to determine platform status
                        current_step = job.get('current_step', '').lower()
                        if platform in current_step:
                            job['platforms'][platform] = {
                                'status': 'processing',
                                'message': f'Generating {"caption" if platform == "instagram" else platform.capitalize() + " content"}...'
                            }
                        else:
                            job['platforms'][platform] = {
                                'status': 'pending',
                                'message': 'Waiting...'
                            }
                    else:
                        job['platforms'][platform] = {
                            'status': 'pending',
                            'message': 'Queued'
                        }

            return job

        # If not in jobs, check database
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return None

        # Build platform statuses based on database content
        platforms = {}
        for platform in ['twitter', 'linkedin', 'threads', 'instagram']:
            if platform == 'instagram':
                content = post.instagram_caption
            else:
                content = getattr(post, f'{platform}_content', None)

            if content:
                platforms[platform] = {
                    'status': 'completed',
                    'message': 'Caption generated' if platform == 'instagram' else 'Ready'
                }
            else:
                platforms[platform] = {
                    'status': 'error' if post.error_message else 'pending',
                    'message': 'Failed' if post.error_message else 'Not generated'
                }

        # Return database state
        return {
            "status": GenerationStatus.COMPLETED if post.status == "draft" else GenerationStatus.FAILED,
            "progress": 100 if post.status == "draft" else 0,
            "current_step": "Complete" if post.status == "draft" else "Not started",
            "content": {
                "twitter": post.twitter_content or "",
                "linkedin": post.linkedin_content or "",
                "threads": post.threads_content or "",
                "instagram": post.instagram_caption or "",
                "summary": post.ai_summary or ""
            },
            "platforms": platforms,
            "validations": [],
            "error": post.error_message,
            "started_at": post.created_at,
            "estimated_completion": None
        }
