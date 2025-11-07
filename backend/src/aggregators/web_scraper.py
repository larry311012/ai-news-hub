import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
from urllib.parse import urljoin
from loguru import logger
from src.utils import retry_with_backoff


class WebScraper:
    """Scrapes AI news from web sources"""

    def __init__(self, sources: List[Dict]):
        """
        Initialize web scraper with sources

        Args:
            sources: List of web source configurations
        """
        self.sources = sources
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def fetch_all(self) -> List[Dict]:
        """
        Fetch articles from all web sources

        Returns:
            List of article dictionaries
        """
        all_articles = []

        for source in self.sources:
            try:
                articles = self._scrape_source(source)
                all_articles.extend(articles)
                logger.info(f"Scraped {len(articles)} articles from {source['name']}")
            except Exception as e:
                logger.error(f"Error scraping {source['name']}: {e}")

        return all_articles

    @retry_with_backoff(
        max_retries=3, initial_delay=1.0, exceptions=(requests.exceptions.RequestException,)
    )
    def _scrape_source(self, source: Dict) -> List[Dict]:
        """
        Scrape articles from a single web source

        Args:
            source: Web source configuration

        Returns:
            List of parsed articles
        """
        # Validate timeout
        timeout = source.get("timeout", 10)
        if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 60:
            logger.warning(f"Invalid timeout {timeout}, using default 10 seconds")
            timeout = 10

        response = requests.get(source["url"], headers=self.headers, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        articles = []

        # This is a basic implementation - customize per source
        selector = source.get("selector", "article")
        elements = soup.select(selector)

        for element in elements[:20]:  # Limit to 20 items
            title_elem = element.find(["h1", "h2", "h3", "a"])
            link_elem = element.find("a")

            if title_elem and link_elem:
                article = {
                    "title": title_elem.get_text(strip=True),
                    "link": self._normalize_url(link_elem.get("href", ""), source["url"]),
                    "summary": "",
                    "published": datetime.now(),
                    "source": source["name"],
                    "category": source.get("category", "general"),
                    "tags": [],
                }
                articles.append(article)

        return articles

    @staticmethod
    def _normalize_url(url: str, base_url: str) -> str:
        """Convert relative URLs to absolute"""
        return urljoin(base_url, url)
