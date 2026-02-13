"""
Database Layer for Farm Condition Matching AI.
Handles MongoDB connection and sensor data retrieval.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from datetime import datetime


class Database:
    """Async MongoDB connection manager."""
    
    def __init__(self):
        self.client: AsyncIOMotorClient = None
        self.db = None
        self.collection = None
    
    async def connect(self):
        """Establish MongoDB connection."""
        self.client = AsyncIOMotorClient(settings.mongo_uri)
        self.db = self.client[settings.db_name]
        self.collection = self.db[settings.collection_name]
        
        # Test connection
        try:
            await self.client.admin.command("ping")
            print(f"Connected to MongoDB: {settings.mongo_uri}/{settings.db_name}")
        except Exception as e:
            print(f"Warning: MongoDB connection test failed: {e}")
    
    async def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            print("MongoDB connection closed")
    
    async def get_new_readings_since(self, since_timestamp: str,
                                      crop_id: str = None) -> list[dict]:
        """
        Fetch only NEW readings that arrived after `since_timestamp`.
        Returns list of data dicts sorted oldest → newest.
        """
        crop_id = crop_id or settings.crop_id
        
        query = {
            "crop_id": crop_id,
            "timestamp": {"$gt": since_timestamp}
        }
        cursor = self.collection.find(query).sort("timestamp", 1)
        
        readings = []
        async for doc in cursor:
            data = doc.get("data", {})
            data["timestamp"] = doc.get("timestamp", datetime.utcnow().isoformat())
            readings.append(data)
        
        return readings
    
    async def get_all_readings(self, crop_id: str = None) -> list[dict]:
        """
        Fetch ALL readings for a crop, sorted oldest → newest.
        Used on startup to load the full history at once.
        """
        crop_id = crop_id or settings.crop_id
        
        cursor = self.collection.find({"crop_id": crop_id}).sort("timestamp", 1)
        
        readings = []
        async for doc in cursor:
            data = doc.get("data", {})
            data["timestamp"] = doc.get("timestamp", datetime.utcnow().isoformat())
            readings.append(data)
        
        return readings
    
    async def get_latest_reading(self, crop_id: str = None) -> dict | None:
        """
        Fetch the single most recent reading.
        """
        crop_id = crop_id or settings.crop_id
        doc = await self.collection.find_one(
            {"crop_id": crop_id},
            sort=[("timestamp", -1)]
        )
        if doc:
            data = doc.get("data", {})
            data["timestamp"] = doc.get("timestamp", "")
            return data
        return None


# Singleton instance
db = Database()
