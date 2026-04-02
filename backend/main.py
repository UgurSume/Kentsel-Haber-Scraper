import uvicorn
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.config import settings
from src.utils.database import db
from src.routes import news_router, scraping_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def _scheduled_scraping():
    """Run scraping automatically at startup and then every SCRAPING_SCHEDULE_HOURS hours."""
    from src.services.scraping_service import scraping_service

    # Wait a few seconds for the app to finish starting up before the first run
    await asyncio.sleep(10)

    while True:
        try:
            logger.info("[SCHEDULER] Starting automatic scraping run...")
            result = await scraping_service.scrape_all_sources(days=3)
            logger.info(
                f"[SCHEDULER] Done — saved: {result['total_saved']}, "
                f"duplicates: {result['total_duplicates']}, "
                f"skipped geocoding: {result['total_skipped_geocoding']}"
            )
        except Exception as exc:
            logger.error(f"[SCHEDULER] Scraping run failed: {exc}")

        interval_seconds = settings.SCRAPING_SCHEDULE_HOURS * 3600
        logger.info(f"[SCHEDULER] Next run in {settings.SCRAPING_SCHEDULE_HOURS} hours.")
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("🚀 Starting Kentsel Haber Scraper API...")
    await db.connect_db()

    # Start background periodic scraping task
    scraping_task = asyncio.create_task(_scheduled_scraping())
    logger.info(f"[SCHEDULER] Automatic scraping enabled (every {settings.SCRAPING_SCHEDULE_HOURS}h).")

    yield

    # Shutdown
    scraping_task.cancel()
    try:
        await scraping_task
    except asyncio.CancelledError:
        pass
    logger.info("🛑 Shutting down...")
    await db.close_db()


app = FastAPI(
    title="Kentsel Haber Scraper API",
    description="Web Scraping Tabanlı Kentsel Haber İzleme Sistemi",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else settings.origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news_router)
app.include_router(scraping_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Kentsel Haber Scraper API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await db.client.admin.command('ping')
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
