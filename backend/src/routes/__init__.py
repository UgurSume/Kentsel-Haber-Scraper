"""Routes package"""
from .news_routes import router as news_router
from .scraping_routes import router as scraping_router

__all__ = ["news_router", "scraping_router"]
