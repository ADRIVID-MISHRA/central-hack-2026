"""
Configuration for Farm Condition Matching AI.
Reads from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # MongoDB
    mongo_uri: str = Field(default="mongodb://localhost:27017", alias="MONGO_URI")
    db_name: str = Field(default="central_hack", alias="DB_NAME")
    collection_name: str = Field(default="sensor_data", alias="COLLECTION_NAME")
    
    # Crop
    crop_id: str = Field(default="POTATO_001", alias="CROP_ID")
    
    # Polling
    poll_interval_seconds: int = Field(default=10, alias="POLL_INTERVAL_SECONDS")
    
    # Model
    model_path: str = Field(default="model.pkl", alias="MODEL_PATH")
    profile_path: str = Field(default="crop_profiles.json", alias="PROFILE_PATH")
    
    # Historical window
    history_window: int = Field(default=20, alias="HISTORY_WINDOW")
    
    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True


settings = Settings()
