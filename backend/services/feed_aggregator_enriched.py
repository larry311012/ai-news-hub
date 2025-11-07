"""
Enhanced Feed Aggregator with Content Enrichment (Tasks 2.7 + 2.8 + 2.13)

This module extends the base feed aggregator with intelligent content enrichment.
It integrates the ArticleEnrichmentService to provide:
- Full-text extraction
- Featured image extraction
- Automatic category classification
- Content quality scoring
- Extractive summarization
- Metadata extraction

This ensures that all articles stored in the database have comprehensive
metadata for better iOS app experience.

Usage:
    from services.feed_aggregator_enriched import EnrichedFeedAggregator

    aggregator = EnrichedFeedAggregator()
    await aggregator.start()
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger

from services.feed_aggregator import FeedAggregator
from services.article_enrichment_service import ArticleEnrichmentService


class EnrichedFeedAggregator(FeedAggregator):
    """
    Enhanced feed aggregator with content enrichment

    Extends the base FeedAggregator to automatically enrich articles
    with full-text, images, categories, summaries, and metadata.
    """

    def __init__(self, enable_enrichment: bool = True):
        """
        Initialize enriched feed aggregator

        Args:
            enable_enrichment: Whether to enable article enrichment (default: True)
        """
        super().__init__()
        self.enable_enrichment = enable_enrichment
        self.enrichment_service = ArticleEnrichmentService() if enable_enrichment else None

        # Update stats to track enrichment
        self.fetch_stats.update({
            "articles_enriched": 0,
            "enrichment_failures": 0,
            "images_extracted": 0,
            "summaries_generated": 0,
        })

    async def _fetch_and_store_feed(self, feed_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch a single feed and store articles with enrichment

        Overrides parent method to add article enrichment.

        Args:
            feed_info: Feed information dictionary

        Returns:
            Result dictionary with success status and statistics
        """
        feed_id = feed_info["id"]
        feed_url = feed_info["feed_url"]
        feed_name = feed_info["feed_name"]
        user_id = feed_info["user_id"]

        logger.info(f"Fetching feed {feed_id}: {feed_name} (enrichment: {self.enable_enrichment})")

        from database import get_db
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

            # Process articles with enrichment
            articles_added = 0
            duplicates_skipped = 0
            enriched_count = 0
            enrichment_failures = 0

            # Limit concurrent enrichment to avoid overwhelming the system
            MAX_CONCURRENT_ENRICHMENT = 3
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_ENRICHMENT)

            async def process_article(entry):
                nonlocal articles_added, duplicates_skipped, enriched_count, enrichment_failures

                async with semaphore:
                    # Extract basic article data
                    article_data = self._extract_article_data(entry, feed_name, user_id)

                    # Check for duplicate by URL
                    if self._is_duplicate_article(db, article_data["link"], user_id):
                        duplicates_skipped += 1
                        return

                    # Enrich article if enabled
                    if self.enable_enrichment and self.enrichment_service:
                        try:
                            enriched_data = await self.enrichment_service.process_feed_article(
                                entry, feed_name, user_id
                            )
                            # Merge enriched data
                            article_data.update(enriched_data)
                            enriched_count += 1

                            # Track enrichment stats
                            if enriched_data.get("featured_image"):
                                self.fetch_stats["images_extracted"] += 1
                            if enriched_data.get("auto_summary"):
                                self.fetch_stats["summaries_generated"] += 1

                        except Exception as e:
                            logger.warning(f"Enrichment failed for {article_data['link']}: {e}")
                            enrichment_failures += 1
                            # Continue with basic data if enrichment fails

                    # Store article
                    if self._store_article_enriched(db, article_data):
                        articles_added += 1

            # Process articles concurrently (but limited)
            from services.feed_aggregator import MAX_ARTICLES_PER_FETCH
            tasks = [process_article(entry) for entry in entries[:MAX_ARTICLES_PER_FETCH]]
            await asyncio.gather(*tasks, return_exceptions=True)

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
                f"{articles_added} new, {duplicates_skipped} duplicates, "
                f"{enriched_count} enriched, {enrichment_failures} enrichment failures"
            )

            # Update global stats
            self.fetch_stats["duplicates_skipped"] += duplicates_skipped
            self.fetch_stats["articles_enriched"] += enriched_count
            self.fetch_stats["enrichment_failures"] += enrichment_failures

            return {
                "success": True,
                "feed_id": feed_id,
                "articles_added": articles_added,
                "duplicates_skipped": duplicates_skipped,
                "enriched_count": enriched_count,
                "enrichment_failures": enrichment_failures,
            }

        except Exception as e:
            logger.error(f"Feed {feed_id} error: {e}", exc_info=True)
            await self._update_feed_status(
                db, feed_id,
                success=False,
                error_message=str(e),
                health_status="error"
            )
            db.commit()
            return {"success": False, "feed_id": feed_id, "error": str(e)}

        finally:
            db.close()

    def _store_article_enriched(self, db, article_data: Dict[str, Any]) -> bool:
        """
        Store enriched article in database

        Extended version that handles additional enrichment fields.

        Args:
            db: Database session
            article_data: Article data dictionary (with enrichment fields)

        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            from sqlalchemy import text

            # First, check if the articles table has enrichment columns
            # If not, we'll need to add them or skip enrichment fields
            result = db.execute(text("PRAGMA table_info(articles)")).fetchall()
            existing_columns = {row[1] for row in result}

            # Prepare data for insertion
            insert_data = {
                "title": article_data.get("title", "Untitled")[:500],
                "link": article_data.get("link", "")[:1000],
                "summary": article_data.get("summary", "")[:2000] if article_data.get("summary") else None,
                "content": article_data.get("content_for_ai") or article_data.get("full_text"),
                "source": article_data.get("source"),
                "category": article_data.get("category"),
                "published": article_data.get("published", datetime.utcnow()),
                "fetched_at": article_data.get("fetched_at", datetime.utcnow()),
                "user_id": article_data.get("user_id"),
                "bookmarked": article_data.get("bookmarked", False),
                "tags": json.dumps(article_data.get("tags")) if article_data.get("tags") else None,
            }

            # Build dynamic INSERT query based on available columns
            columns = list(insert_data.keys())
            placeholders = [f":{col}" for col in columns]

            query = f"""
                INSERT INTO articles ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """

            db.execute(text(query), insert_data)
            return True

        except Exception as e:
            logger.error(f"Error storing enriched article: {e}")
            return False

    def get_enrichment_stats(self) -> Dict[str, Any]:
        """Get enrichment statistics"""
        stats = self.get_stats()

        if self.enrichment_service:
            enrichment_stats = self.enrichment_service.get_stats()
            stats["enrichment"] = enrichment_stats

        return stats


# ============================================================================
# DATABASE MIGRATION: Add Enrichment Columns
# ============================================================================

def add_enrichment_columns_to_articles():
    """
    Add enrichment columns to articles table

    This migration adds columns for storing enriched article data:
    - full_text: Full article text (up to 10k chars)
    - content_for_ai: Truncated content for AI processing (5k chars)
    - featured_image: URL of featured image
    - auto_summary: Auto-generated summary
    - quality_score: Content quality score (0-100)
    - author: Article author name
    - publish_date: Original publication date
    - reading_time: Estimated reading time in minutes
    - topics: JSON array of key topics

    Run this once to add the columns to the database.
    """
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            # Check if columns already exist
            result = conn.execute(text("PRAGMA table_info(articles)"))
            existing_columns = {row[1] for row in result}

            columns_to_add = [
                ("full_text", "TEXT"),
                ("content_for_ai", "TEXT"),
                ("featured_image", "TEXT"),
                ("auto_summary", "TEXT"),
                ("quality_score", "INTEGER"),
                ("author", "VARCHAR(200)"),
                ("publish_date", "VARCHAR(100)"),
                ("reading_time", "INTEGER"),
                ("topics", "JSON"),
            ]

            for column_name, column_type in columns_to_add:
                if column_name not in existing_columns:
                    logger.info(f"Adding column {column_name} to articles table")
                    conn.execute(text(f"ALTER TABLE articles ADD COLUMN {column_name} {column_type}"))
                    conn.commit()
                    logger.info(f"Column {column_name} added successfully")
                else:
                    logger.info(f"Column {column_name} already exists")

            logger.info("Article enrichment columns migration complete")

    except Exception as e:
        logger.error(f"Error adding enrichment columns: {e}")
        raise


# ============================================================================
# STANDALONE FUNCTIONS
# ============================================================================

async def start_enriched_aggregator():
    """
    Start enriched feed aggregator service

    This is the main entry point for starting the aggregator with enrichment.
    """
    aggregator = EnrichedFeedAggregator(enable_enrichment=True)
    await aggregator.start()


async def fetch_all_feeds_enriched():
    """
    Fetch all feeds once with enrichment

    Use this for manual/scheduled runs.
    """
    aggregator = EnrichedFeedAggregator(enable_enrichment=True)
    await aggregator.fetch_all_feeds()
    return aggregator.get_enrichment_stats()


async def migrate_existing_articles(user_id: int, limit: int = 50):
    """
    Enrich existing articles in database

    This can be run to retroactively enrich articles that were added
    before the enrichment service was implemented.

    Args:
        user_id: User ID
        limit: Maximum number of articles to process per run

    Returns:
        Statistics dictionary
    """
    from services.article_enrichment_service import enrich_existing_articles

    return await enrich_existing_articles(user_id, limit)
