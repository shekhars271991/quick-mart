"""
RecoEngine Configuration Management
"""

import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Database Configuration
    AEROSPIKE_HOST: str = "localhost"
    AEROSPIKE_PORT: int = 3000
    AEROSPIKE_NAMESPACE: str = "churnprediction"
    
    # QuickMart Integration
    QUICKMART_API_URL: str = "http://localhost:3011"  # 3011 for local dev, 3010 for Docker
    
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
        extra = "ignore"  # Ignore extra environment variables

# Create settings instance
settings = Settings()

# Override with environment variables if running in Docker
if os.getenv("AEROSPIKE_HOST"):
    settings.AEROSPIKE_HOST = os.getenv("AEROSPIKE_HOST")
if os.getenv("AEROSPIKE_PORT"):
    settings.AEROSPIKE_PORT = int(os.getenv("AEROSPIKE_PORT"))
if os.getenv("AEROSPIKE_NAMESPACE"):
    settings.AEROSPIKE_NAMESPACE = os.getenv("AEROSPIKE_NAMESPACE")
if os.getenv("QUICKMART_API_URL"):
    settings.QUICKMART_API_URL = os.getenv("QUICKMART_API_URL")
