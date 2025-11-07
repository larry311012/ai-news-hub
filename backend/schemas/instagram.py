"""
Instagram Schemas - Pydantic models for Instagram API endpoints

This module defines request/response schemas for Instagram image generation
and publishing functionality.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ImageGenerationStatus(str, Enum):
    """Image generation job status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImageStyle(str, Enum):
    """Predefined image styles"""
    MODERN = "modern"
    MINIMALIST = "minimalist"
    VIBRANT = "vibrant"
    PROFESSIONAL = "professional"
    ABSTRACT = "abstract"
    FUTURISTIC = "futuristic"


class ImageProvider(str, Enum):
    """AI image generation providers"""
    OPENAI = "openai"
    STABLE_DIFFUSION = "stable-diffusion"
    MIDJOURNEY = "midjourney"


class InstagramPublishStatus(str, Enum):
    """Instagram publishing status"""
    INITIATED = "initiated"
    CONTAINER_CREATED = "container_created"
    PUBLISHED = "published"
    FAILED = "failed"


# ============================================================================
# IMAGE GENERATION REQUESTS
# ============================================================================

class GenerateImageRequest(BaseModel):
    """Request to generate Instagram image"""
    regenerate: bool = Field(
        default=False,
        description="Force regenerate even if cached image exists"
    )
    style: Optional[ImageStyle] = Field(
        default=ImageStyle.MODERN,
        description="Image style preset"
    )
    custom_prompt: Optional[str] = Field(
        default=None,
        max_length=400,
        description="User-provided custom prompt (overrides auto-generated)"
    )
    size: Optional[str] = Field(
        default="1024x1024",
        description="Image dimensions (1024x1024, 1792x1024, 1024x1792)"
    )
    quality: Optional[str] = Field(
        default="standard",
        description="Image quality (standard, hd)"
    )

    @field_validator('size')
    @classmethod
    def validate_size(cls, v: str) -> str:
        """Validate image size is supported"""
        valid_sizes = ["1024x1024", "1792x1024", "1024x1792"]
        if v not in valid_sizes:
            raise ValueError(f"Size must be one of {valid_sizes}")
        return v

    @field_validator('quality')
    @classmethod
    def validate_quality(cls, v: str) -> str:
        """Validate quality setting"""
        valid_qualities = ["standard", "hd"]
        if v not in valid_qualities:
            raise ValueError(f"Quality must be one of {valid_qualities}")
        return v


class RegenerateImageRequest(BaseModel):
    """Request to regenerate image with new parameters"""
    style: Optional[ImageStyle] = Field(
        default=None,
        description="New style to apply"
    )
    custom_prompt: Optional[str] = Field(
        default=None,
        max_length=400,
        description="New custom prompt"
    )


# ============================================================================
# IMAGE GENERATION RESPONSES
# ============================================================================

class GenerateImageResponse(BaseModel):
    """Response when starting image generation"""
    success: bool
    message: str
    job_id: str = Field(description="Unique job ID for status polling")
    post_id: int
    estimated_seconds: int = Field(default=15)
    status_url: str = Field(description="URL to poll for status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Image generation started",
                "job_id": "img_gen_abc123",
                "post_id": 123,
                "estimated_seconds": 15,
                "status_url": "/api/posts/123/instagram-image/status"
            }
        }
    )


class ImageStatusResponse(BaseModel):
    """Response for image generation status polling"""
    status: ImageGenerationStatus
    progress: int = Field(ge=0, le=100)
    current_step: Optional[str] = None
    job_id: str

    # Results (when completed)
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    prompt: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size_bytes: Optional[int] = None
    cached: bool = Field(default=False)

    # Error info (when failed)
    error: Optional[str] = None
    error_code: Optional[str] = None

    # Timing
    generation_time_seconds: Optional[float] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "completed",
                "progress": 100,
                "current_step": "Image generation complete",
                "job_id": "img_gen_abc123",
                "image_url": "/api/images/instagram/123_1698765432.png",
                "thumbnail_url": "/api/images/instagram/123_1698765432_thumb.png",
                "prompt": "Modern abstract visualization of AI neural networks...",
                "width": 1024,
                "height": 1024,
                "file_size_bytes": 1234567,
                "cached": False,
                "generation_time_seconds": 12.5
            }
        }
    )


class ImageMetadataResponse(BaseModel):
    """Detailed image metadata"""
    image_id: int
    post_id: int
    user_id: int
    article_id: Optional[int] = None

    # Image info
    image_url: str
    thumbnail_url: Optional[str] = None
    prompt: str
    prompt_hash: str
    width: int
    height: int
    format: str
    file_size_bytes: int

    # AI metadata
    ai_provider: str
    ai_model: str
    generation_params: Optional[Dict[str, Any]] = None

    # Usage tracking
    times_used: int
    last_used_at: Optional[datetime] = None

    # Status
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# INSTAGRAM PUBLISHING REQUESTS
# ============================================================================

class InstagramPublishRequest(BaseModel):
    """Request to publish to Instagram"""
    post_id: int
    image_id: Optional[int] = Field(
        default=None,
        description="Specific image to use (defaults to post's instagram_image)"
    )
    caption: Optional[str] = Field(
        default=None,
        max_length=2200,
        description="Custom caption (overrides post.instagram_caption)"
    )
    location_id: Optional[str] = Field(
        default=None,
        description="Instagram location ID"
    )
    user_tags: Optional[List[str]] = Field(
        default=None,
        description="List of Instagram usernames to tag"
    )

    @field_validator('caption')
    @classmethod
    def validate_caption_length(cls, v: Optional[str]) -> Optional[str]:
        """Ensure caption doesn't exceed Instagram's limit"""
        if v and len(v) > 2200:
            raise ValueError("Caption must be 2200 characters or less")
        return v

    @field_validator('user_tags')
    @classmethod
    def validate_user_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate user tags format"""
        if v:
            for tag in v:
                if not tag.startswith('@'):
                    raise ValueError("User tags must start with @")
        return v


# ============================================================================
# INSTAGRAM PUBLISHING RESPONSES
# ============================================================================

class InstagramPublishResponse(BaseModel):
    """Response from Instagram publish attempt"""
    success: bool
    platform: str = "instagram"
    platform_post_id: Optional[str] = None
    platform_url: Optional[str] = None
    published_at: Optional[datetime] = None
    container_id: Optional[str] = None
    message: str

    # Error details
    error: Optional[str] = None
    error_code: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "platform": "instagram",
                "platform_post_id": "18027939294050184",
                "platform_url": "https://www.instagram.com/p/CxYz123ABC/",
                "published_at": "2025-10-22T14:30:00Z",
                "container_id": "17920384756291",
                "message": "Successfully published to Instagram"
            }
        }
    )


# ============================================================================
# INSTAGRAM OAUTH REQUESTS/RESPONSES
# ============================================================================

class InstagramOAuthAuthorizeResponse(BaseModel):
    """Response from OAuth authorize endpoint"""
    authorization_url: str
    state: str
    expires_in: int = Field(default=300, description="State token expires in seconds")


class InstagramOAuthCallbackRequest(BaseModel):
    """Request to handle OAuth callback"""
    code: str = Field(description="Authorization code from Instagram")
    state: str = Field(description="State token for CSRF protection")


class InstagramOAuthCallbackResponse(BaseModel):
    """Response after successful OAuth"""
    success: bool
    connection_id: int
    platform_username: str
    platform_user_id: str
    access_token_expires_at: datetime
    message: str = "Instagram connected successfully"


class InstagramConnectionStatus(BaseModel):
    """Instagram connection validation status"""
    valid: bool
    connected: bool
    username: Optional[str] = None
    user_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    days_until_expiry: Optional[int] = None
    needs_renewal: bool = Field(default=False)
    error: Optional[str] = None


# ============================================================================
# CONTENT GENERATION RESPONSES
# ============================================================================

class InstagramContentResponse(BaseModel):
    """Instagram-specific content (caption + image prompt)"""
    caption: str = Field(max_length=2200)
    image_prompt: str = Field(max_length=400)
    hashtags: List[str] = Field(default_factory=list)

    @field_validator('hashtags')
    @classmethod
    def validate_hashtag_count(cls, v: List[str]) -> List[str]:
        """Instagram allows max 30 hashtags"""
        if len(v) > 30:
            raise ValueError("Maximum 30 hashtags allowed")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "caption": "AI is transforming how we work! 🤖\n\nNew research shows...\n\n#AI #Technology #Innovation",
                "image_prompt": "Modern abstract visualization of AI neural networks, vibrant blue gradient, 3D geometric shapes",
                "hashtags": ["AI", "Technology", "Innovation", "MachineLearning"]
            }
        }
    )


# ============================================================================
# QUOTA AND USAGE RESPONSES
# ============================================================================

class ImageGenerationQuotaResponse(BaseModel):
    """User's image generation quota status"""
    daily_limit: int
    images_generated_today: int
    remaining_today: int
    quota_reset_date: datetime
    total_images_generated: int
    total_cost_usd: float

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "daily_limit": 50,
                "images_generated_today": 12,
                "remaining_today": 38,
                "quota_reset_date": "2025-10-23T00:00:00Z",
                "total_images_generated": 156,
                "total_cost_usd": 6.24
            }
        }
    )


# ============================================================================
# ERROR RESPONSES
# ============================================================================

class InstagramErrorResponse(BaseModel):
    """Detailed error response for Instagram operations"""
    success: bool = False
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Suggested actions user can take"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": "Instagram post requires an image",
                "error_code": "MISSING_IMAGE",
                "details": {
                    "platform": "instagram",
                    "post_id": 456
                },
                "actions": [
                    {
                        "action": "generate_image",
                        "url": "/api/posts/456/generate-instagram-image",
                        "label": "Generate Image Now"
                    }
                ]
            }
        }
    )


# ============================================================================
# ANALYTICS RESPONSES
# ============================================================================

class InstagramAnalyticsResponse(BaseModel):
    """Instagram usage analytics"""
    total_posts: int
    successful_posts: int
    failed_posts: int
    success_rate: float
    total_images_generated: int
    images_from_cache: int
    cache_hit_rate: float
    average_generation_time_seconds: float
    total_cost_usd: float

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_posts": 45,
                "successful_posts": 42,
                "failed_posts": 3,
                "success_rate": 93.3,
                "total_images_generated": 45,
                "images_from_cache": 8,
                "cache_hit_rate": 17.8,
                "average_generation_time_seconds": 14.2,
                "total_cost_usd": 1.80
            }
        }
    )
