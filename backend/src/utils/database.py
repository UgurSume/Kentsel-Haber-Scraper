"""
Database connection and operations
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure
from src.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager"""

    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB"""
        try:
            cls.client = AsyncIOMotorClient(settings.MONGODB_URI)
            cls.db = cls.client[settings.MONGODB_DB_NAME]

            # Test connection
            await cls.client.admin.command('ping')
            logger.info(f"✅ Connected to MongoDB: {settings.MONGODB_DB_NAME}")

            # Create indexes
            await cls.create_indexes()

        except ConnectionFailure as e:
            logger.error(f"❌ Could not connect to MongoDB: {e}")
            raise

    @classmethod
    async def close_db(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            logger.info("🔌 MongoDB connection closed")

    @classmethod
    async def create_indexes(cls):
        """Create database indexes"""
        try:
            news_collection = cls.db.news

            # Index for similarity hash (duplicate check)
            await news_collection.create_index("similarity_hash")

            # Index for news type
            await news_collection.create_index("news_type")

            # Index for publish date
            await news_collection.create_index("publish_date")

            # Compound indexes for duplicate candidate narrowing
            await news_collection.create_index([
                ("news_type", 1),
                ("publish_date", -1)
            ])
            await news_collection.create_index([
                ("similarity_hash", 1),
                ("news_type", 1)
            ])

            # Index for location coordinates
            await news_collection.create_index("location.coordinates")

            # Text index for search
            await news_collection.create_index([
                ("title", "text"),
                ("content", "text")
            ])

            logger.info("✅ Database indexes created")

        except Exception as e:
            logger.error(f"❌ Error creating indexes: {e}")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if cls.db is None:
            raise RuntimeError("Database not connected. Call connect_db() first.")
        return cls.db


# Global database instance
db = Database()
