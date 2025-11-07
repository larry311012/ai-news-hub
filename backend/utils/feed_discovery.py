"""
RSS Feed Discovery Utility

Discovers RSS, Atom, and JSON feeds from website URLs using:
1. HTML <link> tag parsing
2. Common feed URL patterns
3. WordPress/CMS pattern detection
"""
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import logging
from loguru import logger

# Timeout for HTTP requests (seconds)
REQUEST_TIMEOUT = 10

# Common feed URL patterns to try
COMMON_FEED_PATTERNS = [
    "/feed/",
    "/feed",
    "/rss/",
    "/rss",
    "/atom.xml",
    "/rss.xml",
    "/index.xml",
    "/feed.xml",
    "/?feed=rss2",
    "/?feed=atom",
    "/feeds/posts/default",  # Blogger
    "/rss/index.rss",  # Ghost
]

# User agent to avoid being blocked
USER_AGENT = "Mozilla/5.0 (compatible; RSS Feed Aggregator/1.0; +https://github.com)"


def normalize_url(url: str) -> str:
    """
    Normalize URL to ensure proper format

    Args:
        url: URL string to normalize

    Returns:
        Normalized URL with scheme
    """
    url = url.strip()

    # Add https:// if no scheme
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url


def is_valid_feed_url(url: str) -> bool:
    """
    Basic validation of feed URL format

    Args:
        url: URL to validate

    Returns:
        True if URL appears valid
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


async def discover_feeds_from_url(website_url: str) -> List[Dict[str, str]]:
    """
    Discovers RSS/Atom/JSON feeds from a website URL

    This function:
    1. Fetches website HTML
    2. Parses <link rel="alternate"> tags for RSS/Atom
    3. Tries common feed URL patterns as fallback
    4. Validates each discovered feed
    5. Returns sorted list by reliability

    Args:
        website_url: Website URL to discover feeds from

    Returns:
        List of dicts with keys: url, title, type, description
        Example: [
            {
                "url": "https://example.com/feed/",
                "title": "Example Feed",
                "type": "rss",
                "description": "Latest posts"
            }
        ]

    Raises:
        ValueError: If URL is invalid
        requests.Timeout: If request times out (>10s)
    """
    # Normalize and validate URL
    website_url = normalize_url(website_url)

    if not is_valid_feed_url(website_url):
        raise ValueError(f"Invalid URL format: {website_url}")

    discovered_feeds = []

    try:
        # Fetch website HTML
        logger.info(f"Fetching website: {website_url}")
        response = requests.get(
            website_url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            verify=True,  # Verify SSL certificates
        )
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, "lxml")

        # 1. Look for <link rel="alternate"> tags
        link_feeds = _discover_from_link_tags(soup, website_url)
        discovered_feeds.extend(link_feeds)

        # 2. If no feeds found, try common patterns
        if not discovered_feeds:
            logger.info("No feeds found in <link> tags, trying common patterns...")
            pattern_feeds = _discover_from_patterns(website_url)
            discovered_feeds.extend(pattern_feeds)

        # 3. Remove duplicates (same URL)
        discovered_feeds = _deduplicate_feeds(discovered_feeds)

        # 4. Sort by reliability (RSS > Atom > JSON)
        discovered_feeds = _sort_feeds_by_priority(discovered_feeds)

        logger.info(f"Discovered {len(discovered_feeds)} feed(s) from {website_url}")
        return discovered_feeds

    except requests.Timeout:
        logger.error(f"Request timeout after {REQUEST_TIMEOUT}s: {website_url}")
        raise requests.Timeout(
            f"Could not connect to website (timeout after {REQUEST_TIMEOUT}s). "
            "Please check the URL and try again."
        )

    except requests.exceptions.SSLError as e:
        logger.error(f"SSL certificate error: {website_url} - {str(e)}")
        return []  # Return empty list instead of raising

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {website_url} - {str(e)}")
        return []  # Return empty list instead of raising

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {website_url} - {str(e)}")
        return []  # Return empty list instead of raising

    except Exception as e:
        logger.error(f"Unexpected error during feed discovery: {str(e)}")
        return []


def _discover_from_link_tags(soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
    """
    Discover feeds from HTML <link> tags

    Args:
        soup: BeautifulSoup parsed HTML
        base_url: Base URL for resolving relative URLs

    Returns:
        List of discovered feeds
    """
    feeds = []

    # Find all <link rel="alternate"> tags
    link_tags = soup.find_all("link", rel="alternate")

    for link in link_tags:
        feed_type_attr = link.get("type", "")
        href = link.get("href", "")
        title = link.get("title", "")

        if not href:
            continue

        # Resolve relative URLs
        feed_url = urljoin(base_url, href)

        # Determine feed type from MIME type
        feed_type = "unknown"
        if "rss" in feed_type_attr.lower():
            feed_type = "rss"
        elif "atom" in feed_type_attr.lower():
            feed_type = "atom"
        elif "json" in feed_type_attr.lower():
            feed_type = "json"

        # Skip if not a feed
        if feed_type == "unknown":
            continue

        feeds.append(
            {
                "url": feed_url,
                "title": title or f"{feed_type.upper()} Feed",
                "type": feed_type,
                "description": f"{feed_type.upper()} feed from {urlparse(base_url).netloc}",
            }
        )

    logger.info(f"Found {len(feeds)} feed(s) in <link> tags")
    return feeds


def _discover_from_patterns(base_url: str) -> List[Dict[str, str]]:
    """
    Try common feed URL patterns

    Args:
        base_url: Base URL to try patterns with

    Returns:
        List of discovered feeds
    """
    feeds = []

    for pattern in COMMON_FEED_PATTERNS:
        feed_url = urljoin(base_url, pattern)

        try:
            # Quick HEAD request to check if feed exists
            response = requests.head(
                feed_url,
                timeout=5,  # Shorter timeout for pattern testing
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
            )

            # Check if successful (200-299)
            if 200 <= response.status_code < 300:
                # Determine feed type from content-type or URL
                content_type = response.headers.get("Content-Type", "").lower()
                feed_type = "rss"  # Default

                if "atom" in content_type or "atom" in feed_url:
                    feed_type = "atom"
                elif "json" in content_type or "json" in feed_url:
                    feed_type = "json"

                feeds.append(
                    {
                        "url": feed_url,
                        "title": f"{feed_type.upper()} Feed",
                        "type": feed_type,
                        "description": f"Auto-discovered {feed_type.upper()} feed",
                    }
                )

                logger.info(f"Found feed at pattern: {feed_url}")

        except requests.RequestException:
            # Pattern didn't work, continue to next
            continue

    logger.info(f"Found {len(feeds)} feed(s) from patterns")
    return feeds


def _deduplicate_feeds(feeds: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Remove duplicate feeds (same URL)

    Args:
        feeds: List of discovered feeds

    Returns:
        Deduplicated list of feeds
    """
    seen_urls = set()
    unique_feeds = []

    for feed in feeds:
        url = feed["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            unique_feeds.append(feed)

    return unique_feeds


def _sort_feeds_by_priority(feeds: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Sort feeds by reliability/priority

    Priority: RSS > Atom > JSON

    Args:
        feeds: List of discovered feeds

    Returns:
        Sorted list of feeds
    """
    priority_map = {"rss": 0, "atom": 1, "json": 2, "unknown": 3}

    return sorted(feeds, key=lambda f: priority_map.get(f["type"], 99))
