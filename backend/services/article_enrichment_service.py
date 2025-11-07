"""
Article Enrichment and Preprocessing Service (Tasks 2.8 + 2.13)

This service provides intelligent content processing for articles to improve
the iOS app user experience. It combines content enrichment (Task 2.8) and
article preprocessing (Task 2.13).

Features:
- Full-text extraction using readability algorithm
- Article image extraction from OpenGraph tags and content
- Automatic category classification using keywords and patterns
- Content quality scoring based on multiple factors
- Extractive summarization for coherent summaries
- Metadata extraction (author, publish date, reading time, topics)
- Content cleaning and sanitization
- Summary caching to reduce AI calls

Architecture:
- Modular design with separate functions for each enrichment task
- Async/await for non-blocking operations
- Caching layer for expensive operations
- Error handling and fallback mechanisms
- Configurable quality thresholds

Usage:
    from services.article_enrichment_service import ArticleEnrichmentService

    service = ArticleEnrichmentService()

    # Enrich a single article
    enriched = await service.enrich_article(article_url, article_html)

    # Process article from feed entry
    enriched = await service.process_feed_article(feed_entry)
"""
import asyncio
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse, urljoin
from collections import Counter
import json

import requests
from bs4 import BeautifulSoup
from loguru import logger
from readability import Document
import hashlib

# ============================================================================
# CONFIGURATION
# ============================================================================

# Content extraction settings
MAX_CONTENT_LENGTH = 5000  # Maximum characters for AI processing
MIN_CONTENT_LENGTH = 100   # Minimum characters for valid article
MIN_PARAGRAPH_LENGTH = 50  # Minimum length for a paragraph to be considered

# Image extraction settings
MIN_IMAGE_WIDTH = 400      # Minimum width for featured image
MIN_IMAGE_HEIGHT = 300     # Minimum height for featured image
IMAGE_TIMEOUT = 5          # Timeout for image validation requests

# Summarization settings
SUMMARY_SENTENCE_COUNT = 3 # Number of sentences in summary
MAX_SUMMARY_LENGTH = 300   # Maximum characters for summary

# Quality scoring thresholds
MIN_QUALITY_SCORE = 30     # Minimum score to keep article (0-100)
EXCELLENT_QUALITY = 80     # Score threshold for excellent articles

# Category keywords (expandable)
CATEGORY_KEYWORDS = {
    "technology": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning",
                   "neural network", "tech", "software", "hardware", "computer", "programming",
                   "code", "developer", "data science", "algorithm", "robotics", "automation"],
    "business": ["business", "startup", "entrepreneur", "investment", "finance", "economy",
                 "market", "stock", "company", "revenue", "profit", "funding", "vc", "venture capital"],
    "science": ["research", "study", "science", "scientific", "experiment", "discovery",
                "physics", "biology", "chemistry", "medicine", "health", "clinical"],
    "news": ["breaking", "news", "report", "announced", "government", "policy", "election",
             "politics", "political", "world", "global", "international"],
    "tutorial": ["tutorial", "guide", "how to", "learn", "beginner", "introduction",
                 "course", "lesson", "step by step", "walkthrough"],
    "opinion": ["opinion", "editorial", "commentary", "perspective", "analysis", "think",
                "believe", "argue", "debate", "criticism"],
    "product": ["product", "launch", "release", "review", "features", "specs",
                "announcement", "unveil", "introduce", "new version"],
}

# Request settings
REQUEST_TIMEOUT = 10       # Timeout for HTTP requests
USER_AGENT = "Mozilla/5.0 (compatible; ArticleEnrichmentBot/1.0)"


# ============================================================================
# ARTICLE ENRICHMENT SERVICE
# ============================================================================

class ArticleEnrichmentService:
    """
    Service for enriching articles with full content, images, categories, etc.

    Combines content enrichment (Task 2.8) and preprocessing (Task 2.13)
    to provide comprehensive article enhancement for the iOS app.
    """

    def __init__(self):
        """Initialize the enrichment service"""
        self.summary_cache = {}  # Simple in-memory cache for summaries
        self.stats = {
            "articles_enriched": 0,
            "images_extracted": 0,
            "categories_assigned": 0,
            "summaries_generated": 0,
            "quality_failures": 0,
        }

    # ========================================================================
    # MAIN ENRICHMENT FUNCTIONS
    # ========================================================================

    async def enrich_article(
        self,
        url: str,
        existing_content: Optional[str] = None,
        existing_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enrich an article with full content, images, metadata, etc.

        This is the main entry point for article enrichment. It performs:
        - Full-text extraction
        - Image extraction
        - Category classification
        - Content quality scoring
        - Summarization
        - Metadata extraction

        Args:
            url: Article URL
            existing_content: Existing article content (optional, will fetch if not provided)
            existing_data: Existing article data to merge with

        Returns:
            Dictionary with enriched article data
        """
        logger.info(f"Enriching article: {url}")

        try:
            # Fetch article HTML if not provided
            if existing_content is None:
                html_content = await self._fetch_article_html(url)
            else:
                html_content = existing_content

            if not html_content:
                logger.warning(f"Failed to fetch article content: {url}")
                return existing_data or {}

            # Parse HTML
            soup = BeautifulSoup(html_content, 'lxml')

            # Extract full text using readability
            full_text, cleaned_html = self._extract_full_text(html_content, url)

            # Extract images
            featured_image = self._extract_featured_image(soup, url)

            # Classify category
            category = self._classify_category(full_text, existing_data)

            # Extract metadata
            metadata = self._extract_metadata(soup, full_text, url)

            # Calculate quality score
            quality_score = self._calculate_quality_score(
                full_text=full_text,
                has_image=bool(featured_image),
                metadata=metadata
            )

            # Generate summary (only if quality is sufficient)
            summary = None
            if quality_score >= MIN_QUALITY_SCORE:
                summary = self._generate_summary(full_text, url)

            # Prepare limited content for AI processing
            content_for_ai = self._prepare_content_for_ai(full_text)

            # Compile enriched data
            enriched_data = {
                "url": url,
                "full_text": full_text[:10000] if full_text else None,  # Store up to 10k chars
                "content_for_ai": content_for_ai,
                "cleaned_html": cleaned_html[:5000] if cleaned_html else None,
                "featured_image": featured_image,
                "category": category,
                "auto_summary": summary,
                "quality_score": quality_score,
                **metadata,  # author, publish_date, reading_time, topics
            }

            # Merge with existing data
            if existing_data:
                # Don't overwrite existing values with None
                for key, value in enriched_data.items():
                    if value is not None:
                        existing_data[key] = value
                enriched_data = existing_data

            # Update stats
            self.stats["articles_enriched"] += 1
            if featured_image:
                self.stats["images_extracted"] += 1
            if category:
                self.stats["categories_assigned"] += 1
            if summary:
                self.stats["summaries_generated"] += 1

            if quality_score < MIN_QUALITY_SCORE:
                self.stats["quality_failures"] += 1
                logger.info(f"Article quality below threshold: {quality_score}/100")

            logger.info(f"Article enriched successfully - Quality: {quality_score}/100")
            return enriched_data

        except Exception as e:
            logger.error(f"Error enriching article {url}: {e}")
            return existing_data or {}

    async def process_feed_article(
        self,
        entry: Dict[str, Any],
        source: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Process and enrich an article from a feed entry

        This is a convenience function for processing feed entries directly.
        It extracts basic data from the entry and enriches it.

        Args:
            entry: Feed entry dictionary (from feedparser)
            source: Feed source name
            user_id: User ID who owns the feed

        Returns:
            Enriched article data dictionary
        """
        # Extract basic data from feed entry
        link = entry.get("link", "")
        title = entry.get("title", "Untitled")

        # Get existing content from entry
        existing_content = None
        if entry.get("content"):
            existing_content = entry["content"][0].get("value", "")
        elif entry.get("description"):
            existing_content = entry.get("description", "")

        # Build basic article data
        article_data = {
            "title": title[:500] if title else "Untitled",
            "link": link[:1000] if link else "",
            "source": source,
            "user_id": user_id,
        }

        # Enrich the article
        enriched = await self.enrich_article(
            url=link,
            existing_content=existing_content,
            existing_data=article_data
        )

        return enriched

    # ========================================================================
    # FULL-TEXT EXTRACTION (Task 2.8)
    # ========================================================================

    async def _fetch_article_html(self, url: str) -> Optional[str]:
        """
        Fetch article HTML from URL

        Args:
            url: Article URL

        Returns:
            HTML content or None if fetch fails
        """
        try:
            response = requests.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.warning(f"Failed to fetch article HTML: {e}")
            return None

    def _extract_full_text(self, html: str, url: str) -> Tuple[str, str]:
        """
        Extract main content from article HTML using readability algorithm

        This strips ads, navigation, and other non-content elements.

        Args:
            html: Raw HTML content
            url: Article URL (for context)

        Returns:
            Tuple of (plain_text, cleaned_html)
        """
        try:
            # Use readability to extract main content
            doc = Document(html)

            # Get cleaned HTML
            cleaned_html = doc.summary()

            # Parse cleaned HTML to extract text
            soup = BeautifulSoup(cleaned_html, 'lxml')

            # Remove script and style elements
            for script in soup(["script", "style", "noscript"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            return text, cleaned_html

        except Exception as e:
            logger.warning(f"Error extracting full text: {e}")
            # Fallback: just extract text from HTML
            soup = BeautifulSoup(html, 'lxml')
            return soup.get_text()[:MAX_CONTENT_LENGTH], ""

    # ========================================================================
    # IMAGE EXTRACTION (Task 2.8)
    # ========================================================================

    def _extract_featured_image(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """
        Extract featured image from article

        Tries multiple strategies:
        1. OpenGraph image (og:image)
        2. Twitter card image
        3. Article schema.org image
        4. First large image in content

        Args:
            soup: BeautifulSoup object of article HTML
            base_url: Base URL for resolving relative URLs

        Returns:
            Image URL or None
        """
        try:
            # Strategy 1: OpenGraph image
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                image_url = og_image["content"]
                if self._is_valid_image_url(image_url):
                    return self._resolve_url(image_url, base_url)

            # Strategy 2: Twitter card image
            twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
            if twitter_image and twitter_image.get("content"):
                image_url = twitter_image["content"]
                if self._is_valid_image_url(image_url):
                    return self._resolve_url(image_url, base_url)

            # Strategy 3: Schema.org image
            schema_image = soup.find("meta", attrs={"itemprop": "image"})
            if schema_image and schema_image.get("content"):
                image_url = schema_image["content"]
                if self._is_valid_image_url(image_url):
                    return self._resolve_url(image_url, base_url)

            # Strategy 4: First large image in content
            # Look for images in article body (common containers)
            article_containers = soup.find_all(["article", "main", "div"], class_=re.compile(r"(article|content|post|entry)", re.I))

            for container in article_containers:
                images = container.find_all("img")
                for img in images:
                    img_url = img.get("src") or img.get("data-src")
                    if img_url and self._is_valid_image_url(img_url):
                        # Check if image is likely large enough
                        width = img.get("width")
                        height = img.get("height")

                        # If dimensions are specified, check them
                        if width and height:
                            try:
                                if int(width) >= MIN_IMAGE_WIDTH and int(height) >= MIN_IMAGE_HEIGHT:
                                    return self._resolve_url(img_url, base_url)
                            except ValueError:
                                pass
                        else:
                            # If no dimensions, assume it might be good
                            return self._resolve_url(img_url, base_url)

            # If still no image, try any image in the page
            all_images = soup.find_all("img")
            for img in all_images[:10]:  # Check first 10 images
                img_url = img.get("src") or img.get("data-src")
                if img_url and self._is_valid_image_url(img_url):
                    return self._resolve_url(img_url, base_url)

            return None

        except Exception as e:
            logger.warning(f"Error extracting featured image: {e}")
            return None

    def _is_valid_image_url(self, url: str) -> bool:
        """
        Check if URL is a valid image URL

        Args:
            url: URL to check

        Returns:
            True if valid image URL
        """
        if not url:
            return False

        # Check for common image extensions
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')
        url_lower = url.lower()

        # Check extension
        if any(url_lower.endswith(ext) for ext in image_extensions):
            return True

        # Check for image-related patterns in URL
        if any(pattern in url_lower for pattern in ['image', 'img', 'photo', 'picture']):
            return True

        return False

    def _resolve_url(self, url: str, base_url: str) -> str:
        """
        Resolve relative URL to absolute URL

        Args:
            url: URL to resolve (may be relative)
            base_url: Base URL

        Returns:
            Absolute URL
        """
        if url.startswith(('http://', 'https://')):
            return url
        return urljoin(base_url, url)

    # ========================================================================
    # CATEGORY CLASSIFICATION (Task 2.8)
    # ========================================================================

    def _classify_category(
        self,
        content: str,
        existing_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Automatically classify article category using keywords

        Uses keyword matching with weighted scoring. Can be extended
        with ML models for better accuracy.

        Args:
            content: Article content
            existing_data: Existing article data (may contain tags/category)

        Returns:
            Category name or None
        """
        try:
            # If existing data has a category, keep it
            if existing_data and existing_data.get("category"):
                return existing_data["category"]

            # If existing data has tags, try to match category from tags
            if existing_data and existing_data.get("tags"):
                tags = existing_data["tags"]
                if isinstance(tags, list) and tags:
                    first_tag = tags[0].lower()
                    for category_name in CATEGORY_KEYWORDS.keys():
                        if category_name in first_tag or first_tag in category_name:
                            return category_name

            # Classify based on content
            content_lower = content.lower()

            # Count keyword matches for each category
            category_scores = {}
            for category, keywords in CATEGORY_KEYWORDS.items():
                score = 0
                for keyword in keywords:
                    # Use word boundaries for more accurate matching
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    matches = len(re.findall(pattern, content_lower))
                    score += matches

                if score > 0:
                    category_scores[category] = score

            # Return category with highest score
            if category_scores:
                best_category = max(category_scores, key=category_scores.get)
                if category_scores[best_category] >= 2:  # At least 2 keyword matches
                    return best_category

            # Default category if no matches
            return "general"

        except Exception as e:
            logger.warning(f"Error classifying category: {e}")
            return None

    # ========================================================================
    # CONTENT QUALITY SCORING (Task 2.13)
    # ========================================================================

    def _calculate_quality_score(
        self,
        full_text: str,
        has_image: bool,
        metadata: Dict[str, Any]
    ) -> int:
        """
        Calculate content quality score (0-100)

        Scoring factors:
        - Content length (30 points)
        - Readability (20 points)
        - Has image (15 points)
        - Has author (10 points)
        - Has publish date (10 points)
        - Has topics/entities (15 points)

        Args:
            full_text: Article full text
            has_image: Whether article has an image
            metadata: Article metadata dictionary

        Returns:
            Quality score (0-100)
        """
        score = 0

        # Content length score (30 points)
        if full_text:
            text_length = len(full_text)
            if text_length >= 2000:
                score += 30
            elif text_length >= 1000:
                score += 25
            elif text_length >= 500:
                score += 20
            elif text_length >= MIN_CONTENT_LENGTH:
                score += 10

        # Readability score (20 points)
        # Simple readability check: average sentence length and word length
        if full_text:
            sentences = re.split(r'[.!?]+', full_text)
            sentences = [s.strip() for s in sentences if s.strip()]

            if sentences:
                words = full_text.split()
                avg_sentence_length = len(words) / len(sentences)
                avg_word_length = sum(len(word) for word in words) / len(words) if words else 0

                # Ideal: 15-20 words per sentence, 4-6 chars per word
                if 10 <= avg_sentence_length <= 25 and 3 <= avg_word_length <= 7:
                    score += 20
                elif 5 <= avg_sentence_length <= 35:
                    score += 15
                else:
                    score += 5

        # Has image (15 points)
        if has_image:
            score += 15

        # Has author (10 points)
        if metadata.get("author"):
            score += 10

        # Has publish date (10 points)
        if metadata.get("publish_date"):
            score += 10

        # Has topics/entities (15 points)
        topics = metadata.get("topics", [])
        if topics and len(topics) >= 3:
            score += 15
        elif topics and len(topics) >= 1:
            score += 10

        return min(score, 100)  # Cap at 100

    # ========================================================================
    # SUMMARIZATION (Task 2.13)
    # ========================================================================

    def _generate_summary(self, content: str, url: str) -> Optional[str]:
        """
        Generate extractive summary of article content

        Uses a simple but effective extractive summarization algorithm:
        1. Score sentences based on important keywords
        2. Select top N sentences
        3. Return in original order

        This approach is fast and doesn't require AI API calls.
        Summaries are cached to improve performance.

        Args:
            content: Article full text
            url: Article URL (for cache key)

        Returns:
            Summary text (2-3 sentences) or None
        """
        # Check cache first
        cache_key = hashlib.md5(url.encode()).hexdigest()
        if cache_key in self.summary_cache:
            return self.summary_cache[cache_key]

        try:
            if not content:
                return None

            # For short content, return as-is instead of None
            if len(content) < MIN_CONTENT_LENGTH:
                summary = content.strip()
                self.summary_cache[cache_key] = summary
                return summary

            # Split into sentences
            sentences = re.split(r'(?<=[.!?])\s+', content)
            sentences = [s.strip() for s in sentences if len(s.strip()) >= MIN_PARAGRAPH_LENGTH]

            if len(sentences) <= SUMMARY_SENTENCE_COUNT:
                summary = ' '.join(sentences)
                self.summary_cache[cache_key] = summary
                return summary

            # Score sentences based on important keywords
            # Extract important words (nouns, verbs, adjectives)
            words = re.findall(r'\b[a-z]{4,}\b', content.lower())
            word_freq = Counter(words)

            # Get top keywords (excluding common words)
            common_words = {'that', 'this', 'with', 'from', 'have', 'been', 'will', 'would',
                          'could', 'should', 'there', 'their', 'which', 'about', 'when', 'where'}
            important_words = {word: count for word, count in word_freq.most_common(50)
                             if word not in common_words}

            # Score each sentence
            sentence_scores = []
            for i, sentence in enumerate(sentences):
                score = 0
                sentence_lower = sentence.lower()

                # Score based on important word presence
                for word, freq in important_words.items():
                    if word in sentence_lower:
                        score += freq

                # Bonus for position (first sentences are often important)
                if i < 3:
                    score += 10

                # Bonus for sentence length (not too short, not too long)
                word_count = len(sentence.split())
                if 10 <= word_count <= 30:
                    score += 5

                sentence_scores.append((sentence, score, i))

            # Sort by score and get top N sentences
            sentence_scores.sort(key=lambda x: x[1], reverse=True)
            top_sentences = sentence_scores[:SUMMARY_SENTENCE_COUNT]

            # Sort by original position to maintain flow
            top_sentences.sort(key=lambda x: x[2])

            # Build summary
            summary = ' '.join(s[0] for s in top_sentences)

            # Truncate if too long
            if len(summary) > MAX_SUMMARY_LENGTH:
                summary = summary[:MAX_SUMMARY_LENGTH].rsplit(' ', 1)[0] + '...'

            # Cache summary
            self.summary_cache[cache_key] = summary

            return summary

        except Exception as e:
            logger.warning(f"Error generating summary: {e}")
            return None

    # ========================================================================
    # METADATA EXTRACTION (Task 2.13)
    # ========================================================================

    def _extract_metadata(
        self,
        soup: BeautifulSoup,
        content: str,
        url: str
    ) -> Dict[str, Any]:
        """
        Extract article metadata

        Extracts:
        - Author name
        - Publication date
        - Reading time estimate
        - Key topics/entities

        Args:
            soup: BeautifulSoup object of article HTML
            content: Article full text
            url: Article URL

        Returns:
            Dictionary with metadata fields
        """
        metadata = {
            "author": None,
            "publish_date": None,
            "reading_time": None,
            "topics": [],
        }

        try:
            # Extract author
            author = self._extract_author(soup)
            if author:
                metadata["author"] = author

            # Extract publish date
            publish_date = self._extract_publish_date(soup)
            if publish_date:
                metadata["publish_date"] = publish_date

            # Calculate reading time
            if content:
                reading_time = self._calculate_reading_time(content)
                metadata["reading_time"] = reading_time

            # Extract topics/entities
            topics = self._extract_topics(content)
            if topics:
                metadata["topics"] = topics

        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")

        return metadata

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author name from article"""
        # Try multiple strategies

        # OpenGraph author
        og_author = soup.find("meta", property="og:article:author")
        if og_author and og_author.get("content"):
            return og_author["content"].strip()

        # Author meta tag
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta and author_meta.get("content"):
            return author_meta["content"].strip()

        # Schema.org author
        author_schema = soup.find("meta", attrs={"itemprop": "author"})
        if author_schema and author_schema.get("content"):
            return author_schema["content"].strip()

        # Author in structured data
        author_span = soup.find(["span", "a", "div"], class_=re.compile(r"author", re.I))
        if author_span:
            return author_span.get_text().strip()

        return None

    def _extract_publish_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date from article"""
        # Try multiple strategies

        # OpenGraph published_time
        og_date = soup.find("meta", property="og:article:published_time")
        if og_date and og_date.get("content"):
            return og_date["content"]

        # Date meta tag
        date_meta = soup.find("meta", attrs={"name": "publishdate"})
        if date_meta and date_meta.get("content"):
            return date_meta["content"]

        # Schema.org datePublished
        date_schema = soup.find("meta", attrs={"itemprop": "datePublished"})
        if date_schema and date_schema.get("content"):
            return date_schema["content"]

        # Time element
        time_elem = soup.find("time")
        if time_elem and time_elem.get("datetime"):
            return time_elem["datetime"]

        return None

    def _calculate_reading_time(self, content: str) -> int:
        """
        Calculate estimated reading time in minutes

        Assumes average reading speed of 200 words per minute

        Args:
            content: Article content

        Returns:
            Reading time in minutes
        """
        words = content.split()
        word_count = len(words)
        reading_time = max(1, round(word_count / 200))  # At least 1 minute
        return reading_time

    def _extract_topics(self, content: str) -> List[str]:
        """
        Extract key topics/entities from content

        Uses simple frequency analysis of meaningful words.
        Can be enhanced with NER (Named Entity Recognition) models.

        Args:
            content: Article content

        Returns:
            List of topic keywords
        """
        try:
            if not content:
                return []

            # First try to extract capitalized words (likely proper nouns/important terms)
            capitalized_words = re.findall(r'\b[A-Z][a-z]{3,}\b', content)

            # Filter out common words
            common_words = {'The', 'This', 'That', 'With', 'From', 'Have', 'Been',
                          'Will', 'Would', 'Could', 'Should', 'There', 'Their',
                          'When', 'What', 'Where', 'Which', 'While'}

            if capitalized_words:
                # Count frequency of capitalized words
                word_freq = Counter(capitalized_words)

                # Get top topics (words that appear at least once)
                topics = [word for word, count in word_freq.most_common(10)
                         if word not in common_words]

                if topics:
                    return topics[:5]  # Return top 5

            # Fallback: extract all meaningful words (4+ characters)
            all_words = re.findall(r'\b[a-z]{4,}\b', content.lower())

            if all_words:
                word_freq = Counter(all_words)

                # Common lowercase words to exclude
                common_lowercase = {'that', 'this', 'with', 'from', 'have', 'been',
                                  'will', 'would', 'could', 'should', 'there', 'their',
                                  'when', 'what', 'where', 'which', 'while', 'about',
                                  'more', 'than', 'some', 'into', 'over', 'after',
                                  'make', 'made', 'most', 'many', 'much', 'them',
                                  'such', 'only', 'also', 'well', 'very', 'even'}

                # Get top topics that appear multiple times
                topics = [word for word, count in word_freq.most_common(15)
                         if word not in common_lowercase and count >= 2]

                return topics[:5]  # Return top 5

            return []

        except Exception as e:
            logger.warning(f"Error extracting topics: {e}")
            return []

    # ========================================================================
    # CONTENT PREPROCESSING (Task 2.13)
    # ========================================================================

    def _prepare_content_for_ai(self, content: str) -> str:
        """
        Prepare article content for AI processing

        Limits content to MAX_CONTENT_LENGTH characters while preserving
        paragraph structure and important content.

        Args:
            content: Full article content

        Returns:
            Truncated content suitable for AI processing
        """
        if not content:
            return ""

        if len(content) <= MAX_CONTENT_LENGTH:
            return content

        # Split into paragraphs
        paragraphs = content.split('\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        # Take paragraphs until we reach the limit
        result = []
        current_length = 0

        for para in paragraphs:
            para_with_newline = len(para) + 1  # Account for newline in joined result

            if current_length + para_with_newline <= MAX_CONTENT_LENGTH:
                result.append(para)
                current_length += para_with_newline
            else:
                # Add partial paragraph if there's room
                remaining = MAX_CONTENT_LENGTH - current_length
                if remaining > 100:  # Only if we can add a meaningful chunk
                    # Subtract 3 for '...' and ensure we don't exceed limit
                    truncate_at = min(len(para), remaining - 3)
                    result.append(para[:truncate_at] + '...')
                break

        final_result = '\n'.join(result)

        # Final safety check - truncate if still over limit
        if len(final_result) > MAX_CONTENT_LENGTH:
            final_result = final_result[:MAX_CONTENT_LENGTH]

        return final_result

    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get enrichment service statistics"""
        return {
            **self.stats,
            "cache_size": len(self.summary_cache),
        }

    def clear_cache(self):
        """Clear summary cache"""
        self.summary_cache.clear()
        logger.info("Summary cache cleared")


# ============================================================================
# STANDALONE FUNCTIONS
# ============================================================================

async def enrich_article_by_url(url: str) -> Dict[str, Any]:
    """
    Enrich a single article by URL

    Convenience function for one-off article enrichment.

    Args:
        url: Article URL

    Returns:
        Enriched article data
    """
    service = ArticleEnrichmentService()
    return await service.enrich_article(url)


async def enrich_existing_articles(user_id: int, limit: int = 100):
    """
    Enrich existing articles in database

    This can be run as a background job to enrich articles that were
    added before the enrichment service was implemented.

    Args:
        user_id: User ID
        limit: Maximum number of articles to process
    """
    from database import get_db
    from sqlalchemy import text

    service = ArticleEnrichmentService()
    db = next(get_db())

    try:
        # Get articles without enrichment data
        result = db.execute(
            text("""
                SELECT id, link, content
                FROM articles
                WHERE user_id = :user_id
                AND (full_text IS NULL OR featured_image IS NULL)
                LIMIT :limit
            """),
            {"user_id": user_id, "limit": limit}
        )

        articles = result.fetchall()
        logger.info(f"Found {len(articles)} articles to enrich for user {user_id}")

        enriched_count = 0
        for article in articles:
            try:
                # Enrich article
                enriched = await service.enrich_article(
                    url=article.link,
                    existing_content=article.content
                )

                # Update database (basic update, extend as needed)
                if enriched:
                    db.execute(
                        text("""
                            UPDATE articles
                            SET
                                content = COALESCE(:content, content),
                                category = COALESCE(:category, category)
                            WHERE id = :article_id
                        """),
                        {
                            "article_id": article.id,
                            "content": enriched.get("content_for_ai"),
                            "category": enriched.get("category"),
                        }
                    )
                    enriched_count += 1

            except Exception as e:
                logger.error(f"Error enriching article {article.id}: {e}")
                continue

        db.commit()
        logger.info(f"Successfully enriched {enriched_count} articles")

        return service.get_stats()

    finally:
        db.close()
