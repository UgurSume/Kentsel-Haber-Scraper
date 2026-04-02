"""
API Routes for news operations
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import logging
from src.utils.database import db
from src.models import NewsArticle
from bson import ObjectId
from src.config import REQUIRED_NEWS_TYPES, KOCAELI_DISTRICTS, NEWS_SOURCES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/meta", response_model=dict)
async def get_news_metadata():
    """
    Metadata contract for frontend filters and constants
    """
    return {
        "news_types": REQUIRED_NEWS_TYPES,
        "districts": KOCAELI_DISTRICTS,
        "sources": [source["name"] for source in NEWS_SOURCES]
    }


@router.get("/", response_model=List[dict])
async def get_news(
    news_type: Optional[str] = Query(None, description="Filter by news type"),
    district: Optional[str] = Query(None, description="Filter by district"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=500, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get news articles with optional filters
    """
    try:
        database = db.get_db()

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
        cursor = database.news.find(query).sort("publish_date", -1).skip(offset).limit(limit)
        articles = await cursor.to_list(length=limit)

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
