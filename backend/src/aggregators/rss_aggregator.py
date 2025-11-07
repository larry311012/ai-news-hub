import feedparser
from datetime import datetime
from typing import List, Dict
from loguru import logger
from src.utils import retry_with_backoff


class RSSAggregator:
    """Aggregates news from RSS feeds"""

    def __init__(self, sources: List[Dict]):
        """
        Initialize RSS aggregator with sources

        Args:
            sources: List of RSS feed configurations
        """
        self.sources = sources

    def fetch_all(self) -> List[Dict]:
        """
        Fetch articles from all RSS sources

        Returns:
            List of article dictionaries
        """
        all_articles = []

        for source in self.sources:
            try:
                articles = self._fetch_feed(source)
                all_articles.extend(articles)
                logger.info(f"Fetched {len(articles)} articles from {source['name']}")
            except Exception as e:
                logger.error(f"Error fetching from {source['name']}: {e}")

        return all_articles

    @retry_with_backoff(max_retries=3, initial_delay=1.0, exceptions=(Exception,))
    def _fetch_feed(self, source: Dict) -> List[Dict]:
        """
        Fetch articles from a single RSS feed

        Args:
            source: Feed configuration

        Returns:
            List of parsed articles
        """
        feed = feedparser.parse(source["url"])
        articles = []

        for entry in feed.entries:
            article = {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", ""),
                "published": self._parse_date(entry.get("published", "")),
                "source": source["name"],
                "category": source.get("category", "general"),
                "tags": [tag.term for tag in entry.get("tags", [])],
            }
            articles.append(article)

        return articles

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse RSS date string to datetime"""
        try:
            from email.utils import parsedate_to_datetime

            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"Date parsing failed for '{date_str}': {e}")
            return datetime.now()
