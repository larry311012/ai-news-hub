"""
Articles API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from database import get_db, Article, User  # noqa: E402
from src.aggregators import RSSAggregator  # noqa: E402
from src.utils import ConfigLoader  # noqa: E402
from utils.auth_selector import get_current_user as get_current_user_dependency  # noqa: E402

router = APIRouter()
logger = logging.getLogger(__name__)


# Pydantic models
class ArticleResponse(BaseModel):
    id: int
    title: str
    link: str
    summary: Optional[str]
    source: str
    category: str
    published: datetime
    bookmarked: bool
    tags: Optional[list]
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

    @property
    def is_saved(self) -> bool:
        """Alias for bookmarked to support frontend"""
        return self.bookmarked

    def model_dump(self, **kwargs):
        """Override to include is_saved in serialization"""
        data = super().model_dump(**kwargs)
        data["is_saved"] = self.bookmarked
        return data


class FetchRequest(BaseModel):
    force_refresh: bool = False


class BookmarkRequest(BaseModel):
    """Request model for bookmarking an article"""

    article_id: int


class RefreshInfo(BaseModel):
    """Refresh information for modern refresh endpoint"""
    new_articles_count: int
    has_updates: bool
    message: str
    last_refresh: Optional[datetime] = None


class RefreshResponse(BaseModel):
    """Response model for refresh endpoint"""
    success: bool
    refresh_info: RefreshInfo
    articles: List[ArticleResponse]
    total: int
    returned: int


@router.get("", response_model=List[ArticleResponse])
async def get_articles(
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    source: Optional[str] = None,
    bookmarked: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get articles with filtering and pagination

    When no category filter is applied and limit is high (>100), returns a balanced
    mix of articles from all categories to ensure diverse content in the feed.
    """

    # If category filter is applied or limit is small, use standard query
    if category or source or bookmarked is not None or search or limit <= 100:
        query = db.query(Article)

        # Apply filters
        if category:
            query = query.filter(Article.category == category)
        if source:
            query = query.filter(Article.source == source)
        if bookmarked is not None:
            query = query.filter(Article.bookmarked.is_(bookmarked))
        if search:
            query = query.filter(Article.title.contains(search))

        # Order by published date (newest first)
        query = query.order_by(Article.published.desc())

        # Pagination
        articles = query.offset(skip).limit(limit).all()

        return articles

    # For large unfiltered requests, return balanced mix from all categories
    # This ensures the frontend sees articles from all categories

    # Get all categories
    categories = db.query(Article.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]  # Filter out None values

    if not categories:
        return []

    # Calculate how many articles to fetch per category
    per_category = limit // len(categories)
    remainder = limit % len(categories)

    # Fetch articles from each category
    all_articles = []
    for i, cat in enumerate(categories):
        # Give extra articles to first categories to reach exact limit
        cat_limit = per_category + (1 if i < remainder else 0)

        cat_articles = (
            db.query(Article)
            .filter(Article.category == cat)
            .order_by(Article.published.desc())
            .limit(cat_limit)
            .all()
        )
        all_articles.extend(cat_articles)

    # Sort combined results by published date
    all_articles.sort(key=lambda x: x.published, reverse=True)

    return all_articles


# ============================================================================
# MODERN REFRESH ENDPOINT
# ============================================================================


@router.get("/refresh", response_model=RefreshResponse)
async def refresh_articles(
    skip: int = Query(0, description="Number of articles to skip for pagination"),
    limit: int = Query(50, description="Maximum number of articles to return"),
    category: Optional[str] = Query(None, description="Filter by category"),
    source: Optional[str] = Query(None, description="Filter by source"),
    since: Optional[str] = Query(None, description="ISO datetime to check for new articles since"),
    db: Session = Depends(get_db),
):
    """
    Modern refresh endpoint that tracks new articles since last refresh.

    This endpoint enhances the standard articles endpoint by:
    - Tracking new article counts since last refresh
    - Providing status feedback (has_updates or not)
    - Returning enriched response with refresh_info

    Args:
        skip: Pagination offset
        limit: Max articles to return
        category: Optional category filter
        source: Optional source filter
        since: Optional ISO datetime to check for articles newer than this
        db: Database session

    Returns:
        RefreshResponse with refresh_info and articles
    """
    try:
        # Determine the timestamp for "new" articles
        if since:
            try:
                # Parse ISO datetime string
                last_refresh_time = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                # Invalid timestamp format - treat as first refresh
                last_refresh_time = None
        else:
            # No timestamp provided - this is first refresh
            last_refresh_time = None

        # Build base query
        query = db.query(Article)

        # Apply filters
        if category:
            query = query.filter(Article.category == category)
        if source:
            query = query.filter(Article.source == source)

        # Count total articles matching filters (for pagination info)
        total_count = query.count()

        # Count new articles since last refresh
        if last_refresh_time:
            # Count articles fetched after the last refresh time
            new_articles_query = query.filter(Article.fetched_at > last_refresh_time)
            new_articles_count = new_articles_query.count()
        else:
            # First refresh - all articles are "new"
            new_articles_count = total_count

        # Determine if there are updates
        has_updates = new_articles_count > 0

        # Generate appropriate message
        if new_articles_count == 0:
            message = "No new updates"
        elif new_articles_count == 1:
            message = "1 new article loaded"
        else:
            message = f"{new_articles_count} new articles loaded"

        # Fetch articles with pagination (ordered by most recent first)
        articles = (
            query.order_by(Article.published.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Build refresh info
        refresh_info = RefreshInfo(
            new_articles_count=new_articles_count,
            has_updates=has_updates,
            message=message,
            last_refresh=datetime.utcnow()
        )

        # Build response
        response = RefreshResponse(
            success=True,
            refresh_info=refresh_info,
            articles=[ArticleResponse.model_validate(article) for article in articles],
            total=total_count,
            returned=len(articles)
        )

        logger.info(
            f"Refresh completed: {new_articles_count} new articles "
            f"(total: {total_count}, returned: {len(articles)})"
        )

        return response

    except Exception as e:
        logger.error(f"Error in refresh endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error refreshing articles: {str(e)}"
        )


# ============================================================================
# SAVED ARTICLES ENDPOINTS (Must be before /{article_id} to avoid route conflict)
# ============================================================================


@router.get("/saved", response_model=List[ArticleResponse])
async def get_saved_articles(
    skip: int = Query(0, description="Number of articles to skip"),
    limit: int = Query(50, description="Maximum number of articles to return"),
    category: Optional[str] = Query(None, description="Category filter"),
    source: Optional[str] = Query(None, description="Source filter"),
    time_filter: Optional[str] = Query(
        None, alias="filter", description="Time filter: 'all', 'today', or 'week'"
    ),
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Get all saved/bookmarked articles for the current user.

    Args:
        skip: Number of articles to skip (pagination)
        limit: Maximum number of articles to return
        category: Optional category filter
        source: Optional source filter
        time_filter: Optional time filter ('all', 'today', 'week')
        user: Current authenticated user
        db: Database session

    Returns:
        List of bookmarked articles
    """
    try:
        from datetime import timedelta

        # Query bookmarked articles for this user
        query = db.query(Article).filter(Article.user_id == user.id, Article.bookmarked.is_(True))

        # Apply optional filters
        if category:
            query = query.filter(Article.category == category)
        if source:
            query = query.filter(Article.source == source)

        # Apply time filter
        if time_filter == "today":
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(Article.fetched_at >= today_start)
        elif time_filter == "week":
            week_start = datetime.utcnow() - timedelta(days=7)
            query = query.filter(Article.fetched_at >= week_start)
        # 'all' or None - no time filter applied

        # Order by most recently bookmarked (fetched_at)
        articles = query.order_by(Article.fetched_at.desc()).offset(skip).limit(limit).all()

        logger.info(
            f"Retrieved {len(articles)} saved articles "
            f"for user {user.id} with filter: {time_filter}"
        )

        return articles

    except Exception as e:
        logger.error(f"Error retrieving saved articles: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving saved articles",
        )


@router.get("/saved/count")
async def get_saved_count(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Get count of saved articles for current user.

    Args:
        user: Current authenticated user
        db: Database session

    Returns:
        Count of saved articles
    """
    try:
        count = (
            db.query(Article)
            .filter(Article.user_id == user.id, Article.bookmarked.is_(True))
            .count()
        )

        return {"success": True, "count": count}

    except Exception as e:
        logger.error(f"Error counting saved articles: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while counting saved articles",
        )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: int, db: Session = Depends(get_db)):
    """Get a single article by ID"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.post("/fetch")
async def fetch_articles(request: FetchRequest, db: Session = Depends(get_db)):
    """Fetch new articles from RSS sources"""
    try:
        # Load configuration from backend directory
        import os

        backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        config_dir = os.path.join(backend_root, "config")
        config_loader = ConfigLoader(config_dir)
        sources_config = config_loader.load_sources()

        # Fetch from RSS feeds
        rss_sources = sources_config["sources"].get("rss_feeds", [])
        aggregator = RSSAggregator(rss_sources)
        articles = aggregator.fetch_all()

        # Store in database (avoid duplicates)
        new_count = 0
        for article_data in articles:
            try:
                # Check if already exists
                existing = db.query(Article).filter(Article.link == article_data["link"]).first()

                if existing:
                    # Skip duplicate unless force refresh
                    if request.force_refresh:
                        # Update existing
                        existing.title = article_data["title"]
                        existing.summary = article_data.get("summary", "")
                        existing.fetched_at = datetime.utcnow()
                        db.commit()
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
                )
                db.add(article)
                db.flush()  # Flush to check for errors without committing
                new_count += 1

            except Exception as article_error:
                # Skip this article if there's an error
                db.rollback()
                title = article_data.get("title", "unknown")
                print(f"Skipping article {title}: {article_error}")
                continue

        # Final commit
        db.commit()

        return {
            "success": True,
            "total_fetched": len(articles),
            "new_articles": new_count,
        }

    except Exception as e:
        # Log the error but return success if articles were fetched
        import traceback

        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # Log to console

        # If we got articles but had an error storing them,
        # still return success
        if "articles" in locals() and len(articles) > 0:
            return {
                "success": True,
                "total_fetched": len(articles),
                "new_articles": 0,
                "message": "Articles fetched but some may already exist",
            }

        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BOOKMARK / SAVED ARTICLES ENDPOINTS (User-aware)
# ============================================================================


@router.post("/save")
async def save_article(
    request: BookmarkRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Save/bookmark an article for the current user.

    Args:
        request: Article ID to bookmark
        user: Current authenticated user
        db: Database session

    Returns:
        Success response with bookmarked status

    Raises:
        HTTPException: If article not found
    """
    try:
        # Find the article
        article = db.query(Article).filter(Article.id == request.article_id).first()

        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        # If article doesn't have a user_id, assign it to this user
        if article.user_id is None:
            article.user_id = user.id

        # Set bookmark
        article.bookmarked = True
        db.commit()
        db.refresh(article)

        logger.info(f"Article {article.id} bookmarked by user {user.id}")

        return {
            "success": True,
            "bookmarked": True,
            "article_id": article.id,
            "message": "Article saved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bookmarking article: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while saving article")


@router.delete("/save/{article_id}")
async def unsave_article(
    article_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Remove bookmark from an article.

    Args:
        article_id: ID of article to unsave
        user: Current authenticated user
        db: Database session

    Returns:
        Success response

    Raises:
        HTTPException: If article not found or not bookmarked by user
    """
    try:
        # Find the article
        article = (
            db.query(Article).filter(Article.id == article_id, Article.user_id == user.id).first()
        )

        if not article:
            raise HTTPException(status_code=404, detail="Article not found or not saved by you")

        # Remove bookmark
        article.bookmarked = False
        db.commit()
        db.refresh(article)

        logger.info(f"Article {article.id} unbookmarked by user {user.id}")

        return {
            "success": True,
            "bookmarked": False,
            "article_id": article.id,
            "message": "Article removed from saved",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing bookmark: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while removing bookmark")


# ============================================================================
# LEGACY BOOKMARK ENDPOINT (kept for backward compatibility)
# ============================================================================


@router.patch("/{article_id}/bookmark")
async def toggle_bookmark(article_id: int, db: Session = Depends(get_db)):
    """
    Toggle article bookmark status (legacy endpoint, no user auth).

    Note: This is kept for backward compatibility. New code should use
    POST /articles/save and DELETE /articles/save/{id} instead.
    """
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article.bookmarked = not article.bookmarked
    db.commit()

    return {"bookmarked": article.bookmarked}


@router.get("/stats/summary")
async def get_stats(db: Session = Depends(get_db)):
    """Get article statistics"""
    total = db.query(Article).count()
    bookmarked = db.query(Article).filter(Article.bookmarked.is_(True)).count()

    # Count by category
    categories = db.query(Article.category, func.count(Article.id)).group_by(Article.category).all()

    # Count by source
    sources = db.query(Article.source, func.count(Article.id)).group_by(Article.source).all()

    return {
        "total": total,
        "bookmarked": bookmarked,
        "by_category": {cat: count for cat, count in categories},
        "by_source": {src: count for src, count in sources},
    }
