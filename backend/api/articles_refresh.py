"""
Enhanced Article Refresh API

Provides smart pull-to-refresh functionality with:
- New article count tracking
- Optional RSS aggregation trigger
- Status feedback (updates vs. no updates)
- User-specific last refresh tracking
- Cache invalidation
- Performance optimization

iOS Integration:
- Called from NewsFeedView.swift pull-to-refresh
- Returns count of NEW articles since last refresh
- Provides clear feedback messages
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import time
from loguru import logger

from database import get_db, Article, User
from utils.auth_selector import get_current_user as get_current_user_dependency
from config.redis_config import get_async_redis_client, RedisConfig

# Import RSS aggregator for optional fetch
from src.aggregators.rss_aggregator import RSSAggregator
from src.utils.config_loader import ConfigLoader

router = APIRouter()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class ArticleMetadata(BaseModel):
    """Lightweight article metadata"""
    id: int
    title: str
    link: str
    summary: Optional[str]
    source: str
    category: Optional[str]
    published: Optional[datetime]
    bookmarked: bool
    image_url: Optional[str] = None
    fetched_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RefreshInfo(BaseModel):
    """Refresh metadata"""
    new_articles_count: int = Field(..., description="Number of new articles since last refresh")
    total_articles: int = Field(..., description="Total articles returned")
    has_updates: bool = Field(..., description="Whether new content was found")
    last_refreshed_at: datetime = Field(..., description="When user last refreshed")
    current_refresh_at: datetime = Field(..., description="Current refresh timestamp")
    message: str = Field(..., description="Human-readable status message")
    rss_fetch_triggered: bool = Field(False, description="Whether RSS aggregation was triggered")
    rss_articles_fetched: Optional[int] = Field(None, description="Number of articles fetched from RSS")


class PaginationInfo(BaseModel):
    """Pagination metadata"""
    limit: int
    offset: int
    total: int
    has_more: bool
    page: int
    total_pages: int


class ArticleRefreshResponse(BaseModel):
    """Enhanced refresh response"""
    articles: List[ArticleMetadata]
    refresh_info: RefreshInfo
    pagination: PaginationInfo


# ============================================================================
# CACHE HELPERS
# ============================================================================


async def get_user_last_refresh(user_id: int) -> Optional[datetime]:
    """Get user's last refresh timestamp from cache"""
    try:
        redis = await get_async_redis_client()
        cache_key = f"user:{user_id}:last_refresh"
        timestamp_str = await redis.get(cache_key)

        if timestamp_str:
            return datetime.fromisoformat(timestamp_str)
        return None
    except Exception as e:
        logger.warning(f"Failed to get last refresh from cache: {e}")
        return None


async def set_user_last_refresh(user_id: int, timestamp: datetime) -> bool:
    """Set user's last refresh timestamp in cache"""
    try:
        redis = await get_async_redis_client()
        cache_key = f"user:{user_id}:last_refresh"

        # Store timestamp with 30-day TTL (auto-cleanup for inactive users)
        await redis.setex(
            cache_key,
            60 * 60 * 24 * 30,  # 30 days
            timestamp.isoformat()
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to set last refresh in cache: {e}")
        return False


async def invalidate_articles_cache(user_id: int) -> int:
    """Invalidate article cache for user after refresh"""
    try:
        redis = await get_async_redis_client()

        # Invalidate all article-related cache for this user
        patterns = [
            f"feeds:recent:{user_id}:*",
            f"feeds:articles:{user_id}:*",
            f"feeds:list:{user_id}:*",
        ]

        total_invalidated = 0
        for pattern in patterns:
            keys = await redis.keys(pattern)
            if keys:
                await redis.delete(*keys)
                total_invalidated += len(keys)

        return total_invalidated
    except Exception as e:
        logger.warning(f"Failed to invalidate cache: {e}")
        return 0


# ============================================================================
# RSS AGGREGATOR HELPER
# ============================================================================


async def trigger_rss_fetch(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Trigger RSS aggregation for user's active feeds

    Returns:
        Dictionary with fetch results
    """
    try:
        # Get user's active feeds
        feeds_result = db.execute(
            text("""
                SELECT feed_url, feed_name, feed_type
                FROM user_feeds
                WHERE user_id = :user_id AND is_active = true
            """),
            {"user_id": user_id}
        ).fetchall()

        if not feeds_result:
            logger.info(f"No active feeds for user {user_id}")
            return {
                "success": False,
                "articles_fetched": 0,
                "error": "No active feeds configured"
            }

        # Convert to aggregator format
        sources = [
            {
                "url": feed.feed_url,
                "name": feed.feed_name,
                "category": "user_feed"
            }
            for feed in feeds_result
        ]

        # Fetch from RSS
        aggregator = RSSAggregator(sources)
        articles = aggregator.fetch_all()

        # Store new articles in database
        new_count = 0
        for article_data in articles:
            try:
                # Check if already exists
                existing = db.query(Article).filter(
                    Article.link == article_data["link"],
                    Article.user_id == user_id
                ).first()

                if existing:
                    continue

                # Create new article
                article = Article(
                    title=article_data["title"],
                    link=article_data["link"],
                    summary=article_data.get("summary", ""),
                    source=article_data["source"],
                    category=article_data.get("category", "general"),
                    published=article_data.get("published", datetime.utcnow()),
                    tags=article_data.get("tags", []),
                    user_id=user_id,
                    fetched_at=datetime.utcnow()
                )
                db.add(article)
                new_count += 1

            except Exception as e:
                logger.warning(f"Error storing article: {e}")
                continue

        # Commit all new articles
        db.commit()

        logger.info(f"RSS fetch for user {user_id}: {new_count} new articles from {len(articles)} total")

        return {
            "success": True,
            "articles_fetched": new_count,
            "total_articles": len(articles)
        }

    except Exception as e:
        logger.error(f"RSS fetch failed for user {user_id}: {e}")
        return {
            "success": False,
            "articles_fetched": 0,
            "error": str(e)
        }


# ============================================================================
# ENHANCED REFRESH ENDPOINT
# ============================================================================


@router.get("/articles/refresh", response_model=ArticleRefreshResponse, tags=["articles-refresh"])
async def refresh_articles(
    limit: int = Query(20, ge=1, le=100, description="Articles per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    category: Optional[str] = Query(None, description="Filter by category"),
    source: Optional[str] = Query(None, description="Filter by source"),
    trigger_fetch: bool = Query(False, description="Trigger RSS feed fetch before returning"),
    force_refresh: bool = Query(False, description="Force refresh even if recently refreshed"),
    last_refresh_client: Optional[str] = Query(
        None,
        description="Client's last refresh timestamp (ISO format). If provided, used instead of server cache."
    ),
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> ArticleRefreshResponse:
    """
    Enhanced article refresh endpoint for iOS pull-to-refresh

    Features:
    - Tracks new articles since last refresh
    - Optional RSS feed aggregation
    - Smart caching and invalidation
    - Clear status messages
    - Performance optimized

    Flow:
    1. Get user's last refresh timestamp (from cache or client)
    2. Optionally trigger RSS feed fetch
    3. Query articles newer than last refresh
    4. Return enriched response with counts and status
    5. Update last refresh timestamp
    6. Invalidate stale cache

    Args:
        limit: Number of articles to return
        offset: Pagination offset
        category: Optional category filter
        source: Optional source filter
        trigger_fetch: Whether to fetch from RSS feeds before querying
        force_refresh: Bypass refresh throttling
        last_refresh_client: Client-provided last refresh timestamp
        user: Current authenticated user
        db: Database session

    Returns:
        ArticleRefreshResponse with articles, refresh info, and pagination

    iOS Usage:
    ```swift
    func refreshArticles() async throws {
        let url = "\(baseURL)/api/articles/refresh?limit=20&trigger_fetch=true"
        let response = try await fetch(url)

        if response.refresh_info.has_updates {
            print("Loaded \(response.refresh_info.new_articles_count) new articles!")
        } else {
            print("No new updates")
        }
    }
    ```
    """
    start_time = time.time()
    current_refresh = datetime.utcnow()

    try:
        # ====================================================================
        # STEP 1: Determine last refresh timestamp
        # ====================================================================

        # Try client timestamp first (more accurate for offline scenarios)
        last_refresh: Optional[datetime] = None

        if last_refresh_client:
            try:
                last_refresh = datetime.fromisoformat(last_refresh_client.replace('Z', '+00:00'))
                logger.debug(f"Using client-provided last refresh: {last_refresh}")
            except ValueError:
                logger.warning(f"Invalid client timestamp format: {last_refresh_client}")

        # Fallback to server cache
        if last_refresh is None:
            last_refresh = await get_user_last_refresh(user.id)

        # Default to 24 hours ago if no history
        if last_refresh is None:
            last_refresh = datetime.utcnow() - timedelta(hours=24)
            logger.info(f"First refresh for user {user.id}, using 24h default")

        # ====================================================================
        # STEP 2: Optionally trigger RSS fetch
        # ====================================================================

        rss_fetch_triggered = False
        rss_articles_fetched = None

        if trigger_fetch:
            # Throttle RSS fetching to prevent abuse (max once per minute)
            time_since_refresh = (current_refresh - last_refresh).total_seconds()

            if force_refresh or time_since_refresh > 60:
                logger.info(f"Triggering RSS fetch for user {user.id}")
                fetch_result = await trigger_rss_fetch(db, user.id)

                rss_fetch_triggered = True
                rss_articles_fetched = fetch_result.get("articles_fetched", 0)

                if not fetch_result["success"]:
                    logger.warning(f"RSS fetch failed: {fetch_result.get('error')}")
            else:
                logger.info(f"Skipping RSS fetch (refreshed {int(time_since_refresh)}s ago)")

        # ====================================================================
        # STEP 3: Query articles
        # ====================================================================

        # Build filters
        filters = ["user_id = :user_id"]
        params = {
            "user_id": user.id,
            "limit": limit,
            "offset": offset,
            "last_refresh": last_refresh
        }

        if category:
            filters.append("category = :category")
            params["category"] = category

        if source:
            filters.append("source = :source")
            params["source"] = source

        where_clause = " AND ".join(filters)

        # Count NEW articles (since last refresh)
        new_count_query = f"""
            SELECT COUNT(*) as count
            FROM articles
            WHERE {where_clause} AND fetched_at > :last_refresh
        """
        new_count_result = db.execute(text(new_count_query), params).fetchone()
        new_articles_count = new_count_result.count if new_count_result else 0

        # Get total count (for pagination)
        total_count_query = f"""
            SELECT COUNT(*) as count
            FROM articles
            WHERE {where_clause}
        """
        total_count_result = db.execute(text(total_count_query), params).fetchone()
        total_count = total_count_result.count if total_count_result else 0

        # Get articles (most recent first)
        articles_query = f"""
            SELECT
                id, title, link, summary, source, category,
                published, bookmarked, image_url, fetched_at
            FROM articles
            WHERE {where_clause}
            ORDER BY fetched_at DESC, published DESC
            LIMIT :limit OFFSET :offset
        """

        articles_raw = db.execute(text(articles_query), params).fetchall()

        # Convert to metadata
        articles = [
            ArticleMetadata(
                id=article.id,
                title=article.title,
                link=article.link,
                summary=article.summary,
                source=article.source,
                category=article.category,
                published=article.published,
                bookmarked=article.bookmarked or False,
                image_url=article.image_url,
                fetched_at=article.fetched_at
            )
            for article in articles_raw
        ]

        # ====================================================================
        # STEP 4: Build response
        # ====================================================================

        # Generate status message
        if new_articles_count > 0:
            if new_articles_count == 1:
                message = "1 new article loaded"
            else:
                message = f"{new_articles_count} new articles loaded"
        else:
            message = "No new updates"

        # Build refresh info
        refresh_info = RefreshInfo(
            new_articles_count=new_articles_count,
            total_articles=len(articles),
            has_updates=new_articles_count > 0,
            last_refreshed_at=last_refresh,
            current_refresh_at=current_refresh,
            message=message,
            rss_fetch_triggered=rss_fetch_triggered,
            rss_articles_fetched=rss_articles_fetched
        )

        # Build pagination
        pagination = PaginationInfo(
            limit=limit,
            offset=offset,
            total=total_count,
            has_more=(offset + limit) < total_count,
            page=(offset // limit) + 1 if limit > 0 else 1,
            total_pages=(total_count + limit - 1) // limit if limit > 0 else 1
        )

        response = ArticleRefreshResponse(
            articles=articles,
            refresh_info=refresh_info,
            pagination=pagination
        )

        # ====================================================================
        # STEP 5: Update cache and clean up
        # ====================================================================

        # Store current refresh timestamp
        await set_user_last_refresh(user.id, current_refresh)

        # Invalidate stale article cache
        if new_articles_count > 0:
            invalidated = await invalidate_articles_cache(user.id)
            logger.debug(f"Invalidated {invalidated} cache keys")

        # Log performance
        elapsed = (time.time() - start_time) * 1000
        logger.info(
            f"User {user.id} refresh: {new_articles_count} new / {len(articles)} returned "
            f"(RSS: {rss_fetch_triggered}, time: {elapsed:.0f}ms)"
        )

        return response

    except Exception as e:
        logger.error(f"Error refreshing articles for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh articles: {str(e)}"
        )


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================


@router.post("/articles/refresh/clear", tags=["articles-refresh"])
async def clear_refresh_state(
    user: User = Depends(get_current_user_dependency),
) -> Dict[str, Any]:
    """
    Clear user's refresh state (for testing or reset)

    This resets the last refresh timestamp, causing the next refresh
    to show all articles as "new".

    Returns:
        Success status
    """
    try:
        redis = await get_async_redis_client()
        cache_key = f"user:{user.id}:last_refresh"
        await redis.delete(cache_key)

        logger.info(f"Cleared refresh state for user {user.id}")

        return {
            "success": True,
            "message": "Refresh state cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing refresh state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear refresh state"
        )


@router.get("/articles/refresh/status", tags=["articles-refresh"])
async def get_refresh_status(
    user: User = Depends(get_current_user_dependency),
) -> Dict[str, Any]:
    """
    Get current refresh status for user

    Useful for debugging or showing user their last refresh time.

    Returns:
        Last refresh timestamp and time since refresh
    """
    try:
        last_refresh = await get_user_last_refresh(user.id)

        if last_refresh is None:
            return {
                "has_refreshed": False,
                "message": "No refresh history"
            }

        time_since = datetime.utcnow() - last_refresh

        return {
            "has_refreshed": True,
            "last_refreshed_at": last_refresh.isoformat(),
            "seconds_since_refresh": int(time_since.total_seconds()),
            "human_readable": _format_time_since(time_since)
        }
    except Exception as e:
        logger.error(f"Error getting refresh status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get refresh status"
        )


def _format_time_since(delta: timedelta) -> str:
    """Format timedelta as human-readable string"""
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return f"{seconds} seconds ago"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"
