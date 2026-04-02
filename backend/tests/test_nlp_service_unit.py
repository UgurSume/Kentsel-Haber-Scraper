"""Unit tests for NLP service behavior without external dependencies."""
import os
import sys

# Add backend root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.nlp_service import NLPService


def test_classify_news_uses_priority_for_tie():
    service = NLPService()

    news_type, keywords = service.classify_news(
        "Kocaeli'de kaza ve yangın paniği",
        "Yangın sonrası bir kaza daha meydana geldi."
    )

    assert news_type == "Yangın"
    assert "yangın" in [k.lower() for k in keywords]


def test_extract_location_detects_kocaeli_district():
    service = NLPService()

    location = service.extract_location("İzmit ilçesinde elektrik kesintisi yaşandı")

    assert location == "İzmit"


def test_clean_content_removes_html_urls_and_extra_spaces():
    service = NLPService()

    raw = "<div>Haber metni</div>  https://example.com   reklam göster   devam"
    cleaned = service.clean_content(raw)

    assert "<div>" not in cleaned
    assert "http" not in cleaned
    assert "  " not in cleaned
    assert "Haber metni" in cleaned
