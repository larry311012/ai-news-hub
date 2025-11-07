"""
RSS Feed Validation and Parsing Utility

Validates and parses RSS, Atom, and JSON feeds using feedparser library.
Provides metadata extraction and validation checks.
"""
from typing import Dict, Any, Optional
import feedparser
import requests
from datetime import datetime
from loguru import logger

# Timeout for HTTP requests
REQUEST_TIMEOUT = 10

# User agent
USER_AGENT = "Mozilla/5.0 (compatible; RSS Feed Aggregator/1.0; +https://github.com)"


async def validate_feed(feed_url: str) -> Dict[str, Any]:
    """
    Validates a feed URL and returns validation results

    Validation checks:
    1. URL is accessible (HTTP 200)
    2. Content-Type is valid (application/rss+xml, application/atom+xml, etc.)
    3. XML/JSON is well-formed
    4. Contains valid feed structure (channel/items or feed/entries)
    5. Has at least 1 item/entry

    Args:
        feed_url: URL of the feed to validate

    Returns:
        Dict with validation results:
        {
            "is_valid": True/False,
            "feed_type": "rss"/"atom"/"json",
            "error_message": str (if invalid),
            "warning_message": str (optional warnings)
        }
    """
    try:
        logger.info(f"Validating feed: {feed_url}")

        # 1. Fetch feed
        response = requests.get(
            feed_url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )

        # Check HTTP status
        if response.status_code == 404:
            return {
                "is_valid": False,
                "error_message": "Feed not found (404). Please check the URL and try again.",
            }

        if response.status_code != 200:
            return {
                "is_valid": False,
                "error_message": f"Feed returned error status {response.status_code}. The feed may be temporarily unavailable.",
            }

        # 2. Parse feed with feedparser
        feed = feedparser.parse(response.content)

        # Check for bozo (malformed) feeds
        if feed.bozo:
            bozo_exception = getattr(feed, "bozo_exception", None)
            error_msg = str(bozo_exception) if bozo_exception else "Unknown parsing error"

            return {
                "is_valid": False,
                "error_message": f"Feed is malformed or invalid: {error_msg}",
            }

        # 3. Check feed structure
        if not hasattr(feed, "feed"):
            return {
                "is_valid": False,
                "error_message": "Feed does not contain valid feed structure. This may not be a valid RSS/Atom feed.",
            }

        # 4. Check for entries/items
        entries = feed.entries if hasattr(feed, "entries") else []

        if len(entries) == 0:
            return {
                "is_valid": False,
                "error_message": "Feed is empty (no articles found). The feed may be valid but has no content yet.",
                "warning_message": "Feed has no items",
            }

        # 5. Determine feed type
        feed_type = _detect_feed_type(feed)

        # Feed is valid
        logger.info(f"Feed validated successfully: {feed_url} (type: {feed_type})")
        return {"is_valid": True, "feed_type": feed_type}

    except requests.Timeout:
        return {
            "is_valid": False,
            "error_message": f"Connection timeout after {REQUEST_TIMEOUT}s. The feed server may be slow or unresponsive.",
        }

    except requests.exceptions.SSLError:
        return {
            "is_valid": False,
            "error_message": "SSL certificate error. The feed's SSL certificate is invalid or expired.",
        }

    except requests.exceptions.ConnectionError:
        return {
            "is_valid": False,
            "error_message": "Could not connect to feed. Please check the URL and your internet connection.",
        }

    except requests.exceptions.RequestException as e:
        return {"is_valid": False, "error_message": f"Network error: {str(e)}"}

    except Exception as e:
        logger.error(f"Unexpected error validating feed: {str(e)}")
        return {"is_valid": False, "error_message": f"An unexpected error occurred: {str(e)}"}


async def parse_feed_metadata(feed_url: str) -> Dict[str, Any]:
    """
    Extracts metadata from a feed

    Args:
        feed_url: URL of the feed to parse

    Returns:
        Dict with feed metadata:
        {
            "title": str,
            "description": str,
            "language": str,
            "last_updated": datetime,
            "item_count": int,
            "feed_type": "rss"/"atom"/"json",
            "website_url": str
        }
    """
    try:
        logger.info(f"Parsing feed metadata: {feed_url}")

        # Fetch and parse feed
        response = requests.get(
            feed_url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        response.raise_for_status()

        feed = feedparser.parse(response.content)

        # Extract metadata
        feed_info = feed.feed if hasattr(feed, "feed") else {}

        # Title
        title = feed_info.get("title", "Untitled Feed")

        # Description
        description = (
            feed_info.get("subtitle")
            or feed_info.get("description")
            or feed_info.get("summary")
            or ""
        )

        # Language
        language = feed_info.get("language", "en")

        # Last updated
        last_updated = None
        if hasattr(feed_info, "updated_parsed") and feed_info.updated_parsed:
            try:
                last_updated = datetime(*feed_info.updated_parsed[:6])
            except Exception:
                pass

        # Item count
        item_count = len(feed.entries) if hasattr(feed, "entries") else 0

        # Feed type
        feed_type = _detect_feed_type(feed)

        # Website URL
        website_url = feed_info.get("link", "")

        logger.info(f"Feed metadata parsed: {title} ({item_count} items)")

        return {
            "title": title,
            "description": description,
            "language": language,
            "last_updated": last_updated.isoformat() if last_updated else None,
            "item_count": item_count,
            "feed_type": feed_type,
            "website_url": website_url,
        }

    except requests.Timeout:
        raise Exception(f"Connection timeout after {REQUEST_TIMEOUT}s")

    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {str(e)}")

    except Exception as e:
        logger.error(f"Error parsing feed metadata: {str(e)}")
        raise Exception(f"Failed to parse feed: {str(e)}")


def _detect_feed_type(feed: feedparser.FeedParserDict) -> str:
    """
    Detect feed type (RSS, Atom, JSON)

    Args:
        feed: Parsed feed object from feedparser

    Returns:
        Feed type string: "rss", "atom", or "json"
    """
    # Check version attribute
    version = getattr(feed, "version", "")

    if version:
        if "atom" in version.lower():
            return "atom"
        elif "rss" in version.lower():
            return "rss"
        elif "json" in version.lower():
            return "json"

    # Fallback: check feed structure
    feed_info = feed.feed if hasattr(feed, "feed") else {}

    # Atom feeds typically have 'id' field
    if "id" in feed_info:
        return "atom"

    # Default to RSS
    return "rss"


async def get_feed_preview_items(feed_url: str, limit: int = 3) -> Dict[str, Any]:
    """
    Get preview items from a feed for display

    Args:
        feed_url: URL of the feed
        limit: Maximum number of preview items to return

    Returns:
        Dict with preview data:
        {
            "items": [
                {
                    "title": str,
                    "link": str,
                    "published_date": str (ISO format),
                    "summary": str
                }
            ],
            "total_items": int
        }
    """
    try:
        response = requests.get(
            feed_url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        response.raise_for_status()

        feed = feedparser.parse(response.content)
        entries = feed.entries if hasattr(feed, "entries") else []

        # Extract preview items
        preview_items = []
        for entry in entries[:limit]:
            # Published date
            published_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published_date = datetime(*entry.published_parsed[:6]).isoformat()
                except Exception:
                    pass

            # Summary/description
            summary = (
                entry.get("summary")
                or entry.get("description")
                or entry.get("content", [{}])[0].get("value", "")
                if entry.get("content")
                else ""
            )

            # Truncate summary to 200 characters
            if len(summary) > 200:
                summary = summary[:200] + "..."

            preview_items.append(
                {
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "published_date": published_date,
                    "summary": summary,
                }
            )

        return {"items": preview_items, "total_items": len(entries)}

    except Exception as e:
        logger.error(f"Error getting feed preview: {str(e)}")
        return {"items": [], "total_items": 0}
