"""
Scraper for Ozgur Kocaeli news site
"""
from typing import List, Dict, Optional
import logging
import re
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class OzgurKocaeliScraper(BaseScraper):
    """Scraper for ozgurkocaeli.com.tr"""

    def __init__(self):
        super().__init__(
            source_name="Ozgur Kocaeli",
            base_url="https://www.ozgurkocaeli.com.tr"
        )

    def scrape(self, days: int = 3) -> List[Dict]:
        """Scrape news articles from Ozgur Kocaeli"""
        articles = []

        try:
            logger.info(f"[SCRAPING] {self.source_name}...")
            soup = self.get_page(self.base_url)

            if not soup:
                return articles

            for article_url in self.extract_candidate_urls(soup, max_links=80):
                # Ozgur Kocaeli article URLs follow /haber/{numeric-id}/slug pattern
                # Skip category pages like /kocaeli-ekonomi-haberleri
                if not re.search(r'/haber/\d+/', article_url):
                    continue

                # Parse individual article
                article_data = self.parse_article(article_url)

                if article_data and self.is_within_date_range(article_data.get('publish_date'), days):
                    article_data['url'] = article_url
                    articles.append(article_data)
                    logger.info(f"[SUCCESS] Scraped: {article_data['title'][:50]}...")

                    # Limit to avoid too many requests
                    if len(articles) >= 30:
                        break

            logger.info(f"[COMPLETE] Found {len(articles)} articles from {self.source_name}")

        except Exception as e:
            logger.error(f"[ERROR] Scraper {self.source_name} failed: {e}")

        return articles

    def parse_article(self, article_url: str) -> Optional[Dict]:
        """Parse a single article from Ozgur Kocaeli"""
        try:
            soup = self.get_page(article_url)
            if not soup:
                return None

            title = self.extract_title(soup)

            if not title:
                return None

            content = self.extract_content(soup)

            if not content or len(content) < 100:
                return None

            # Extract publish date
            publish_date = self.extract_date(soup)

            if not publish_date:
                return None

            return {
                'title': title,
                'content': content,
                'publish_date': publish_date
            }

        except Exception as e:
            logger.error(f"[ERROR] Failed to parse article {article_url}: {e}")
            return None

