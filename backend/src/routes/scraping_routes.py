"""
API Routes for scraping operations
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Dict
import logging
from src.services.scraping_service import scraping_service
from src.services.geocoding_service import geocoding_service
from src.services.nlp_service import nlp_service
from src.config import DEFAULT_SCRAPE_DAYS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scrape", tags=["scraping"])


@router.post("/", response_model=Dict)
async def trigger_scraping(
    background_tasks: BackgroundTasks,
    days: int = Query(DEFAULT_SCRAPE_DAYS, ge=1, le=30, description="Number of days to scrape"),
    background: bool = Query(False, description="Run in background")
):
    """
    Trigger news scraping from all sources
    """
    try:
        if background:
            # Run in background
            background_tasks.add_task(scraping_service.scrape_all_sources, days)
            return {
                "message": "Scraping started in background",
                "status": "running",
                "days": days
            }
        else:
            # Run synchronously
            logger.info(f"[START] Scraping {days} days of news...")
            result = await scraping_service.scrape_all_sources(days=days)
            return result

    except Exception as e:
        logger.error(f"[ERROR] Scraping failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_scraping_status():
    """
    Get status of scraping operations
    """
    try:
        from src.utils.database import db
        database = db.get_db()

        # Get last scraping time
        last_article = await database.news.find_one(
            {},
            sort=[("created_at", -1)]
        )

        if last_article:
            last_scrape = last_article.get('created_at')
        else:
            last_scrape = None

        # Count total articles
        total_articles = await database.news.count_documents({})

        return {
            "status": "ready",
            "last_scrape": last_scrape,
            "total_articles": total_articles,
            "sources_configured": len(scraping_service.scrapers)
        }

    except Exception as e:
        logger.error(f"[ERROR] Failed to get scraping status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repair-coordinates")
async def repair_coordinates():
    """
    Re-geocode articles that are missing coordinates.
    Finds articles where location text exists but coordinates are missing,
    and also re-extracts location from articles with no location at all.
    """
    try:
        from src.utils.database import db
        database = db.get_db()

        updated = 0
        skipped = 0
        failed = 0

        # Find all articles without coordinates
        cursor = database.news.find(
            {"$or": [
                {"location": None},
                {"location.coordinates": None},
                {"location.coordinates": {"$exists": False}},
            ]}
        )
        articles = await cursor.to_list(length=500)

        logger.info(f"[REPAIR] Found {len(articles)} articles without coordinates")

        for article in articles:
            article_id = article["_id"]
            location_text = None

            # Use existing location text if present
            if article.get("location") and article["location"].get("text"):
                location_text = article["location"]["text"]
            else:
                # Re-extract location from content
                text = f"{article.get('title', '')} {article.get('cleaned_content', '') or article.get('content', '')}"
                location_text = nlp_service.extract_location(text)

            if not location_text:
                skipped += 1
                continue

            # Try to geocode
            coordinates = geocoding_service.geocode_location(location_text)
            if not coordinates:
                logger.warning(f"[REPAIR] Could not geocode: {location_text}")
                failed += 1
                continue

            # Update article in DB
            await database.news.update_one(
                {"_id": article_id},
                {"$set": {
                    "location": {
                        "text": location_text,
                        "coordinates": coordinates,
                    }
                }}
            )
            updated += 1
            logger.info(f"[REPAIR] Updated article {article_id}: {location_text} -> {coordinates}")

        return {
            "message": "Coordinate repair complete",
            "updated": updated,
            "skipped_no_location": skipped,
            "failed_geocoding": failed,
            "total_processed": len(articles),
        }

    except Exception as e:
        logger.error(f"[ERROR] Repair failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
