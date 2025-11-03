"""
RecoEngine Configuration Management
"""

import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Database Configuration - Aerospike Cloud
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
    
    # QuickMart Integration
    QUICKMART_API_URL: str = "http://localhost:3010"
    
    # Application Settings
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Model Configuration
    MODEL_PATH: str = "churn_model.joblib"
    MODEL_METRICS_PATH: str = "churn_model_metrics.json"
    
    # Training Configuration
    DEFAULT_TRAINING_SAMPLES: int = 5000
    DEFAULT_TEST_SIZE: float = 0.2
    RANDOM_STATE: int = 42
    
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
if os.getenv("QUICKMART_API_URL"):
    settings.QUICKMART_API_URL = os.getenv("QUICKMART_API_URL")
