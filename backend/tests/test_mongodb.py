"""
Test MongoDB connection
"""
import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import settings


async def test_connection():
    """Test MongoDB connection"""
    print("[*] Testing MongoDB connection...")
    print(f"[*] URI: {settings.MONGODB_URI}")
    print(f"[*] Database: {settings.MONGODB_DB_NAME}\n")

    try:
        # Create client
        client = AsyncIOMotorClient(settings.MONGODB_URI)

        # Test connection
        await client.admin.command('ping')
        print("[SUCCESS] Successfully connected to MongoDB!")

        # Get database
        db = client[settings.MONGODB_DB_NAME]

        # List collections
        collections = await db.list_collection_names()
        print(f"\n[INFO] Existing collections: {collections if collections else 'None'}")

        # Test insert
        test_collection = db.test_connection
        result = await test_collection.insert_one({"test": "Connection successful", "timestamp": "2024"})
        print(f"\n[SUCCESS] Test document inserted with ID: {result.inserted_id}")

        # Test find
        doc = await test_collection.find_one({"_id": result.inserted_id})
        print(f"[SUCCESS] Test document retrieved: {doc}")

        # Clean up
        await test_collection.delete_one({"_id": result.inserted_id})
        print("[SUCCESS] Test document deleted")

        # Close connection
        client.close()
        print("\n[SUCCESS] MongoDB connection test passed!")
        return True

    except ConnectionFailure as e:
        print(f"\n[ERROR] Connection failed: {e}")
        print("\n[TIP] Make sure MongoDB is running:")
        print("   - MongoDB Atlas: Check your connection string")
        print("   - Local MongoDB: Run 'mongod' or check if service is running")
        return False

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)
