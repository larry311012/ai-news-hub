"""
Pydantic schemas for post generation and publishing

These schemas provide request/response validation and documentation
for the post generation API endpoints.
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class PlatformEnum(str, Enum):
    """Supported social media platforms"""
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    THREADS = "threads"
    INSTAGRAM = "instagram"


class GenerationStatus(str, Enum):
    """Post generation status states"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PublishStatus(str, Enum):
    """Publishing status states"""
    DRAFT = "draft"
    PROCESSING = "processing"
    PUBLISHED = "published"
    PARTIALLY_PUBLISHED = "partially_published"
    FAILED = "failed"


class GenerateRequest(BaseModel):
    """Request to generate social media posts"""
    article_ids: List[int] = Field(..., min_length=1, max_length=10, description="Article IDs to generate posts from (1-10)")
    platforms: List[PlatformEnum] = Field(..., min_length=1, description="Platforms to generate content for")

    @field_validator('article_ids')
    @classmethod
    def validate_article_ids(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError("At least one article ID is required")
        if len(v) > 10:
            raise ValueError("Maximum 10 articles allowed per generation")
        if len(set(v)) != len(v):
            raise ValueError("Duplicate article IDs not allowed")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "article_ids": [1, 2, 3],
                "platforms": ["twitter", "linkedin"]
            }
        }
    )


class GenerateResponse(BaseModel):
    """Response from post generation request"""
    success: bool
    post_id: int
    status: GenerationStatus
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "post_id": 42,
                "status": "processing",
                "message": "Post generation started. Poll /api/posts/42/status for progress."
            }
        }
    )


class GenerationStepInfo(BaseModel):
    """Information about current generation step"""
    step_name: str
    description: str
    progress: int = Field(..., ge=0, le=100)


class ContentValidation(BaseModel):
    """Content validation result for a platform"""
    platform: PlatformEnum
    is_valid: bool
    content_length: int
    max_length: int
    warnings: List[str] = []
    errors: List[str] = []


class PlatformContent(BaseModel):
    """Generated content for a single platform"""
    platform: PlatformEnum
    content: str
    validation: Optional[ContentValidation] = None


class PlatformGenerationStatus(BaseModel):
    """Status of generation for a specific platform"""
    status: str  # pending, processing, complete, error
    message: str


class GenerationStatusResponse(BaseModel):
    """Response for generation status polling"""
    post_id: int
    status: GenerationStatus
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    current_step: str
    step_info: Optional[GenerationStepInfo] = None
    content: Dict[str, str] = Field(default_factory=dict, description="Generated content by platform")
    platforms: Dict[str, PlatformGenerationStatus] = Field(default_factory=dict, description="Per-platform generation status")
    validations: List[ContentValidation] = Field(default_factory=list)
    error: Optional[str] = None
    estimated_completion_seconds: Optional[int] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "post_id": 42,
                "status": "processing",
                "progress": 75,
                "current_step": "Generating LinkedIn content",
                "content": {
                    "twitter": "AI breakthrough in language models...",
                    "linkedin": "Detailed analysis of the latest AI developments..."
                },
                "validations": [],
                "error": None,
                "estimated_completion_seconds": 15
            }
        }
    )


class PlatformConnectionStatus(BaseModel):
    """OAuth connection status for a platform"""
    platform: PlatformEnum
    connected: bool
    username: Optional[str] = None
    needs_reconnection: bool = False
    is_expired: bool = False
    last_used: Optional[datetime] = None
    error: Optional[str] = None
    can_publish: bool = False


class PostEditResponse(BaseModel):
    """Response for post edit endpoint"""
    id: int
    article_title: Optional[str] = None
    created_at: datetime
    status: str

    # Platform content
    twitter_content: Optional[str] = None
    linkedin_content: Optional[str] = None
    threads_content: Optional[str] = None
    instagram_caption: Optional[str] = None

    # Instagram image support - CRITICAL for image persistence
    instagram_image_url: Optional[str] = None
    instagram_image_prompt: Optional[str] = None

    # Connection status
    platform_statuses: List[PlatformConnectionStatus]

    # Validations
    validations: List[ContentValidation]

    # Metadata
    ai_summary: Optional[str] = None
    platforms: List[str]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 42,
                "article_title": "AI Breakthrough in NLP",
                "created_at": "2025-10-19T12:00:00Z",
                "status": "draft",
                "twitter_content": "AI breakthrough...",
                "linkedin_content": "Detailed analysis...",
                "threads_content": "Thread about AI...",
                "instagram_caption": "Instagram post with hashtags...",
                "instagram_image_url": "/api/images/instagram/6/post_42_1234567890.png",
                "instagram_image_prompt": "A modern digital illustration...",
                "platform_statuses": [
                    {
                        "platform": "twitter",
                        "connected": True,
                        "username": "@example",
                        "needs_reconnection": False,
                        "can_publish": True
                    }
                ],
                "validations": [],
                "ai_summary": "Summary of articles...",
                "platforms": ["twitter", "linkedin"]
            }
        }
    )


class PublishRequest(BaseModel):
    """Request to publish post to platforms"""
    post_id: int
    platforms: List[PlatformEnum] = Field(..., min_length=1)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "post_id": 42,
                "platforms": ["twitter", "linkedin"]
            }
        }
    )


class PublishResult(BaseModel):
    """Result of publishing to a single platform"""
    success: bool
    platform: PlatformEnum
    message: str
    platform_url: Optional[str] = None
    platform_post_id: Optional[str] = None
    error: Optional[str] = None


class PublishResponse(BaseModel):
    """Response from publish request"""
    success: bool
    message: str
    results: Dict[str, PublishResult] = Field(default_factory=dict)
    errors: Optional[Dict[str, str]] = None
    missing_connections: List[str] = Field(default_factory=list)
    published_count: int = 0
    failed_count: int = 0

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Published to 2 platforms",
                "results": {
                    "twitter": {
                        "success": True,
                        "platform": "twitter",
                        "message": "Published successfully",
                        "platform_url": "https://twitter.com/user/status/123"
                    }
                },
                "errors": None,
                "missing_connections": [],
                "published_count": 2,
                "failed_count": 0
            }
        }
    )


class PostResponse(BaseModel):
    """Basic post response"""
    id: int
    article_title: Optional[str] = None
    twitter_content: Optional[str] = None
    linkedin_content: Optional[str] = None
    threads_content: Optional[str] = None
    instagram_caption: Optional[str] = None
    platforms: List[str]
    status: str
    created_at: datetime
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UpdatePostRequest(BaseModel):
    """
    Request to update post content

    Validates platform-specific character limits:
    - Twitter: 280 characters
    - LinkedIn: 3000 characters
    - Threads: 500 characters
    - Instagram: 2200 characters

    Supports updating post status (draft, ready, scheduled, published)
    """
    twitter_content: Optional[str] = None
    linkedin_content: Optional[str] = None
    threads_content: Optional[str] = None
    instagram_caption: Optional[str] = None
    status: Optional[str] = Field(
        None,
        description="Post status (draft, ready, scheduled, published)"
    )

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate post status is one of allowed values"""
        if v is not None:
            allowed_statuses = ['draft', 'ready', 'scheduled', 'published']
            if v not in allowed_statuses:
                raise ValueError(
                    f"Invalid status '{v}'. Must be one of: {', '.join(allowed_statuses)}"
                )
        return v

    @field_validator('twitter_content')
    @classmethod
    def validate_twitter_content(cls, v: Optional[str]) -> Optional[str]:
        """Validate Twitter content length (280 character limit)"""
        if v is not None and len(v) > 280:
            over_by = len(v) - 280
            raise ValueError(
                f"Twitter content is {over_by} character{'s' if over_by > 1 else ''} too long. "
                f"Current: {len(v)} characters, Maximum: 280 characters. "
                f"Please shorten your tweet by {over_by} character{'s' if over_by > 1 else ''}."
            )
        return v

    @field_validator('linkedin_content')
    @classmethod
    def validate_linkedin_content(cls, v: Optional[str]) -> Optional[str]:
        """Validate LinkedIn content length (3000 character limit)"""
        if v is not None and len(v) > 3000:
            over_by = len(v) - 3000
            raise ValueError(
                f"LinkedIn content is {over_by} character{'s' if over_by > 1 else ''} too long. "
                f"Current: {len(v)} characters, Maximum: 3000 characters. "
                f"Please shorten your post by {over_by} character{'s' if over_by > 1 else ''}."
            )
        return v

    @field_validator('threads_content')
    @classmethod
    def validate_threads_content(cls, v: Optional[str]) -> Optional[str]:
        """Validate Threads content length (500 character limit)"""
        if v is not None and len(v) > 500:
            over_by = len(v) - 500
            raise ValueError(
                f"Threads content is {over_by} character{'s' if over_by > 1 else ''} too long. "
                f"Current: {len(v)} characters, Maximum: 500 characters. "
                f"Please shorten your thread by {over_by} character{'s' if over_by > 1 else ''}."
            )
        return v

    @field_validator('instagram_caption')
    @classmethod
    def validate_instagram_caption(cls, v: Optional[str]) -> Optional[str]:
        """Validate Instagram caption length (2200 character limit)"""
        if v is not None and len(v) > 2200:
            over_by = len(v) - 2200
            raise ValueError(
                f"Instagram caption is {over_by} character{'s' if over_by > 1 else ''} too long. "
                f"Current: {len(v)} characters, Maximum: 2200 characters. "
                f"Please shorten your caption by {over_by} character{'s' if over_by > 1 else ''}."
            )
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "twitter_content": "Updated tweet content here",
                "linkedin_content": "Updated LinkedIn post content",
                "threads_content": "Updated Threads content",
                "instagram_caption": "Updated Instagram caption with hashtags #example #instagram",
                "status": "draft"
            }
        }
    )


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": "No API key configured",
                "error_code": "API_KEY_MISSING",
                "details": {
                    "required_action": "Add API key in Profile settings"
                }
            }
        }
    )
