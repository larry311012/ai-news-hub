"""
Feed Aggregator API Endpoints (Task 2.7)

API endpoints for managing the article aggregation service:
- Start/stop background aggregator
- Manual feed refresh
- View aggregator statistics
- Feed health dashboard
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from database import get_db, User
from utils.auth_selector import get_current_user as get_current_user_dependency
from services.feed_aggregator import (
    FeedAggregator,
    fetch_all_feeds_once,
    fetch_single_feed,
)

router = APIRouter()

# Global aggregator instance
_aggregator_instance: Optional[FeedAggregator] = None


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class FeedRefreshRequest(BaseModel):
    """Request to refresh a specific feed"""
    feed_id: int


class AggregatorStatsResponse(BaseModel):
    """Aggregator statistics response"""
    running: bool
    total_fetches: int
    successful_fetches: int
    failed_fetches: int
    articles_added: int
    duplicates_skipped: int
    last_run: Optional[datetime]
    success_rate: float


class FeedHealthResponse(BaseModel):
    """Feed health dashboard response"""
    total_feeds: int
    active_feeds: int
    inactive_feeds: int
    healthy_feeds: int
    warning_feeds: int
    error_feeds: int
    feeds_needing_attention: list


# ============================================================================
# AGGREGATOR MANAGEMENT ENDPOINTS
# ============================================================================


@router.post("/aggregator/start", tags=["feed-aggregator"])
async def start_aggregator(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_dependency),
):
    """
    Start the background feed aggregator service

    **Note**: This requires admin permissions in production.
    For development, any authenticated user can start it.

    The aggregator will:
    - Run continuously in the background
    - Fetch all active feeds every 15 minutes
    - Handle rate limiting and retries
    - Update feed health status
    - Deduplicate articles

    Returns:
        Success message and aggregator status
    """
    global _aggregator_instance

    # Check if already running
    if _aggregator_instance and _aggregator_instance.running:
        return {
            "message": "Aggregator is already running",
            "status": "running",
            "stats": _aggregator_instance.get_stats()
        }

    # Create and start aggregator
    _aggregator_instance = FeedAggregator()

    # Start in background
    background_tasks.add_task(_aggregator_instance.start)

    logger.info(f"Feed aggregator started by user {user.id}")

    return {
        "message": "Feed aggregator started successfully",
        "status": "running",
        "fetch_interval_seconds": 900,  # 15 minutes
    }


@router.post("/aggregator/stop", tags=["feed-aggregator"])
async def stop_aggregator(
    user: User = Depends(get_current_user_dependency),
):
    """
    Stop the background feed aggregator service

    **Note**: This requires admin permissions in production.

    Returns:
        Success message and final statistics
    """
    global _aggregator_instance

    if not _aggregator_instance or not _aggregator_instance.running:
        return {
            "message": "Aggregator is not running",
            "status": "stopped"
        }

    # Stop aggregator
    _aggregator_instance.stop()
    stats = _aggregator_instance.get_stats()

    logger.info(f"Feed aggregator stopped by user {user.id}")

    return {
        "message": "Feed aggregator stopped successfully",
        "status": "stopped",
        "final_stats": stats
    }


@router.get("/aggregator/status", tags=["feed-aggregator"])
async def get_aggregator_status(
    user: User = Depends(get_current_user_dependency),
) -> AggregatorStatsResponse:
    """
    Get current aggregator status and statistics

    Returns:
        - running: Whether aggregator is running
        - total_fetches: Total feed fetches attempted
        - successful_fetches: Successful fetches
        - failed_fetches: Failed fetches
        - articles_added: Total new articles added
        - duplicates_skipped: Duplicate articles skipped
        - last_run: Last aggregation run time
        - success_rate: Fetch success rate percentage
    """
    global _aggregator_instance

    if not _aggregator_instance:
        return AggregatorStatsResponse(
            running=False,
            total_fetches=0,
            successful_fetches=0,
            failed_fetches=0,
            articles_added=0,
            duplicates_skipped=0,
            last_run=None,
            success_rate=0.0
        )

    stats = _aggregator_instance.get_stats()

    # Calculate success rate
    total = stats["total_fetches"]
    success_rate = (
        (stats["successful_fetches"] / total * 100)
        if total > 0
        else 0.0
    )

    return AggregatorStatsResponse(
        running=stats["running"],
        total_fetches=stats["total_fetches"],
        successful_fetches=stats["successful_fetches"],
        failed_fetches=stats["failed_fetches"],
        articles_added=stats["articles_added"],
        duplicates_skipped=stats["duplicates_skipped"],
        last_run=stats["last_run"],
        success_rate=round(success_rate, 1)
    )


# ============================================================================
# MANUAL FEED OPERATIONS
# ============================================================================


@router.post("/aggregator/fetch-all", tags=["feed-aggregator"])
async def manual_fetch_all(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_dependency),
):
    """
    Manually trigger a feed fetch for all active feeds

    This is a one-time fetch, independent of the background aggregator.
    Useful for:
    - Testing feed aggregation
    - Forcing an immediate update
    - Initial feed population

    The fetch runs in the background and returns immediately.

    Returns:
        Status message
    """
    # Run fetch in background
    background_tasks.add_task(fetch_all_feeds_once)

    logger.info(f"Manual feed fetch triggered by user {user.id}")

    return {
        "message": "Feed fetch started in background",
        "status": "running",
        "note": "Check /api/aggregator/status for progress"
    }


@router.post("/aggregator/fetch-feed/{feed_id}", tags=["feed-aggregator"])
async def manual_fetch_single_feed(
    feed_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Manually refresh a specific feed

    Fetches the latest articles from the feed and stores them.
    Useful for:
    - Testing a newly added feed
    - Forcing an immediate update for a specific feed
    - Troubleshooting feed issues

    Args:
        feed_id: ID of the feed to refresh

    Returns:
        Fetch result with statistics
    """
    # Verify feed exists and belongs to user
    feed = db.execute(
        text("""
            SELECT id, feed_name
            FROM user_feeds
            WHERE id = :feed_id AND user_id = :user_id
        """),
        {"feed_id": feed_id, "user_id": user.id}
    ).fetchone()

    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found"
        )

    logger.info(f"User {user.id} triggered manual fetch for feed {feed_id}")

    # Fetch feed
    result = await fetch_single_feed(feed_id)

    return {
        "message": "Feed fetch complete",
        "feed_id": feed_id,
        "feed_name": feed.feed_name,
        "result": result
    }


# ============================================================================
# FEED HEALTH DASHBOARD
# ============================================================================


@router.get("/aggregator/health-dashboard", tags=["feed-aggregator"])
async def get_health_dashboard(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> FeedHealthResponse:
    """
    Get comprehensive feed health dashboard

    Provides an overview of all feeds' health status:
    - Total feeds (active + inactive)
    - Health breakdown (healthy/warning/error)
    - Feeds needing attention (errors or warnings)
    - Consecutive failure tracking

    Returns:
        Feed health statistics and list of problematic feeds
    """
    try:
        # Get all feeds for user
        feeds = db.execute(
            text("""
                SELECT
                    id,
                    feed_name,
                    feed_url,
                    is_active,
                    health_status,
                    error_message,
                    last_successful_fetch,
                    last_fetched_at,
                    COALESCE(consecutive_failures, 0) as consecutive_failures
                FROM user_feeds
                WHERE user_id = :user_id
                ORDER BY
                    CASE health_status
                        WHEN 'error' THEN 1
                        WHEN 'warning' THEN 2
                        WHEN 'healthy' THEN 3
                        ELSE 4
                    END,
                    consecutive_failures DESC
            """),
            {"user_id": user.id}
        ).fetchall()

        # Calculate statistics
        total_feeds = len(feeds)
        active_feeds = sum(1 for f in feeds if f.is_active)
        inactive_feeds = total_feeds - active_feeds

        health_counts = {
            "healthy": 0,
            "warning": 0,
            "error": 0,
            "unknown": 0
        }

        feeds_needing_attention = []

        for feed in feeds:
            health_status = feed.health_status or "unknown"
            health_counts[health_status] = health_counts.get(health_status, 0) + 1

            # Add to attention list if error, warning, or consecutive failures
            if health_status in ["error", "warning"] or feed.consecutive_failures > 0:
                feeds_needing_attention.append({
                    "id": feed.id,
                    "feed_name": feed.feed_name,
                    "feed_url": feed.feed_url,
                    "health_status": health_status,
                    "error_message": feed.error_message,
                    "consecutive_failures": feed.consecutive_failures,
                    "last_successful_fetch": feed.last_successful_fetch.isoformat()
                    if feed.last_successful_fetch
                    else None,
                    "last_fetched_at": feed.last_fetched_at.isoformat()
                    if feed.last_fetched_at
                    else None,
                    "is_active": feed.is_active,
                })

        return FeedHealthResponse(
            total_feeds=total_feeds,
            active_feeds=active_feeds,
            inactive_feeds=inactive_feeds,
            healthy_feeds=health_counts["healthy"],
            warning_feeds=health_counts["warning"],
            error_feeds=health_counts["error"],
            feeds_needing_attention=feeds_needing_attention
        )

    except Exception as e:
        logger.error(f"Error getting health dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve health dashboard"
        )


# ============================================================================
# FEED REACTIVATION
# ============================================================================


@router.post("/aggregator/reactivate-feed/{feed_id}", tags=["feed-aggregator"])
async def reactivate_feed(
    feed_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Reactivate an inactive feed

    Resets consecutive failures and marks feed as active.
    Useful when a feed was temporarily unavailable but is now working.

    Args:
        feed_id: ID of the feed to reactivate

    Returns:
        Success message
    """
    # Verify feed exists and belongs to user
    feed = db.execute(
        text("""
            SELECT id, feed_name, is_active
            FROM user_feeds
            WHERE id = :feed_id AND user_id = :user_id
        """),
        {"feed_id": feed_id, "user_id": user.id}
    ).fetchone()

    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found"
        )

    if feed.is_active:
        return {
            "message": "Feed is already active",
            "feed_id": feed_id,
            "feed_name": feed.feed_name
        }

    # Reactivate feed
    db.execute(
        text("""
            UPDATE user_feeds
            SET
                is_active = 1,
                consecutive_failures = 0,
                health_status = 'unknown',
                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :feed_id
        """),
        {"feed_id": feed_id}
    )

    db.commit()

    logger.info(f"User {user.id} reactivated feed {feed_id}")

    return {
        "message": "Feed reactivated successfully",
        "feed_id": feed_id,
        "feed_name": feed.feed_name,
        "note": "The feed will be fetched in the next aggregation cycle"
    }
