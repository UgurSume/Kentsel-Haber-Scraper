"""Scrapers package"""
from .base_scraper import BaseScraper
from .cagdas_kocaeli import CagdasKocaeliScraper
from .ozgur_kocaeli import OzgurKocaeliScraper
from .ses_kocaeli import SesKocaeliScraper
from .yeni_kocaeli import YeniKocaeliScraper
from .bizim_yaka import BizimYakaScraper

__all__ = [
    "BaseScraper",
    "CagdasKocaeliScraper",
    "OzgurKocaeliScraper",
    "SesKocaeliScraper",
    "YeniKocaeliScraper",
    "BizimYakaScraper"
]
