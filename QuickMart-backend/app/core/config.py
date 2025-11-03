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
    
    # Database - Aerospike Cloud Configuration
    AEROSPIKE_HOST: str = "localhost"
    AEROSPIKE_PORT: int = 3000
    AEROSPIKE_NAMESPACE: str = "churnprediction"
    # TLS Configuration for Aerospike Cloud (requires CA file for server authentication)
    AEROSPIKE_USE_TLS: bool = False
    AEROSPIKE_TLS_CAFILE: str = ""
    AEROSPIKE_TLS_NAME: str = ""
    # Authentication credentials for Aerospike Cloud
    AEROSPIKE_USERNAME: str = ""
    AEROSPIKE_PASSWORD: str = ""
    
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
        env_file = [".env", "env.config"]
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
if os.getenv("AEROSPIKE_USE_TLS"):
    settings.AEROSPIKE_USE_TLS = os.getenv("AEROSPIKE_USE_TLS").lower() in ("true", "1", "yes")
if os.getenv("AEROSPIKE_TLS_CAFILE"):
    settings.AEROSPIKE_TLS_CAFILE = os.getenv("AEROSPIKE_TLS_CAFILE")
if os.getenv("AEROSPIKE_TLS_NAME"):
    settings.AEROSPIKE_TLS_NAME = os.getenv("AEROSPIKE_TLS_NAME")
if os.getenv("AEROSPIKE_USERNAME"):
    settings.AEROSPIKE_USERNAME = os.getenv("AEROSPIKE_USERNAME")
if os.getenv("AEROSPIKE_PASSWORD"):
    settings.AEROSPIKE_PASSWORD = os.getenv("AEROSPIKE_PASSWORD")
if os.getenv("RECO_ENGINE_URL"):
    settings.RECO_ENGINE_URL = os.getenv("RECO_ENGINE_URL")
if os.getenv("JWT_SECRET"):
    settings.JWT_SECRET = os.getenv("JWT_SECRET")
