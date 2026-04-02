"""Unit tests for BaseScraper utility methods."""
import os
import sys

# Add backend root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.scrapers.base_scraper import BaseScraper, BeautifulSoup


class DummyScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="Dummy", base_url="https://example.com")

    def scrape(self, days: int = 3):
        return []

    def parse_article(self, article_url: str):
        return None


def test_extract_candidate_urls_filters_and_deduplicates():
    scraper = DummyScraper()
    html = """
    <html>
      <body>
        <a href="/haber/abc">haber 1</a>
        <a href="/haber/abc">haber 1 duplicate</a>
        <a href="/video/abc">video</a>
        <a href="https://example.com/2026/03/olay">dated article</a>
        <a href="https://another.com/haber/x">external</a>
      </body>
    </html>
    """

    soup = BeautifulSoup(html, "lxml")
    urls = scraper.extract_candidate_urls(soup, max_links=20)

    assert "https://example.com/haber/abc" in urls
    assert "https://example.com/2026/03/olay" in urls
    assert len(urls) == 2


def test_parse_turkish_date_supports_iso_and_text_formats():
    scraper = DummyScraper()

    iso_date = scraper.parse_turkish_date("2026-03-20T10:15:00")
    tr_date = scraper.parse_turkish_date("20 Mart 2026")

    assert iso_date is not None
    assert tr_date is not None
    assert iso_date.year == 2026
    assert tr_date.month == 3
