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
        return readings
    
    def _map_schema(self, raw_doc: dict) -> dict:
        """
        Map the user's custom MongoDB schema (nested 'data' object)
        to the flat format expected by our Scorer.
        """
        data = raw_doc.get("data", {})
        
        # Extract timestamp
        ts = raw_doc.get("timestamp")
        if isinstance(ts, datetime):
            ts = ts.isoformat()
        elif not ts:
            ts = datetime.utcnow().isoformat()
            
        return {
            "timestamp": ts,
            # Schema Mapping:
            "air_temp": data.get("air_temperature", 25.0),
            "soil_moisture": data.get("soil_moisture", 50.0),
            "humidity": data.get("humidity", 50.0),
            "soil_temp": data.get("soil_temperature", 20.0),
            "ph": data.get("soil_ph", 6.5),
            "sunlight": data.get("sunlight_intensity", 5000), # Note: 'intensity' suffix
            "nitrogen": data.get("soil_nitrogen", 100),       # Note: 'soil_' prefix
            "air_quality": data.get("air_quality", 50),
            # Keep IDs for reference
            "_id": str(raw_doc.get("_id", "")),
            "crop_id": raw_doc.get("crop_id", settings.crop_id),
        }

    async def get_new_readings_since(self, since_timestamp: str,
                                      crop_id: str = None) -> list[dict]:
        """
        Fetch only NEW readings that arrived after `since_timestamp`.
        Returns list of mapped data dicts sorted oldest → newest.
        """
        crop_id = crop_id or settings.crop_id
        
        query = {
            "crop_id": crop_id,
            "timestamp": {"$gt": since_timestamp}
        }
        cursor = self.collection.find(query).sort("timestamp", 1)
        
        readings = []
        async for doc in cursor:
            readings.append(self._map_schema(doc))
        
        return readings
    
    async def get_all_readings(self, crop_id: str = None) -> list[dict]:
        """
        Fetch ALL readings for a crop, sorted oldest → newest.
        Used on startup to load the full history at once.
        """
        crop_id = crop_id or settings.crop_id
        
        cursor = self.collection.find({"crop_id": crop_id}).sort("timestamp", 1)
        
        readings = []
        readings = []
        async for doc in cursor:
            readings.append(self._map_schema(doc))
        
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
            return self._map_schema(doc)
        return None

    async def save_score(self, reading_id: str, score_result: dict):
        """
        Update the original sensor reading document with the AI analysis.
        """
        if not reading_id:
            return

        from bson import ObjectId
        try:
            # Convert string ID to ObjectId if valid
            if ObjectId.is_valid(reading_id):
                oid = ObjectId(reading_id)
            else:
                oid = reading_id
                
            update_data = {
                "ai_analysis": {
                    "score": score_result["predicted_score"],
                    "status": "analyzed",
                    "scored_at": datetime.utcnow().isoformat(),
                    "details": score_result["per_parameter"]
                }
            }
            
            await self.collection.update_one(
                {"_id": oid},
                {"$set": update_data}
            )
            print(f"✅ Score saved for reading {reading_id}")
            
        except Exception as e:
            print(f"❌ Failed to save score for {reading_id}: {e}")


# Singleton instance
db = Database()
