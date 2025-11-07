"""
Enhanced RSS Feed Endpoints for iOS Mobile App (Task 2.6)

Optimized endpoints with:
- Pagination (limit, offset)
- Filtering (active status, category)
- Sorting (name, article count, updated)
- Caching (Redis)
- Performance optimizations
- Bulk operations

All endpoints are iOS-optimized with standardized error responses.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_, desc, asc
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import time
import hashlib
import json
from loguru import logger

from database import get_db, User, Article
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.feed_validator import validate_feed, parse_feed_metadata, get_feed_preview_items
from config.redis_config import get_async_redis_client, RedisConfig

router = APIRouter()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class PaginationParams(BaseModel):
    """Pagination parameters"""
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    offset: int = Field(0, ge=0, description="Number of items to skip")


class FeedSortParams(BaseModel):
    """Feed sorting parameters"""
    sort_by: str = Field("created_at", description="Sort field: name, article_count, updated_at, created_at")
    sort_order: str = Field("desc", description="Sort order: asc, desc")


class FeedFilterParams(BaseModel):
    """Feed filtering parameters"""
    active_only: Optional[bool] = Field(None, description="Filter by active status")
    health_status: Optional[str] = Field(None, description="Filter by health: healthy, warning, error, unknown")
    feed_type: Optional[str] = Field(None, description="Filter by type: rss, atom, json")


class ArticleMetadata(BaseModel):
    """Lightweight article metadata for lists"""
    id: int
    title: str
    link: str
    summary: Optional[str]
    source: str
    category: Optional[str]
    published: Optional[datetime]
    bookmarked: bool
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class FeedWithStats(BaseModel):
    """Feed response with statistics"""
    id: int
    feed_url: str
    feed_name: str
    feed_description: Optional[str]
    feed_type: str
    website_url: Optional[str]
    update_frequency: int
    last_fetched_at: Optional[datetime]
    last_successful_fetch: Optional[datetime]
    health_status: str
    error_message: Optional[str]
    total_items_fetched: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Statistics
    article_count: int = 0


class PaginatedFeedsResponse(BaseModel):
    """Paginated feeds response"""
    feeds: List[FeedWithStats]
    pagination: Dict[str, Any]
    statistics: Dict[str, Any]


class PaginatedArticlesResponse(BaseModel):
    """Paginated articles response"""
    articles: List[ArticleMetadata]
    pagination: Dict[str, Any]
    feed_info: Optional[Dict[str, Any]]


class BulkArticlesRequest(BaseModel):
    """Request for bulk articles endpoint"""
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    category: Optional[str] = Field(None, description="Filter by category")
    source: Optional[str] = Field(None, description="Filter by source")
    feed_ids: Optional[List[int]] = Field(None, description="Filter by specific feed IDs")
    search: Optional[str] = Field(None, description="Search query")
    date_from: Optional[datetime] = Field(None, description="Start date filter")
    date_to: Optional[datetime] = Field(None, description="End date filter")
    sort_by: str = Field("published", description="Sort by: published, fetched_at, title")
    sort_order: str = Field("desc", description="Sort order: asc, desc")


class FeedValidationDetailedResponse(BaseModel):
    """Detailed feed validation response"""
    is_valid: bool
    feed_metadata: Optional[Dict[str, Any]] = None
    preview_articles: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    warnings: Optional[List[str]] = None
    validation_time_ms: int


# ============================================================================
# CACHE HELPERS
# ============================================================================


async def get_cached_data(key: str) -> Optional[Any]:
    """Get data from Redis cache"""
    try:
        redis = await get_async_redis_client()
        data = await redis.get(key)
        if data:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(data)
        logger.debug(f"Cache MISS: {key}")
        return None
    except Exception as e:
        logger.warning(f"Redis get failed: {e}")
        return None


async def set_cached_data(key: str, data: Any, ttl: int = 300) -> bool:
    """Set data in Redis cache"""
    try:
        redis = await get_async_redis_client()
        await redis.setex(key, ttl, json.dumps(data, default=str))
        logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.warning(f"Redis set failed: {e}")
        return False


async def invalidate_cache(pattern: str) -> int:
    """Invalidate cache keys matching pattern"""
    try:
        redis = await get_async_redis_client()
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys: {pattern}")
            return len(keys)
        return 0
    except Exception as e:
        logger.warning(f"Cache invalidation failed: {e}")
        return 0


def generate_cache_key(*parts: Any) -> str:
    """Generate consistent cache key"""
    key_str = ":".join(str(p) for p in parts)
    return f"feeds:{key_str}"


# ============================================================================
# ENHANCED FEED ENDPOINTS
# ============================================================================


@router.get("/user-feeds/enhanced", tags=["feeds-enhanced"])
async def list_user_feeds_enhanced(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_by: str = Query("created_at", description="Sort by: name, article_count, updated_at, created_at"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    active_only: Optional[bool] = Query(None, description="Filter by active status"),
    health_status: Optional[str] = Query(None, description="Filter by health status"),
    include_article_count: bool = Query(True, description="Include article count (slower)"),
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> PaginatedFeedsResponse:
    """
    Enhanced feed listing with pagination, filtering, and sorting

    Features:
    - Pagination (limit, offset)
    - Filtering (active, health status)
    - Sorting (name, article count, updated)
    - Article count per feed (optional)
    - Response caching (5 minutes)

    Returns:
        Paginated list of feeds with statistics
    """
    try:
        # Generate cache key
        cache_key = generate_cache_key(
            "list",
            user.id,
            limit,
            offset,
            sort_by,
            sort_order,
            active_only,
            health_status,
            include_article_count
        )

        # Try cache first
        cached = await get_cached_data(cache_key)
        if cached:
            return PaginatedFeedsResponse(**cached)

        # Build query with filters
        filters = [text("user_id = :user_id")]
        params = {"user_id": user.id}

        if active_only is not None:
            filters.append(text("is_active = :is_active"))
            params["is_active"] = active_only

        if health_status:
            filters.append(text("health_status = :health_status"))
            params["health_status"] = health_status

        where_clause = " AND ".join(str(f) for f in filters)

        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM user_feeds
            WHERE {where_clause}
        """
        total_result = db.execute(text(count_query), params).fetchone()
        total_count = total_result.total if total_result else 0

        # Validate sort parameters
        valid_sort_fields = {
            "name": "feed_name",
            "created_at": "created_at",
            "updated_at": "updated_at",
            "article_count": "total_items_fetched"  # Fallback to stored count
        }

        sort_field = valid_sort_fields.get(sort_by, "created_at")
        sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"

        # Get feeds
        feeds_query = f"""
            SELECT *
            FROM user_feeds
            WHERE {where_clause}
            ORDER BY {sort_field} {sort_direction}
            LIMIT :limit OFFSET :offset
        """

        params["limit"] = limit
        params["offset"] = offset

        feeds = db.execute(text(feeds_query), params).fetchall()

        # Convert to list with article counts
        feeds_list = []
        for feed in feeds:
            feed_dict = {
                "id": feed.id,
                "feed_url": feed.feed_url,
                "feed_name": feed.feed_name,
                "feed_description": feed.feed_description,
                "feed_type": feed.feed_type,
                "website_url": feed.website_url,
                "update_frequency": feed.update_frequency,
                "last_fetched_at": feed.last_fetched_at,
                "last_successful_fetch": feed.last_successful_fetch,
                "health_status": feed.health_status,
                "error_message": feed.error_message,
                "total_items_fetched": feed.total_items_fetched,
                "is_active": feed.is_active,
                "created_at": feed.created_at,
                "updated_at": feed.updated_at,
                "article_count": 0
            }

            # Get live article count if requested
            if include_article_count:
                count_result = db.execute(
                    text("""
                        SELECT COUNT(*) as count
                        FROM articles
                        WHERE source = :source AND user_id = :user_id
                    """),
                    {"source": feed.feed_name, "user_id": user.id}
                ).fetchone()

                if count_result:
                    feed_dict["article_count"] = count_result.count

            feeds_list.append(FeedWithStats(**feed_dict))

        # Calculate statistics
        stats_query = f"""
            SELECT
                health_status,
                COUNT(*) as count
            FROM user_feeds
            WHERE {where_clause}
            GROUP BY health_status
        """
        stats_result = db.execute(text(stats_query), params).fetchall()

        health_breakdown = {row.health_status: row.count for row in stats_result}

        response = PaginatedFeedsResponse(
            feeds=feeds_list,
            pagination={
                "limit": limit,
                "offset": offset,
                "total": total_count,
                "has_more": (offset + limit) < total_count,
                "page": (offset // limit) + 1 if limit > 0 else 1,
                "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1
            },
            statistics={
                "total_feeds": total_count,
                "health_breakdown": health_breakdown,
                "active_feeds": sum(1 for f in feeds_list if f.is_active),
                "healthy_feeds": health_breakdown.get("healthy", 0)
            }
        )

        # Cache response for 5 minutes
        await set_cached_data(cache_key, response.model_dump(mode='json'), ttl=RedisConfig.CACHE_TTL_MEDIUM)

        logger.info(
            f"User {user.id} listed feeds: {len(feeds_list)} feeds "
            f"(page {response.pagination['page']}/{response.pagination['total_pages']})"
        )

        return response

    except Exception as e:
        logger.error(f"Error listing feeds for user {user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feeds"
        )


@router.get("/user-feeds/{feed_id}/articles", tags=["feeds-enhanced"])
async def get_feed_articles(
    feed_id: int,
    limit: int = Query(20, ge=1, le=100, description="Articles per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> PaginatedArticlesResponse:
    """
    Get articles from a specific feed with pagination

    Features:
    - Pagination (20 per page)
    - Date range filtering
    - Sorted by published date (newest first)
    - Returns metadata only (not full content)
    - Includes X-Total-Count header

    Returns:
        Paginated list of article metadata
    """
    try:
        # Verify feed exists and belongs to user
        feed = db.execute(
            text("""
                SELECT * FROM user_feeds
                WHERE id = :feed_id AND user_id = :user_id
            """),
            {"feed_id": feed_id, "user_id": user.id}
        ).fetchone()

        if not feed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feed not found"
            )

        # Generate cache key
        cache_key = generate_cache_key(
            "articles",
            feed_id,
            user.id,
            limit,
            offset,
            date_from or "",
            date_to or ""
        )

        # Try cache
        cached = await get_cached_data(cache_key)
        if cached:
            return PaginatedArticlesResponse(**cached)

        # Build query with filters
        filters = ["source = :source", "user_id = :user_id"]
        params = {
            "source": feed.feed_name,
            "user_id": user.id,
            "limit": limit,
            "offset": offset
        }

        # Date filters
        if date_from:
            filters.append("published >= :date_from")
            params["date_from"] = date_from

        if date_to:
            filters.append("published <= :date_to")
            params["date_to"] = date_to

        where_clause = " AND ".join(filters)

        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM articles
            WHERE {where_clause}
        """
        total_result = db.execute(text(count_query), params).fetchone()
        total_count = total_result.total if total_result else 0

        # Get articles (metadata only)
        articles_query = f"""
            SELECT
                id, title, link, summary, source, category,
                published, bookmarked, fetched_at
            FROM articles
            WHERE {where_clause}
            ORDER BY published DESC
            LIMIT :limit OFFSET :offset
        """

        articles_raw = db.execute(text(articles_query), params).fetchall()

        # Convert to metadata objects
        articles = []
        for article in articles_raw:
            articles.append(ArticleMetadata(
                id=article.id,
                title=article.title,
                link=article.link,
                summary=article.summary,
                source=article.source,
                category=article.category,
                published=article.published,
                bookmarked=article.bookmarked or False
            ))

        response = PaginatedArticlesResponse(
            articles=articles,
            pagination={
                "limit": limit,
                "offset": offset,
                "total": total_count,
                "has_more": (offset + limit) < total_count,
                "page": (offset // limit) + 1 if limit > 0 else 1,
                "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1
            },
            feed_info={
                "id": feed.id,
                "name": feed.feed_name,
                "url": feed.feed_url,
                "health_status": feed.health_status
            }
        )

        # Cache for 2 minutes (articles change frequently)
        await set_cached_data(cache_key, response.model_dump(mode='json'), ttl=120)

        logger.info(
            f"User {user.id} retrieved {len(articles)} articles from feed {feed_id} "
            f"(page {response.pagination['page']})"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting articles for feed {feed_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve articles"
        )


# ============================================================================
# BULK ARTICLES ENDPOINT
# ============================================================================


@router.get("/articles/recent", tags=["feeds-enhanced"])
async def get_recent_articles_bulk(
    limit: int = Query(20, ge=1, le=100, description="Articles per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    category: Optional[str] = Query(None, description="Filter by category"),
    source: Optional[str] = Query(None, description="Filter by source (feed name)"),
    feed_ids: Optional[str] = Query(None, description="Comma-separated feed IDs"),
    search: Optional[str] = Query(None, description="Search in title/summary"),
    date_from: Optional[str] = Query(None, description="Start date (ISO format)"),
    date_to: Optional[str] = Query(None, description="End date (ISO format)"),
    sort_by: str = Query("published", description="Sort by: published, fetched_at, title"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> PaginatedArticlesResponse:
    """
    Get recent articles from all active feeds with advanced filtering

    Features:
    - Pagination with configurable page size
    - Multi-filter support (category, source, date range, search)
    - Full-text search in title and summary
    - Optimized with database indexes
    - Response caching (1 minute for frequently accessed pages)
    - Supports filtering by specific feed IDs

    Performance:
    - Uses indexed columns for fast filtering
    - Cached responses for common queries
    - Returns metadata only (not full content)

    Returns:
        Paginated list of recent articles across all feeds
    """
    try:
        # Generate cache key
        cache_key = generate_cache_key(
            "recent",
            user.id,
            limit,
            offset,
            category or "",
            source or "",
            feed_ids or "",
            search or "",
            date_from or "",
            date_to or "",
            sort_by,
            sort_order
        )

        # Try cache
        cached = await get_cached_data(cache_key)
        if cached:
            return PaginatedArticlesResponse(**cached)

        # Build filters
        filters = ["user_id = :user_id"]
        params = {
            "user_id": user.id,
            "limit": limit,
            "offset": offset
        }

        # Category filter
        if category:
            filters.append("category = :category")
            params["category"] = category

        # Source filter
        if source:
            filters.append("source = :source")
            params["source"] = source

        # Feed IDs filter
        if feed_ids:
            feed_id_list = [int(fid.strip()) for fid in feed_ids.split(",") if fid.strip().isdigit()]
            if feed_id_list:
                # Get feed names for these IDs
                feeds_result = db.execute(
                    text("""
                        SELECT feed_name FROM user_feeds
                        WHERE id IN :feed_ids AND user_id = :user_id
                    """),
                    {"feed_ids": tuple(feed_id_list), "user_id": user.id}
                ).fetchall()

                if feeds_result:
                    feed_names = [row.feed_name for row in feeds_result]
                    placeholders = ",".join([f":feed_{i}" for i in range(len(feed_names))])
                    filters.append(f"source IN ({placeholders})")
                    for i, name in enumerate(feed_names):
                        params[f"feed_{i}"] = name

        # Search filter
        if search:
            filters.append("(title LIKE :search OR summary LIKE :search)")
            params["search"] = f"%{search}%"

        # Date filters
        if date_from:
            filters.append("published >= :date_from")
            params["date_from"] = date_from

        if date_to:
            filters.append("published <= :date_to")
            params["date_to"] = date_to

        where_clause = " AND ".join(filters)

        # Validate sort parameters
        valid_sort_fields = {
            "published": "published",
            "fetched_at": "fetched_at",
            "title": "title"
        }
        sort_field = valid_sort_fields.get(sort_by, "published")
        sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"

        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM articles
            WHERE {where_clause}
        """
        total_result = db.execute(text(count_query), params).fetchone()
        total_count = total_result.total if total_result else 0

        # Get articles
        articles_query = f"""
            SELECT
                id, title, link, summary, source, category,
                published, bookmarked, fetched_at, image_url
            FROM articles
            WHERE {where_clause}
            ORDER BY {sort_field} {sort_direction}
            LIMIT :limit OFFSET :offset
        """

        articles_raw = db.execute(text(articles_query), params).fetchall()

        # Convert to metadata
        articles = []
        for article in articles_raw:
            articles.append(ArticleMetadata(
                id=article.id,
                title=article.title,
                link=article.link,
                summary=article.summary,
                source=article.source,
                category=article.category,
                published=article.published,
                bookmarked=article.bookmarked or False,
                image_url=article.image_url
            ))

        response = PaginatedArticlesResponse(
            articles=articles,
            pagination={
                "limit": limit,
                "offset": offset,
                "total": total_count,
                "has_more": (offset + limit) < total_count,
                "page": (offset // limit) + 1 if limit > 0 else 1,
                "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1
            },
            feed_info=None
        )

        # Cache for 1 minute (balance between freshness and performance)
        await set_cached_data(cache_key, response.model_dump(mode='json'), ttl=60)

        logger.info(
            f"User {user.id} retrieved {len(articles)} recent articles "
            f"(filters: category={category}, search={bool(search)}, page={response.pagination['page']})"
        )

        return response

    except Exception as e:
        logger.error(f"Error getting recent articles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recent articles"
        )


# ============================================================================
# ENHANCED FEED VALIDATION
# ============================================================================


@router.post("/feeds/validate-detailed", tags=["feeds-enhanced"])
async def validate_feed_detailed(
    feed_url: str = Query(..., description="Feed URL to validate"),
    include_preview: bool = Query(True, description="Include article previews"),
    user: User = Depends(get_current_user_dependency),
) -> FeedValidationDetailedResponse:
    """
    Enhanced feed validation with detailed metadata and previews

    Features:
    - Validates RSS 2.0, Atom, and JSON Feed formats
    - Returns feed metadata (title, description, type)
    - Returns 3 preview articles
    - Identifies potential issues (warnings)
    - Performance timing

    Validation checks:
    1. URL accessibility (HTTP 200)
    2. Content-Type validation
    3. XML/JSON well-formedness
    4. Valid feed structure
    5. Contains at least 1 item
    6. All required fields present

    Returns:
        Detailed validation results with metadata and previews
    """
    start_time = time.time()

    try:
        # Validate feed
        validation_result = await validate_feed(feed_url)

        if not validation_result["is_valid"]:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return FeedValidationDetailedResponse(
                is_valid=False,
                error_message=validation_result.get("error_message", "Feed validation failed"),
                validation_time_ms=elapsed_ms
            )

        # Parse metadata
        metadata = None
        preview_articles = None
        warnings = []

        try:
            metadata_raw = await parse_feed_metadata(feed_url)

            metadata = {
                "title": metadata_raw.get("title", "Untitled Feed"),
                "description": metadata_raw.get("description", ""),
                "type": metadata_raw.get("feed_type", "rss"),
                "item_count": metadata_raw.get("item_count", 0),
                "last_updated": metadata_raw.get("last_updated"),
                "website_url": metadata_raw.get("website_url", ""),
                "language": metadata_raw.get("language", "en")
            }

            # Check for potential issues
            if metadata["item_count"] == 0:
                warnings.append("Feed is empty (no articles found)")
            elif metadata["item_count"] < 5:
                warnings.append(f"Feed has only {metadata['item_count']} articles")

            if not metadata["description"]:
                warnings.append("Feed has no description")

        except Exception as e:
            logger.warning(f"Error parsing feed metadata: {e}")
            warnings.append("Could not parse some feed metadata")
            metadata = {
                "title": "Unknown Feed",
                "description": "",
                "type": validation_result.get("feed_type", "rss"),
                "item_count": 0
            }

        # Get preview articles
        if include_preview:
            try:
                preview_data = await get_feed_preview_items(feed_url, limit=3)
                preview_articles = preview_data.get("items", [])

                if not preview_articles:
                    warnings.append("Could not retrieve preview articles")

            except Exception as e:
                logger.warning(f"Error getting feed preview: {e}")
                warnings.append("Preview articles unavailable")
                preview_articles = []

        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"User {user.id} validated feed: {feed_url} "
            f"(valid={True}, type={metadata.get('type')}, time={elapsed_ms}ms)"
        )

        return FeedValidationDetailedResponse(
            is_valid=True,
            feed_metadata=metadata,
            preview_articles=preview_articles if include_preview else None,
            warnings=warnings if warnings else None,
            validation_time_ms=elapsed_ms
        )

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Error validating feed: {str(e)}")

        return FeedValidationDetailedResponse(
            is_valid=False,
            error_message=f"Validation error: {str(e)}",
            validation_time_ms=elapsed_ms
        )


# ============================================================================
# SYSTEM SOURCES WITH CACHING
# ============================================================================


@router.get("/system-sources/cached", tags=["feeds-enhanced"])
async def get_system_sources_cached(
    user: User = Depends(get_current_user_dependency),
):
    """
    Get system-wide RSS sources with 1-hour caching

    Features:
    - Redis caching (1 hour TTL)
    - Feed statistics
    - Only returns active feeds
    - Category grouping

    Returns:
        List of system RSS feed sources with metadata
    """
    try:
        # Try cache first
        cache_key = generate_cache_key("system-sources", "all")
        cached = await get_cached_data(cache_key)

        if cached:
            logger.debug("Returning cached system sources")
            return cached

        # Load from YAML file
        from pathlib import Path
        import yaml

        config_path = Path("/Users/ranhui/ai_post/config/sources.yaml")

        if not config_path.exists():
            config_path = Path("../../config/sources.yaml")

        if not config_path.exists():
            logger.warning("sources.yaml not found")
            return {
                "sources": [],
                "total_sources": 0,
                "categories": [],
                "cached": False
            }

        # Load sources
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        rss_feeds = config.get("sources", {}).get("rss_feeds", [])

        # Transform sources
        sources = []
        for idx, feed in enumerate(rss_feeds):
            sources.append({
                "id": f"system-{idx}",
                "feed_name": feed.get("name", "Unnamed Source"),
                "feed_url": feed.get("url", ""),
                "feed_description": f"Category: {feed.get('category', 'general')}",
                "category": feed.get("category", "general"),
                "feed_type": "rss",
                "health_status": "unknown",
                "is_active": True,
                "is_system": True,
                "update_frequency": 3600,
                "total_items_fetched": 0,
            })

        # Get unique categories
        categories = list(set(s["category"] for s in sources))

        # Calculate statistics
        category_counts = {}
        for cat in categories:
            category_counts[cat] = sum(1 for s in sources if s["category"] == cat)

        response = {
            "sources": sources,
            "total_sources": len(sources),
            "categories": categories,
            "category_counts": category_counts,
            "cached": False,
            "cache_ttl_seconds": RedisConfig.CACHE_TTL_LONG
        }

        # Cache for 1 hour
        await set_cached_data(cache_key, response, ttl=RedisConfig.CACHE_TTL_LONG)

        logger.info(f"Loaded {len(sources)} system sources (cached for 1 hour)")

        return response

    except Exception as e:
        logger.error(f"Error loading system sources: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load system sources"
        )


# ============================================================================
# CACHE MANAGEMENT ENDPOINTS
# ============================================================================


@router.post("/feeds/cache/invalidate", tags=["feeds-enhanced"])
async def invalidate_feeds_cache(
    user: User = Depends(get_current_user_dependency),
):
    """
    Invalidate all feeds cache for current user

    Useful after:
    - Adding/removing feeds
    - Updating feed settings
    - Fetching new articles

    Returns:
        Number of cache keys invalidated
    """
    try:
        # Invalidate user-specific cache
        count = await invalidate_cache(f"feeds:*:{user.id}:*")

        logger.info(f"User {user.id} invalidated {count} feed cache keys")

        return {
            "success": True,
            "keys_invalidated": count,
            "message": "Feed cache cleared successfully"
        }

    except Exception as e:
        logger.error(f"Error invalidating cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invalidate cache"
        )
