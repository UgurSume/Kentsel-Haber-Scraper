"""
API Routes for news operations
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
import re
import logging
from src.utils.database import db
from src.models import NewsArticle
from bson import ObjectId
from src.config import (
    REQUIRED_NEWS_TYPES,
    KOCAELI_DISTRICTS,
    NEWS_SOURCES,
    KOCAELISPOR_STADIUM,
    DEFAULT_STADIUM_RADIUS_KM,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/news", tags=["news"])


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """İki koordinat arasındaki mesafeyi kilometre cinsinden hesaplar."""
    r = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c


@router.get("/meta", response_model=dict)
async def get_news_metadata():
    """
    Metadata contract for frontend filters and constants
    """
    return {
        "news_types": REQUIRED_NEWS_TYPES,
        "districts": KOCAELI_DISTRICTS,
        "sources": [source["name"] for source in NEWS_SOURCES],
        "stadium": {
            "name": KOCAELISPOR_STADIUM["name"],
            "lat": KOCAELISPOR_STADIUM["lat"],
            "lng": KOCAELISPOR_STADIUM["lng"],
            "default_radius_km": DEFAULT_STADIUM_RADIUS_KM,
        }
    }


@router.get("/", response_model=List[dict])
async def get_news(
    news_type: Optional[str] = Query(None, description="Filter by news type"),
    district: Optional[str] = Query(None, description="Filter by district"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    around_stadium: bool = Query(False, description="Filter by distance to Kocaeli Stadyumu"),
    radius_km: float = Query(DEFAULT_STADIUM_RADIUS_KM, ge=0.1, le=50, description="Radius around stadium in km"),
    limit: int = Query(100, ge=1, le=500, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get news articles with optional filters
    """
    try:
        database = db.get_db()

        # Spor haberlerinde stadyum çevresi filtresi otomatik ve sabit yarıçap ile uygulanır
        if news_type == "Spor":
            around_stadium = True
            radius_km = DEFAULT_STADIUM_RADIUS_KM

        # Build query
        query = {}

        if news_type:
            query["news_type"] = news_type

        if district:
            query["location.district"] = district

        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = datetime.fromisoformat(start_date)
            if end_date:
                date_query["$lte"] = datetime.fromisoformat(end_date) + timedelta(days=1) - timedelta(seconds=1)
            query["publish_date"] = date_query

        # Execute query
        # Stadyum çevresi filtresinde mesafe hesabı uygulamak için geniş aday kümesi alınır
        db_limit = limit * 5 if around_stadium else limit
        # List endpoint'i için ağır alanları (content/embedding) getirmeyerek yanıtı hızlandır.
        projection = {
            "news_type": 1,
            "title": 1,
            "publish_date": 1,
            "location": 1,
            "sources": 1,
            "keywords": 1,
        }
        cursor = database.news.find(query, projection).sort("publish_date", -1).skip(offset).limit(db_limit)
        articles = await cursor.to_list(length=db_limit)

        if around_stadium:
            center_lat = KOCAELISPOR_STADIUM["lat"]
            center_lng = KOCAELISPOR_STADIUM["lng"]

            filtered_articles = []
            for article in articles:
                location = article.get("location") or {}
                title_lower = (article.get("title") or "").lower()
                loc_text = (location.get("text") or "").strip().lower()
                coords = location.get("coordinates") or {}

                # Eski kayıtlarda spor haberlerinin konumu eksikse (veya Kocaelispor'da sadece
                # "Kocaeli" dönmüşse) stadyum merkezini koşullu fallback olarak uygula.
                if news_type == "Spor":
                    is_kocaelispor_news = bool(re.search(r"kocaeli\s*spor", title_lower))
                    needs_stadium_fallback = (
                        is_kocaelispor_news
                        or ((not is_kocaelispor_news) and not coords and not loc_text)
                    )
                    if needs_stadium_fallback:
                        if "location" not in article or article["location"] is None:
                            article["location"] = {}
                        article["location"]["coordinates"] = {"lat": center_lat, "lng": center_lng}
                        if not article["location"].get("district"):
                            article["location"]["district"] = KOCAELISPOR_STADIUM["district"]
                        if not article["location"].get("text"):
                            article["location"]["text"] = KOCAELISPOR_STADIUM["name"]
                        coords = article["location"]["coordinates"]

                lat = coords.get("lat")
                lng = coords.get("lng")

                if lat is None or lng is None:
                    continue

                distance = _haversine_km(center_lat, center_lng, float(lat), float(lng))
                if distance <= radius_km:
                    article["distance_to_stadium_km"] = round(distance, 2)
                    filtered_articles.append(article)

            articles = filtered_articles[:limit]

        # Convert ObjectId to string
        for article in articles:
            article['_id'] = str(article['_id'])

        logger.info(f"[SUCCESS] Retrieved {len(articles)} articles")

        return articles

    except Exception as e:
        logger.error(f"[ERROR] Failed to get news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{news_id}", response_model=dict)
async def get_news_by_id(news_id: str):
    """
    Get a single news article by ID
    """
    try:
        database = db.get_db()

        # Validate ObjectId
        if not ObjectId.is_valid(news_id):
            raise HTTPException(status_code=400, detail="Invalid news ID")

        # Find article
        article = await database.news.find_one({"_id": ObjectId(news_id)})

        if not article:
            raise HTTPException(status_code=404, detail="News article not found")

        # Convert ObjectId to string
        article['_id'] = str(article['_id'])

        return article

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to get news by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_stats():
    """
    Get statistics about news articles
    """
    try:
        database = db.get_db()

        # Total count
        total = await database.news.count_documents({})

        # Count by news type
        type_counts = await database.news.aggregate([
            {"$group": {"_id": "$news_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]).to_list(length=None)

        # Count by district
        district_counts = await database.news.aggregate([
            {"$match": {"location.district": {"$ne": None}}},
            {"$group": {"_id": "$location.district", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]).to_list(length=None)

        # Recent articles (last 24 hours)
        from datetime import timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_count = await database.news.count_documents({
            "created_at": {"$gte": yesterday}
        })

        return {
            "total_articles": total,
            "recent_articles": recent_count,
            "by_type": type_counts,
            "by_district": district_counts
        }

    except Exception as e:
        logger.error(f"[ERROR] Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{news_id}")
async def delete_news(news_id: str):
    """
    Delete a news article by ID
    """
    try:
        database = db.get_db()

        # Validate ObjectId
        if not ObjectId.is_valid(news_id):
            raise HTTPException(status_code=400, detail="Invalid news ID")

        # Delete article
        result = await database.news.delete_one({"_id": ObjectId(news_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="News article not found")

        return {"message": "News article deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete news: {e}")
        raise HTTPException(status_code=500, detail=str(e))
