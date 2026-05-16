"""
Base scraper class for all news sources
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import logging
import hashlib
import re
from urllib.parse import urldefrag
from src.config import DEFAULT_SCRAPE_DAYS

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all news scrapers"""

    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })
        self._selenium_driver = None

    def _init_selenium(self, chrome_version: int = 146) -> None:
        """Lazily initialise an undetected-chromedriver instance."""
        try:
            import undetected_chromedriver as uc
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1280,800')
            self._selenium_driver = uc.Chrome(options=options, version_main=chrome_version)
            logger.info(f"[SELENIUM] Driver initialised (Chrome {chrome_version})")
        except Exception as e:
            logger.error(f"[SELENIUM] Failed to initialise driver: {e}")
            self._selenium_driver = None

    def get_page_selenium(self, url: str, wait_seconds: int = 6) -> Optional[BeautifulSoup]:
        """Fetch a page using Selenium (bypasses JS challenge protection)."""
        import time
        if self._selenium_driver is None:
            self._init_selenium()
        if self._selenium_driver is None:
            return None
        try:
            self._selenium_driver.get(url)
            # Wait until Cloudflare challenge page is resolved
            # (title changes from "Bir dakika lütfen..." to actual page title)
            deadline = time.time() + 30
            while time.time() < deadline:
                time.sleep(2)
                title = self._selenium_driver.title
                if title and 'bir dakika' not in title.lower() and 'just a moment' not in title.lower():
                    break
                logger.info(f"[SELENIUM] Waiting for challenge to resolve: '{title}'")
            html = self._selenium_driver.page_source
            return BeautifulSoup(html, 'lxml')
        except Exception as e:
            logger.error(f"[SELENIUM] Error fetching {url}: {e}")
            return None

    def close_selenium(self) -> None:
        """Quit the Selenium driver if it was used."""
        if self._selenium_driver is not None:
            try:
                self._selenium_driver.quit()
            except Exception:
                pass
            self._selenium_driver = None

    def get_page(self, url: str, timeout: int = 10) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            logger.error(f"❌ Error fetching {url}: {e}")
            return None

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters (keep Turkish chars)
        text = re.sub(r'[^\w\sçğıöşüÇĞİÖŞÜ.,!?:;()\-\'\"]+', '', text)

        # Remove ads and irrelevant sections
        ad_patterns = [
            r'reklam.*?göster',
            r'sitemize abone ol',
            r'haber bülteni',
            r'whatsapp.*?takip',
            r'facebook.*?beğen',
        ]
        for pattern in ad_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text.strip()

    def generate_hash(self, title: str, content: str) -> str:
        """Generate a unique hash for duplicate detection"""
        combined = f"{title.lower().strip()}{content.lower().strip()}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()

    def is_within_date_range(self, publish_date: datetime, days: int = DEFAULT_SCRAPE_DAYS) -> bool:
        """Check if publish date is within the last N days"""
        if not publish_date:
            return False
        cutoff_date = datetime.now() - timedelta(days=days)
        return publish_date >= cutoff_date

    def normalize_url(self, url: str) -> str:
        """Normalize relative URLs to absolute"""
        if url.startswith('http'):
            return url
        elif url.startswith('/'):
            return f"{self.base_url}{url}"
        else:
            return f"{self.base_url}/{url}"

    def extract_candidate_urls(self, soup: BeautifulSoup, max_links: int = 80) -> List[str]:
        """
        Collect likely article URLs from page links and remove duplicates.
        """
        candidates: List[str] = []
        seen: Set[str] = set()

        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            if not href:
                continue

            if href.startswith('#') or href.lower().startswith('javascript:') or href.lower().startswith('mailto:'):
                continue

            # Skip non-web scheme hrefs (whatsapp://, tel:, viber:, tg: etc.)
            if '://' in href and not href.lower().startswith(('http://', 'https://')):
                continue

            article_url = self.normalize_url(href)
            article_url = urldefrag(article_url).url
            if not article_url:
                continue

            lower_url = article_url.lower()

            # Keep only likely article pages and skip common non-article routes.
            if 'haber' not in lower_url and '/20' not in lower_url:
                continue
            if any(token in lower_url for token in ['/video', '/galeri', '/yazarlar', '/etiket/', '/kategori/']):
                continue

            # Stay in the same source domain.
            if self.base_url.replace('https://', '').replace('http://', '') not in lower_url:
                continue

            if article_url in seen:
                continue

            seen.add(article_url)
            candidates.append(article_url)

            if len(candidates) >= max_links:
                break

        return candidates

    def extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title from common selectors."""
        title_elem = soup.find('h1')
        if not title_elem:
            title_elem = soup.find('meta', attrs={'property': 'og:title'})
            if title_elem and title_elem.get('content'):
                return self.clean_text(title_elem['content'])
        if not title_elem:
            title_elem = soup.find('title')

        return self.clean_text(title_elem.get_text()) if title_elem else ""

    def extract_content(self, soup: BeautifulSoup, min_length: int = 100) -> str:
        """
        Extract article body text using common containers and paragraph fallbacks.
        """
        selectors = [
            'article',
            'div.article-content',
            'div.news-content',
            'div.post-content',
            'div.entry-content',
            'div[class*=content]',
            'div[class*=article]',
            'div[class*=haber]'
        ]

        raw_chunks: List[str] = []
        for selector in selectors:
            nodes = soup.select(selector)
            for node in nodes:
                text = node.get_text(separator=' ', strip=True)
                if text:
                    raw_chunks.append(text)

        # Fallback: collect paragraph text if container extraction is weak.
        if not raw_chunks:
            for p in soup.find_all('p'):
                text = p.get_text(separator=' ', strip=True)
                if text and len(text) > 20:
                    raw_chunks.append(text)

        # Deduplicate repeated chunks from nested selectors.
        seen_chunks: Set[str] = set()
        unique_chunks: List[str] = []
        for chunk in raw_chunks:
            if chunk not in seen_chunks:
                seen_chunks.add(chunk)
                unique_chunks.append(chunk)

        content = self.clean_text(' '.join(unique_chunks))
        if len(content) < min_length:
            return ""
        return content

    def extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract publish date from common HTML patterns."""
        try:
            meta_keys = [
                ('property', 'article:published_time'),
                ('name', 'publish_date'),
                ('name', 'pubdate'),
                ('name', 'date')
            ]

            for attr_key, attr_val in meta_keys:
                date_meta = soup.find('meta', {attr_key: attr_val})
                if date_meta and date_meta.get('content'):
                    parsed = self.parse_turkish_date(date_meta['content'])
                    if parsed:
                        return parsed

            time_elem = soup.find('time')
            if time_elem:
                if time_elem.get('datetime'):
                    parsed = self.parse_turkish_date(time_elem['datetime'])
                    if parsed:
                        return parsed
                time_text = time_elem.get_text(' ', strip=True)
                parsed = self.parse_turkish_date(time_text)
                if parsed:
                    return parsed

            text_content = soup.get_text(' ', strip=True)
            date_patterns = [
                r'(\d{4}-\d{1,2}-\d{1,2}(?:[T\s]\d{1,2}:\d{2}(?::\d{2})?(?:Z|[+\-]\d{2}:?\d{2})?)?)',
                r'(\d{1,2}\.\d{1,2}\.\d{4})',
                r'(\d{1,2}\s+(?:Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|Haziran|Temmuz|Ağustos|Agustos|Eylül|Eylul|Ekim|Kasım|Kasim|Aralık|Aralik)\s+\d{4})'
            ]

            for pattern in date_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    parsed = self.parse_turkish_date(match.group(1))
                    if parsed:
                        return parsed

        except Exception as e:
            logger.error(f"Error extracting date: {e}")

        return None

    def parse_turkish_date(self, date_str: str) -> Optional[datetime]:
        """Parse common Turkish and ISO-like date formats."""
        if not date_str:
            return None

        months = {
            'ocak': 1,
            'şubat': 2,
            'subat': 2,
            'mart': 3,
            'nisan': 4,
            'mayıs': 5,
            'mayis': 5,
            'haziran': 6,
            'temmuz': 7,
            'ağustos': 8,
            'agustos': 8,
            'eylül': 9,
            'eylul': 9,
            'ekim': 10,
            'kasım': 11,
            'kasim': 11,
            'aralık': 12,
            'aralik': 12,
        }

        try:
            normalized = date_str.strip().replace('Z', '+00:00')

            # ISO-like format
            try:
                return datetime.fromisoformat(normalized)
            except ValueError:
                pass

            # DD.MM.YYYY
            match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', normalized)
            if match:
                day, month, year = map(int, match.groups())
                return datetime(year, month, day)

            # DD Month YYYY
            lower_text = normalized.lower()
            match = re.search(
                r'(\d{1,2})\s+(ocak|şubat|subat|mart|nisan|mayıs|mayis|haziran|temmuz|ağustos|agustos|eylül|eylul|ekim|kasım|kasim|aralık|aralik)\s+(\d{4})',
                lower_text,
                re.IGNORECASE
            )
            if match:
                day = int(match.group(1))
                month_name = match.group(2).lower()
                year = int(match.group(3))
                month = months.get(month_name)
                if month:
                    return datetime(year, month, day)

        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {e}")

        return None

    @abstractmethod
    def scrape(self, days: int = DEFAULT_SCRAPE_DAYS) -> List[Dict]:
        """
        Scrape news from the source
        Must return a list of dictionaries with at least:
        - title: str
        - content: str
        - publish_date: datetime
        - url: str
        """
        pass

    @abstractmethod
    def parse_article(self, article_url: str) -> Optional[Dict]:
        """
        Parse a single article page
        Must return a dictionary with:
        - title: str
        - content: str
        - publish_date: datetime
        """
        pass
