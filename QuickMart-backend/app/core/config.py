"""
Configuration settings for QuickMart Backend
"""

from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "QuickMart Backend"
    DEBUG: bool = False
    
    # Database
    AEROSPIKE_HOST: str = "localhost"
    AEROSPIKE_PORT: int = 3000
    AEROSPIKE_NAMESPACE: str = "quick_mart"
    
    # Authentication
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # RecoEngine Integration
    RECO_ENGINE_URL: str = "http://localhost:8000"
    RECO_ENGINE_TIMEOUT: int = 30
    
    # CORS - Allow all origins for development
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Data Initialization
    INIT_DATA_ON_STARTUP: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Override with environment variables if running in Docker
if os.getenv("AEROSPIKE_HOST"):
    settings.AEROSPIKE_HOST = os.getenv("AEROSPIKE_HOST")
if os.getenv("AEROSPIKE_PORT"):
    settings.AEROSPIKE_PORT = int(os.getenv("AEROSPIKE_PORT"))
if os.getenv("AEROSPIKE_NAMESPACE"):
    settings.AEROSPIKE_NAMESPACE = os.getenv("AEROSPIKE_NAMESPACE")
if os.getenv("RECO_ENGINE_URL"):
    settings.RECO_ENGINE_URL = os.getenv("RECO_ENGINE_URL")
if os.getenv("JWT_SECRET"):
    settings.JWT_SECRET = os.getenv("JWT_SECRET")
