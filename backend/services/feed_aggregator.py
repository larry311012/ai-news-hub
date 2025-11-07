"""
Article Aggregation Service (Task 2.7)

Background service that continuously fetches and aggregates articles from RSS feeds.

Features:
- Fetches all active feeds every 15 minutes
- Parses RSS 2.0, Atom, and JSON Feed formats
- Deduplicates articles by URL
- Stores articles in database
- Updates feed statistics
- Implements rate limiting and exponential backoff
- Tracks feed health and marks inactive feeds
- Handles errors gracefully

Architecture:
- Async/await for concurrent fetching
- Per-feed rate limiting
- Exponential backoff for failed feeds
- Feed health monitoring
- Graceful error handling

Usage:
    # Start background aggregator
    aggregator = FeedAggregator()
    await aggregator.start()

    # Or run once manually
    await aggregator.fetch_all_feeds()
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
import feedparser
import requests
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from database import get_db, engine
from utils.feed_validator import REQUEST_TIMEOUT, USER_AGENT


# ============================================================================
# CONFIGURATION
# ============================================================================

# Fetch interval (15 minutes)
FETCH_INTERVAL_SECONDS = 15 * 60

# Maximum concurrent feed fetches
MAX_CONCURRENT_FETCHES = 10

# Maximum consecutive failures before marking feed inactive
MAX_CONSECUTIVE_FAILURES = 10

# Minimum time between fetches for same feed (seconds)
MIN_FETCH_INTERVAL = 300  # 5 minutes

# Request timeout
FETCH_TIMEOUT = 15  # 15 seconds

# Maximum articles to store per fetch
MAX_ARTICLES_PER_FETCH = 100


# ============================================================================
# FEED AGGREGATOR SERVICE
# ============================================================================


class FeedAggregator:
    """
    Background service for fetching and aggregating RSS feeds

    Continuously fetches articles from all active user feeds,
    deduplicates, and stores them in the database.
    """

    def __init__(self):
        self.running = False
        self.fetch_stats = {
            "total_fetches": 0,
            "successful_fetches": 0,
            "failed_fetches": 0,
            "articles_added": 0,
            "duplicates_skipped": 0,
            "last_run": None,
        }

    async def start(self):
        """
        Start the background aggregation service

        Runs continuously, fetching feeds every 15 minutes.
        """
        self.running = True
        logger.info("Feed aggregator service started")

        while self.running:
            try:
                # Fetch all feeds
                await self.fetch_all_feeds()

                # Update stats
                self.fetch_stats["last_run"] = datetime.utcnow()

                # Wait for next interval
                logger.info(f"Feed fetch complete. Next run in {FETCH_INTERVAL_SECONDS}s")
                await asyncio.sleep(FETCH_INTERVAL_SECONDS)

            except Exception as e:
                logger.error(f"Error in feed aggregator main loop: {e}")
                # Wait a bit before retrying to avoid tight error loops
                await asyncio.sleep(60)

    def stop(self):
        """Stop the background aggregation service"""
        self.running = False
        logger.info("Feed aggregator service stopped")

    async def fetch_all_feeds(self):
        """
        Fetch all active feeds from all users

        Fetches feeds concurrently with rate limiting.
        Updates feed statistics and health status.
        """
        logger.info("Starting feed aggregation cycle")
        start_time = datetime.utcnow()

        # Get all active feeds that need fetching
        feeds_to_fetch = self._get_feeds_to_fetch()

        if not feeds_to_fetch:
            logger.info("No feeds need fetching at this time")
            return

        logger.info(f"Found {len(feeds_to_fetch)} feeds to fetch")

        # Fetch feeds concurrently with semaphore for rate limiting
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)

        async def fetch_with_semaphore(feed):
            async with semaphore:
                return await self._fetch_and_store_feed(feed)

        # Execute all fetches concurrently
        results = await asyncio.gather(
            *[fetch_with_semaphore(feed) for feed in feeds_to_fetch],
            return_exceptions=True
        )

        # Calculate statistics
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful
        total_articles = sum(
            r.get("articles_added", 0)
            for r in results
            if isinstance(r, dict)
        )

        elapsed = (datetime.utcnow() - start_time).total_seconds()

        logger.info(
            f"Feed aggregation complete: "
            f"{successful} successful, {failed} failed, "
            f"{total_articles} new articles in {elapsed:.1f}s"
        )

        # Update global stats
        self.fetch_stats["total_fetches"] += len(feeds_to_fetch)
        self.fetch_stats["successful_fetches"] += successful
        self.fetch_stats["failed_fetches"] += failed
        self.fetch_stats["articles_added"] += total_articles

    def _get_feeds_to_fetch(self) -> List[Dict[str, Any]]:
        """
        Get all feeds that need fetching

        Returns feeds that are:
        - Active (is_active = True)
        - Not fetched recently (respects update_frequency)
        - Not in exponential backoff period (for failing feeds)

        Returns:
            List of feed dictionaries
        """
        db = next(get_db())

        try:
            # Calculate cutoff time based on update frequency
            now = datetime.utcnow()

            query = text("""
                SELECT
                    id,
                    user_id,
                    feed_url,
                    feed_name,
                    feed_type,
                    update_frequency,
                    last_fetched_at,
                    last_successful_fetch,
                    health_status,
                    error_message,
                    total_items_fetched,
                    COALESCE(consecutive_failures, 0) as consecutive_failures
                FROM user_feeds
                WHERE is_active = 1
                AND (
                    last_fetched_at IS NULL
                    OR datetime(last_fetched_at, '+' || update_frequency || ' seconds') <= datetime('now')
                )
                ORDER BY last_fetched_at ASC NULLS FIRST
            """)

            result = db.execute(query)
            feeds = []

            for row in result:
                # Skip feeds with too many consecutive failures
                consecutive_failures = row.consecutive_failures or 0

                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.warning(
                        f"Skipping feed {row.id} ({row.feed_name}): "
                        f"{consecutive_failures} consecutive failures"
                    )
                    continue

                # Calculate backoff delay for failing feeds
                if consecutive_failures > 0:
                    # Exponential backoff: 5min, 10min, 20min, 40min, etc.
                    backoff_seconds = MIN_FETCH_INTERVAL * (2 ** consecutive_failures)

                    if row.last_fetched_at:
                        next_fetch_time = row.last_fetched_at + timedelta(seconds=backoff_seconds)

                        if datetime.utcnow() < next_fetch_time:
                            logger.debug(
                                f"Skipping feed {row.id} ({row.feed_name}): "
                                f"in backoff period until {next_fetch_time}"
                            )
                            continue

                feeds.append({
                    "id": row.id,
                    "user_id": row.user_id,
                    "feed_url": row.feed_url,
                    "feed_name": row.feed_name,
                    "feed_type": row.feed_type,
                    "update_frequency": row.update_frequency,
                    "last_fetched_at": row.last_fetched_at,
                    "last_successful_fetch": row.last_successful_fetch,
                    "health_status": row.health_status,
                    "consecutive_failures": consecutive_failures,
                })

            return feeds

        finally:
            db.close()

    @retry(
        retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logger.level("WARNING").name),
    )
    async def _fetch_feed_with_retry(self, feed_url: str) -> feedparser.FeedParserDict:
        """
        Fetch and parse feed with automatic retries

        Uses exponential backoff for transient network errors.

        Args:
            feed_url: URL of the feed to fetch

        Returns:
            Parsed feed object

        Raises:
            Exception: If fetch fails after retries
        """
        logger.debug(f"Fetching feed: {feed_url}")

        response = requests.get(
            feed_url,
            timeout=FETCH_TIMEOUT,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
            },
            allow_redirects=True,
        )

        response.raise_for_status()

        # Parse feed
        feed = feedparser.parse(response.content)

        # Check for parsing errors
        if feed.bozo:
            bozo_exception = getattr(feed, "bozo_exception", None)
            logger.warning(f"Feed has parsing issues: {bozo_exception}")
            # Continue anyway - many feeds have minor issues but are usable

        return feed

    async def _fetch_and_store_feed(self, feed_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch a single feed and store articles

        Handles:
        - Feed fetching with retries
        - Article extraction and parsing
        - Deduplication by URL
        - Database storage
        - Feed statistics update
        - Health status tracking
        - Error handling

        Args:
            feed_info: Feed information dictionary

        Returns:
            Result dictionary with success status and statistics
        """
        feed_id = feed_info["id"]
        feed_url = feed_info["feed_url"]
        feed_name = feed_info["feed_name"]
        user_id = feed_info["user_id"]

        logger.info(f"Fetching feed {feed_id}: {feed_name}")

        db = next(get_db())

        try:
            # Fetch and parse feed
            feed = await self._fetch_feed_with_retry(feed_url)

            # Extract articles
            entries = feed.entries if hasattr(feed, "entries") else []

            if not entries:
                logger.warning(f"Feed {feed_id} has no articles")
                await self._update_feed_status(
                    db, feed_id,
                    success=True,
                    error_message="Feed is empty",
                    health_status="warning",
                    articles_count=0
                )
                return {
                    "success": True,
                    "feed_id": feed_id,
                    "articles_added": 0,
                    "duplicates_skipped": 0,
                }

            # Process articles
            articles_added = 0
            duplicates_skipped = 0

            for entry in entries[:MAX_ARTICLES_PER_FETCH]:
                # Extract article data
                article_data = self._extract_article_data(entry, feed_name, user_id)

                # Check for duplicate by URL
                if self._is_duplicate_article(db, article_data["link"], user_id):
                    duplicates_skipped += 1
                    continue

                # Store article
                if self._store_article(db, article_data):
                    articles_added += 1

            db.commit()

            # Update feed status
            await self._update_feed_status(
                db, feed_id,
                success=True,
                health_status="healthy",
                articles_count=articles_added
            )

            logger.info(
                f"Feed {feed_id} processed: "
                f"{articles_added} new, {duplicates_skipped} duplicates"
            )

            # Update global stats
            self.fetch_stats["duplicates_skipped"] += duplicates_skipped

            return {
                "success": True,
                "feed_id": feed_id,
                "articles_added": articles_added,
                "duplicates_skipped": duplicates_skipped,
            }

        except requests.Timeout:
            error_msg = f"Timeout fetching feed after {FETCH_TIMEOUT}s"
            logger.warning(f"Feed {feed_id}: {error_msg}")
            await self._update_feed_status(
                db, feed_id,
                success=False,
                error_message=error_msg,
                health_status="error"
            )
            db.commit()
            return {"success": False, "feed_id": feed_id, "error": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            logger.warning(f"Feed {feed_id}: {error_msg}")
            await self._update_feed_status(
                db, feed_id,
                success=False,
                error_message=error_msg,
                health_status="error"
            )
            db.commit()
            return {"success": False, "feed_id": feed_id, "error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Feed {feed_id}: {error_msg}", exc_info=True)
            await self._update_feed_status(
                db, feed_id,
                success=False,
                error_message=error_msg,
                health_status="error"
            )
            db.commit()
            return {"success": False, "feed_id": feed_id, "error": error_msg}

        finally:
            db.close()

    def _extract_article_data(
        self,
        entry: feedparser.FeedParserDict,
        source: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Extract article data from feed entry

        Args:
            entry: Feed entry object
            source: Feed source name
            user_id: User ID who owns the feed

        Returns:
            Article data dictionary
        """
        # Title
        title = entry.get("title", "Untitled")

        # Link (required for deduplication)
        link = entry.get("link", "")

        # Summary/description
        summary = entry.get("summary") or entry.get("description")

        # If no summary/description, try to get from content
        if not summary and entry.get("content"):
            summary = entry.get("content", [{}])[0].get("value", "")

        # Content (full article text if available)
        content = None
        if entry.get("content"):
            content = entry.content[0].get("value", "")
        elif entry.get("description"):
            content = entry.description

        # Published date
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6])
            except Exception:
                pass

        # If no published date, try updated date
        if not published and hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                published = datetime(*entry.updated_parsed[:6])
            except Exception:
                pass

        # Category/tags
        category = None
        tags = []

        if entry.get("tags"):
            tags = [tag.get("term", "") for tag in entry.tags if tag.get("term")]
            if tags:
                category = tags[0]  # Use first tag as category

        # If no category from tags, try category field
        if not category and entry.get("category"):
            category = entry.category

        return {
            "title": title[:500] if title else "Untitled",  # Truncate title
            "link": link[:1000] if link else "",  # Truncate link
            "summary": summary[:2000] if summary else None,  # Truncate summary
            "content": content,
            "source": source,
            "category": category,
            "published": published or datetime.utcnow(),
            "fetched_at": datetime.utcnow(),
            "user_id": user_id,
            "bookmarked": False,
            "tags": tags[:10] if tags else None,  # Limit to 10 tags
        }

    def _is_duplicate_article(self, db: Session, link: str, user_id: int) -> bool:
        """
        Check if article already exists for user

        Deduplication is based on article URL (link).

        Args:
            db: Database session
            link: Article URL
            user_id: User ID

        Returns:
            True if article already exists, False otherwise
        """
        if not link:
            return False

        result = db.execute(
            text("""
                SELECT 1 FROM articles
                WHERE link = :link AND user_id = :user_id
                LIMIT 1
            """),
            {"link": link, "user_id": user_id}
        ).fetchone()

        return result is not None

    def _store_article(self, db: Session, article_data: Dict[str, Any]) -> bool:
        """
        Store article in database

        Args:
            db: Database session
            article_data: Article data dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            import json

            db.execute(
                text("""
                    INSERT INTO articles (
                        title, link, summary, content, source, category,
                        published, fetched_at, user_id, bookmarked, tags
                    ) VALUES (
                        :title, :link, :summary, :content, :source, :category,
                        :published, :fetched_at, :user_id, :bookmarked, :tags
                    )
                """),
                {
                    **article_data,
                    "tags": json.dumps(article_data.get("tags")) if article_data.get("tags") else None,
                }
            )
            return True

        except Exception as e:
            logger.error(f"Error storing article: {e}")
            return False

    async def _update_feed_status(
        self,
        db: Session,
        feed_id: int,
        success: bool,
        error_message: Optional[str] = None,
        health_status: Optional[str] = None,
        articles_count: int = 0,
    ):
        """
        Update feed status after fetch attempt

        Tracks:
        - Last fetch time
        - Last successful fetch time
        - Consecutive failures
        - Health status
        - Error message
        - Total items fetched
        - Inactive status (after MAX_CONSECUTIVE_FAILURES)

        Args:
            db: Database session
            feed_id: Feed ID
            success: Whether fetch was successful
            error_message: Error message if failed
            health_status: Health status (healthy/warning/error)
            articles_count: Number of articles fetched
        """
        try:
            # First, add consecutive_failures column if it doesn't exist
            self._ensure_consecutive_failures_column(db)

            if success:
                # Reset consecutive failures on success
                db.execute(
                    text("""
                        UPDATE user_feeds
                        SET
                            last_fetched_at = :now,
                            last_successful_fetch = :now,
                            consecutive_failures = 0,
                            health_status = :health_status,
                            error_message = :error_message,
                            total_items_fetched = total_items_fetched + :articles_count,
                            updated_at = :now
                        WHERE id = :feed_id
                    """),
                    {
                        "feed_id": feed_id,
                        "now": datetime.utcnow(),
                        "health_status": health_status or "healthy",
                        "error_message": error_message,
                        "articles_count": articles_count,
                    }
                )
            else:
                # Increment consecutive failures
                db.execute(
                    text("""
                        UPDATE user_feeds
                        SET
                            last_fetched_at = :now,
                            consecutive_failures = COALESCE(consecutive_failures, 0) + 1,
                            health_status = :health_status,
                            error_message = :error_message,
                            updated_at = :now
                        WHERE id = :feed_id
                    """),
                    {
                        "feed_id": feed_id,
                        "now": datetime.utcnow(),
                        "health_status": health_status or "error",
                        "error_message": error_message,
                    }
                )

                # Check if we should mark feed as inactive
                result = db.execute(
                    text("""
                        SELECT consecutive_failures
                        FROM user_feeds
                        WHERE id = :feed_id
                    """),
                    {"feed_id": feed_id}
                ).fetchone()

                if result and result.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.warning(
                        f"Marking feed {feed_id} as inactive after "
                        f"{result.consecutive_failures} consecutive failures"
                    )

                    db.execute(
                        text("""
                            UPDATE user_feeds
                            SET
                                is_active = 0,
                                health_status = 'error',
                                error_message = :error_message
                            WHERE id = :feed_id
                        """),
                        {
                            "feed_id": feed_id,
                            "error_message": (
                                f"Feed marked inactive after {MAX_CONSECUTIVE_FAILURES} "
                                f"consecutive failures. Please check the feed URL."
                            )
                        }
                    )

        except Exception as e:
            logger.error(f"Error updating feed status: {e}")

    def _ensure_consecutive_failures_column(self, db: Session):
        """
        Ensure consecutive_failures column exists in user_feeds table

        This is a migration helper that adds the column if it doesn't exist.
        """
        try:
            # Check if column exists
            result = db.execute(
                text("PRAGMA table_info(user_feeds)")
            ).fetchall()

            columns = [row[1] for row in result]

            if "consecutive_failures" not in columns:
                logger.info("Adding consecutive_failures column to user_feeds table")
                db.execute(
                    text("""
                        ALTER TABLE user_feeds
                        ADD COLUMN consecutive_failures INTEGER DEFAULT 0
                    """)
                )
                db.commit()
                logger.info("Column added successfully")

        except Exception as e:
            logger.error(f"Error adding consecutive_failures column: {e}")
            # Continue anyway - column might already exist

    def get_stats(self) -> Dict[str, Any]:
        """
        Get aggregator statistics

        Returns:
            Dictionary with statistics
        """
        return {
            **self.fetch_stats,
            "running": self.running,
        }


# ============================================================================
# STANDALONE FUNCTIONS
# ============================================================================


async def fetch_all_feeds_once():
    """
    Fetch all feeds once (for manual/scheduled runs)

    This can be called from a cron job or scheduled task.
    """
    aggregator = FeedAggregator()
    await aggregator.fetch_all_feeds()
    return aggregator.get_stats()


async def fetch_single_feed(feed_id: int) -> Dict[str, Any]:
    """
    Fetch a single feed by ID

    Useful for testing or manual refresh.

    Args:
        feed_id: Feed ID to fetch

    Returns:
        Result dictionary
    """
    db = next(get_db())

    try:
        # Get feed info
        result = db.execute(
            text("""
                SELECT
                    id, user_id, feed_url, feed_name, feed_type,
                    update_frequency, last_fetched_at, last_successful_fetch,
                    health_status, COALESCE(consecutive_failures, 0) as consecutive_failures
                FROM user_feeds
                WHERE id = :feed_id
            """),
            {"feed_id": feed_id}
        ).fetchone()

        if not result:
            return {"success": False, "error": "Feed not found"}

        feed_info = {
            "id": result.id,
            "user_id": result.user_id,
            "feed_url": result.feed_url,
            "feed_name": result.feed_name,
            "feed_type": result.feed_type,
            "update_frequency": result.update_frequency,
            "last_fetched_at": result.last_fetched_at,
            "last_successful_fetch": result.last_successful_fetch,
            "health_status": result.health_status,
            "consecutive_failures": result.consecutive_failures,
        }

        # Fetch and store
        aggregator = FeedAggregator()
        return await aggregator._fetch_and_store_feed(feed_info)

    finally:
        db.close()
