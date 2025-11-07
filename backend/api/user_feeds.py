"""
User Feeds API Endpoints

API endpoints for RSS feed management:
- List feeds
- Discover feeds from website URL
- Validate feed URL
- Add/Update/Delete feeds
- Test feed connection
- Health dashboard
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime
import time
import yaml
from pathlib import Path
from loguru import logger

from database import get_db, User
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.feed_discovery import discover_feeds_from_url
from utils.feed_validator import validate_feed, parse_feed_metadata, get_feed_preview_items

router = APIRouter()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class FeedDiscoveryRequest(BaseModel):
    """Request model for feed discovery"""

    website_url: str = Field(..., description="Website URL to discover feeds from")


class FeedValidationRequest(BaseModel):
    """Request model for feed validation"""

    feed_url: str = Field(..., description="Feed URL to validate")


class FeedCreateRequest(BaseModel):
    """Request model for creating a new feed"""

    feed_url: str = Field(..., description="Feed URL")
    feed_name: str = Field(..., min_length=1, max_length=255, description="Feed name")
    feed_description: Optional[str] = Field(None, description="Feed description")
    update_frequency: int = Field(
        3600, ge=300, le=86400, description="Update frequency in seconds (5 min to 24 hours)"
    )


class FeedUpdateRequest(BaseModel):
    """Request model for updating a feed"""

    feed_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Feed name")
    feed_description: Optional[str] = Field(None, description="Feed description")
    update_frequency: Optional[int] = Field(
        None, ge=300, le=86400, description="Update frequency in seconds"
    )
    is_active: Optional[bool] = Field(None, description="Active status")


class FeedResponse(BaseModel):
    """Response model for a single feed"""

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

    class Config:
        from_attributes = True


class DiscoveredFeed(BaseModel):
    """Model for discovered feed"""

    url: str
    title: str
    type: str
    description: str
    item_count: Optional[int] = None


class PreviewItem(BaseModel):
    """Model for feed preview item"""

    title: str
    published_date: Optional[str]
    link: str


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/user-feeds", tags=["feeds"])
async def list_user_feeds(
    user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    List all feeds for current user with statistics

    Returns:
        - feeds: List of user feeds
        - total_feeds: Total number of feeds
        - healthy_feeds: Count of healthy feeds
        - warning_feeds: Count of feeds with warnings
        - error_feeds: Count of feeds with errors
    """
    try:
        # Get all feeds for user
        feeds = db.execute(
            text(
                """
            SELECT *
            FROM user_feeds
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """
            ),
            {"user_id": user.id},
        ).fetchall()

        # Convert to dict
        feeds_list = []
        for feed in feeds:
            # Note: SQLite returns datetime columns as strings when using raw SQL
            # So we don't need to call .isoformat() - they're already strings
            feeds_list.append(
                {
                    "id": feed.id,
                    "feed_url": feed.feed_url,
                    "feed_name": feed.feed_name,
                    "feed_description": feed.feed_description,
                    "feed_type": feed.feed_type,
                    "website_url": feed.website_url,
                    "update_frequency": feed.update_frequency,
                    "last_fetched_at": feed.last_fetched_at,  # Already a string from SQLite
                    "last_successful_fetch": feed.last_successful_fetch,  # Already a string
                    "health_status": feed.health_status,
                    "error_message": feed.error_message,
                    "total_items_fetched": feed.total_items_fetched,
                    "is_active": feed.is_active,
                    "created_at": feed.created_at,  # Already a string
                    "updated_at": feed.updated_at,  # Already a string
                }
            )

        # Calculate statistics
        total_feeds = len(feeds_list)
        active_feeds = sum(1 for f in feeds_list if f["is_active"])  # Count active feeds
        healthy_feeds = sum(1 for f in feeds_list if f["health_status"] == "healthy")
        warning_feeds = sum(1 for f in feeds_list if f["health_status"] == "warning")
        error_feeds = sum(1 for f in feeds_list if f["health_status"] == "error")

        return {
            "feeds": feeds_list,
            "total_feeds": total_feeds,
            "active_feeds": active_feeds,  # Add active count
            "healthy_feeds": healthy_feeds,
            "warning_feeds": warning_feeds,
            "error_feeds": error_feeds,
        }

    except Exception as e:
        logger.error(f"Error listing feeds for user {user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feeds. Please try again later.",
        )


@router.post("/user-feeds/discover", tags=["feeds"])
async def discover_feeds(
    request: FeedDiscoveryRequest, user: User = Depends(get_current_user_dependency)
):
    """
    Auto-discover feeds from website URL

    Args:
        request: Website URL to discover feeds from

    Returns:
        - discovered_feeds: List of discovered feeds with metadata
        - discovery_time_ms: Time taken for discovery
    """
    start_time = time.time()

    try:
        # Discover feeds
        feeds = await discover_feeds_from_url(request.website_url)

        # Enrich with metadata (item count)
        enriched_feeds = []
        for feed in feeds:
            try:
                metadata = await parse_feed_metadata(feed["url"])
                feed["item_count"] = metadata.get("item_count", 0)
            except Exception:
                feed["item_count"] = 0

            enriched_feeds.append(feed)

        discovery_time = int((time.time() - start_time) * 1000)

        logger.info(
            f"Discovered {len(enriched_feeds)} feeds from {request.website_url} in {discovery_time}ms"
        )

        return {"discovered_feeds": enriched_feeds, "discovery_time_ms": discovery_time}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        logger.error(f"Error discovering feeds: {str(e)}")
        return {
            "discovered_feeds": [],
            "discovery_time_ms": int((time.time() - start_time) * 1000),
            "error_message": "Could not discover feeds from this website. Try entering the feed URL directly.",
        }


@router.post("/user-feeds/validate", tags=["feeds"])
async def validate_feed_endpoint(
    request: FeedValidationRequest, user: User = Depends(get_current_user_dependency)
):
    """
    Validate feed URL before adding

    Args:
        request: Feed URL to validate

    Returns:
        - is_valid: Whether feed is valid
        - feed_metadata: Feed metadata if valid
        - error_message: Error message if invalid
    """
    try:
        # Validate feed
        validation_result = await validate_feed(request.feed_url)

        if not validation_result["is_valid"]:
            return {
                "is_valid": False,
                "error_message": validation_result.get("error_message", "Feed validation failed"),
            }

        # Parse metadata
        try:
            metadata = await parse_feed_metadata(request.feed_url)

            return {
                "is_valid": True,
                "feed_metadata": {
                    "title": metadata["title"],
                    "description": metadata["description"],
                    "type": metadata["feed_type"],
                    "item_count": metadata["item_count"],
                    "last_updated": metadata["last_updated"],
                    "website_url": metadata["website_url"],
                },
            }
        except Exception as e:
            logger.error(f"Error parsing feed metadata: {str(e)}")
            return {
                "is_valid": True,
                "feed_metadata": {
                    "title": "Feed",
                    "description": "",
                    "type": validation_result.get("feed_type", "rss"),
                    "item_count": 0,
                },
            }

    except Exception as e:
        logger.error(f"Error validating feed: {str(e)}")
        return {"is_valid": False, "error_message": f"Validation error: {str(e)}"}


@router.post("/user-feeds", status_code=status.HTTP_201_CREATED, tags=["feeds"])
async def create_feed(
    request: FeedCreateRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Add new feed to user's collection

    Args:
        request: Feed details

    Returns:
        - id: Feed ID
        - message: Success message
        - feed: Created feed object
    """
    try:
        # Check if feed already exists for user
        existing = db.execute(
            text(
                """
            SELECT id FROM user_feeds
            WHERE user_id = :user_id AND feed_url = :feed_url
        """
            ),
            {"user_id": user.id, "feed_url": request.feed_url},
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already added this feed. Each feed can only be added once.",
            )

        # Validate feed first
        validation = await validate_feed(request.feed_url)
        if not validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation.get("error_message", "Invalid feed URL"),
            )

        # Get feed metadata
        try:
            metadata = await parse_feed_metadata(request.feed_url)
            feed_type = metadata["feed_type"]
            website_url = metadata.get("website_url", "")
        except Exception:
            feed_type = validation.get("feed_type", "rss")
            website_url = ""

        # Insert feed
        result = db.execute(
            text(
                """
            INSERT INTO user_feeds (
                user_id, feed_url, feed_name, feed_description,
                feed_type, website_url, update_frequency,
                health_status, created_at, updated_at
            )
            VALUES (
                :user_id, :feed_url, :feed_name, :feed_description,
                :feed_type, :website_url, :update_frequency,
                'unknown', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            RETURNING id
        """
            ),
            {
                "user_id": user.id,
                "feed_url": request.feed_url,
                "feed_name": request.feed_name,
                "feed_description": request.feed_description,
                "feed_type": feed_type,
                "website_url": website_url,
                "update_frequency": request.update_frequency,
            },
        )

        # Fetch the feed_id BEFORE committing (SQLite requirement)
        feed_id = result.fetchone()[0]

        # Now commit the transaction
        db.commit()

        # Fetch created feed
        feed = db.execute(
            text(
                """
            SELECT * FROM user_feeds WHERE id = :id
        """
            ),
            {"id": feed_id},
        ).fetchone()

        logger.info(f"User {user.id} added feed: {request.feed_name} ({feed_id})")

        return {
            "id": feed_id,
            "message": "Feed added successfully",
            "feed": {
                "id": feed.id,
                "feed_url": feed.feed_url,
                "feed_name": feed.feed_name,
                "feed_type": feed.feed_type,
                "health_status": feed.health_status,
            },
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating feed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add feed. Please try again later.",
        )


@router.patch("/user-feeds/{feed_id}", tags=["feeds"])
async def update_feed(
    feed_id: int,
    request: FeedUpdateRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Update feed settings

    Args:
        feed_id: Feed ID to update
        request: Updated feed details

    Returns:
        Updated feed object
    """
    try:
        # Check feed exists and belongs to user
        feed = db.execute(
            text(
                """
            SELECT * FROM user_feeds
            WHERE id = :id AND user_id = :user_id
        """
            ),
            {"id": feed_id, "user_id": user.id},
        ).fetchone()

        if not feed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")

        # Build update query
        updates = []
        params = {"id": feed_id, "user_id": user.id}

        if request.feed_name is not None:
            updates.append("feed_name = :feed_name")
            params["feed_name"] = request.feed_name

        if request.feed_description is not None:
            updates.append("feed_description = :feed_description")
            params["feed_description"] = request.feed_description

        if request.update_frequency is not None:
            updates.append("update_frequency = :update_frequency")
            params["update_frequency"] = request.update_frequency

        if request.is_active is not None:
            updates.append("is_active = :is_active")
            params["is_active"] = request.is_active

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
            )

        # Add updated_at
        updates.append("updated_at = CURRENT_TIMESTAMP")

        # Execute update
        db.execute(
            text(
                f"""
            UPDATE user_feeds
            SET {', '.join(updates)}
            WHERE id = :id AND user_id = :user_id
        """
            ),
            params,
        )

        db.commit()

        # Fetch updated feed
        updated_feed = db.execute(
            text(
                """
            SELECT * FROM user_feeds WHERE id = :id
        """
            ),
            {"id": feed_id},
        ).fetchone()

        logger.info(f"User {user.id} updated feed {feed_id}")

        return {
            "id": updated_feed.id,
            "feed_url": updated_feed.feed_url,
            "feed_name": updated_feed.feed_name,
            "feed_description": updated_feed.feed_description,
            "update_frequency": updated_feed.update_frequency,
            "is_active": updated_feed.is_active,
            "updated_at": updated_feed.updated_at.isoformat() if updated_feed.updated_at else None,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating feed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update feed. Please try again later.",
        )


@router.delete("/user-feeds/{feed_id}", tags=["feeds"])
async def delete_feed(
    feed_id: int, user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Remove feed from user's collection

    Args:
        feed_id: Feed ID to delete

    Returns:
        Success message
    """
    try:
        # Check feed exists and belongs to user
        feed = db.execute(
            text(
                """
            SELECT * FROM user_feeds
            WHERE id = :id AND user_id = :user_id
        """
            ),
            {"id": feed_id, "user_id": user.id},
        ).fetchone()

        if not feed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")

        # Delete feed
        db.execute(
            text(
                """
            DELETE FROM user_feeds
            WHERE id = :id AND user_id = :user_id
        """
            ),
            {"id": feed_id, "user_id": user.id},
        )

        db.commit()

        logger.info(f"User {user.id} deleted feed {feed_id}")

        return {"message": "Feed removed successfully"}

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting feed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete feed. Please try again later.",
        )


@router.post("/user-feeds/{feed_id}/test", tags=["feeds"])
async def test_feed_connection(
    feed_id: int, user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Test feed connection and fetch preview

    Args:
        feed_id: Feed ID to test

    Returns:
        - status: success/error
        - fetch_time_ms: Time taken to fetch feed
        - items_found: Number of items in feed
        - preview_items: Sample items from feed
    """
    start_time = time.time()

    try:
        # Get feed
        feed = db.execute(
            text(
                """
            SELECT * FROM user_feeds
            WHERE id = :id AND user_id = :user_id
        """
            ),
            {"id": feed_id, "user_id": user.id},
        ).fetchone()

        if not feed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")

        # Validate feed
        validation = await validate_feed(feed.feed_url)

        if not validation["is_valid"]:
            fetch_time = int((time.time() - start_time) * 1000)
            return {
                "status": "error",
                "fetch_time_ms": fetch_time,
                "error_message": validation.get("error_message", "Feed test failed"),
            }

        # Get preview items
        preview = await get_feed_preview_items(feed.feed_url, limit=3)

        fetch_time = int((time.time() - start_time) * 1000)

        # Update feed health status
        db.execute(
            text(
                """
            UPDATE user_feeds
            SET
                health_status = 'healthy',
                last_fetched_at = CURRENT_TIMESTAMP,
                last_successful_fetch = CURRENT_TIMESTAMP,
                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """
            ),
            {"id": feed_id},
        )

        db.commit()

        logger.info(f"Feed {feed_id} tested successfully ({fetch_time}ms)")

        return {
            "status": "success",
            "fetch_time_ms": fetch_time,
            "items_found": preview["total_items"],
            "preview_items": preview["items"],
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error testing feed: {str(e)}")
        fetch_time = int((time.time() - start_time) * 1000)

        # Update feed with error
        try:
            db.execute(
                text(
                    """
                UPDATE user_feeds
                SET
                    health_status = 'error',
                    error_message = :error,
                    last_fetched_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """
                ),
                {"id": feed_id, "error": str(e)},
            )
            db.commit()
        except Exception:
            pass

        return {
            "status": "error",
            "fetch_time_ms": fetch_time,
            "error_message": f"Feed test failed: {str(e)}",
        }


@router.get("/user-feeds/health-dashboard", tags=["feeds"])
async def get_health_dashboard(
    user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Get overall feed health metrics

    Returns:
        - total_feeds: Total number of feeds
        - health_breakdown: Count by health status
        - uptime_percentage: Percentage of healthy feeds
        - feeds_needing_attention: Feeds with errors
    """
    try:
        # Get all feeds for user
        feeds = db.execute(
            text(
                """
            SELECT *
            FROM user_feeds
            WHERE user_id = :user_id
        """
            ),
            {"user_id": user.id},
        ).fetchall()

        total_feeds = len(feeds)

        if total_feeds == 0:
            return {
                "total_feeds": 0,
                "health_breakdown": {"healthy": 0, "warning": 0, "error": 0, "unknown": 0},
                "uptime_percentage": 100.0,
                "feeds_needing_attention": [],
            }

        # Count by health status
        health_breakdown = {"healthy": 0, "warning": 0, "error": 0, "unknown": 0}

        feeds_needing_attention = []

        for feed in feeds:
            health_status = feed.health_status or "unknown"
            health_breakdown[health_status] = health_breakdown.get(health_status, 0) + 1

            # Add to attention list if error or warning
            if health_status in ["error", "warning"]:
                feeds_needing_attention.append(
                    {
                        "id": feed.id,
                        "feed_name": feed.feed_name,
                        "error_message": feed.error_message,
                        "last_successful_fetch": feed.last_successful_fetch.isoformat()
                        if feed.last_successful_fetch
                        else None,
                    }
                )

        # Calculate uptime percentage
        healthy_count = health_breakdown.get("healthy", 0)
        uptime_percentage = (healthy_count / total_feeds * 100) if total_feeds > 0 else 0

        return {
            "total_feeds": total_feeds,
            "health_breakdown": health_breakdown,
            "uptime_percentage": round(uptime_percentage, 1),
            "feeds_needing_attention": feeds_needing_attention,
        }

    except Exception as e:
        logger.error(f"Error getting health dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve health dashboard",
        )


# ============================================================================
# SYSTEM SOURCES (Read-only from config)
# ============================================================================


@router.get("/system-sources", tags=["feeds"])
async def get_system_sources(current_user: User = Depends(get_current_user_dependency)):
    """
    Get system-wide RSS sources from config/sources.yaml

    These are read-only default sources that all users have access to.
    Returns: List of system RSS feed sources with metadata
    """
    try:
        # Find the sources.yaml file in backend directory
        import os
        backend_root = Path(__file__).parent.parent
        config_path = backend_root / "config" / "sources.yaml"

        if not config_path.exists():
            logger.warning(f"sources.yaml not found at {config_path}, returning empty list")
            return {"sources": [], "total_sources": 0}

        # Load sources from YAML
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Extract RSS feeds
        rss_feeds = config.get("sources", {}).get("rss_feeds", [])

        # Transform to match frontend expected format
        sources = []
        for idx, feed in enumerate(rss_feeds):
            sources.append(
                {
                    "id": f"system-{idx}",  # Use string ID to differentiate from user feeds
                    "feed_name": feed.get("name", "Unnamed Source"),
                    "feed_url": feed.get("url", ""),
                    "feed_description": f"Category: {feed.get('category', 'general')}",
                    "category": feed.get("category", "general"),
                    "feed_type": "rss",
                    "health_status": "unknown",  # System sources don't have health tracking
                    "is_active": True,
                    "is_system": True,  # Flag to indicate this is a system source
                    "created_at": None,
                    "last_fetched_at": None,
                    "total_items_fetched": 0,
                    "update_frequency": 3600,
                }
            )

        return {
            "sources": sources,
            "total_sources": len(sources),
            "categories": list(set(s["category"] for s in sources)),
        }

    except Exception as e:
        logger.error(f"Error loading system sources: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load system sources: {str(e)}",
        )
