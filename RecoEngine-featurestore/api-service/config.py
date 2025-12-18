"""
RecoEngine Configuration Management

Compatible with Pydantic v2 and pydantic-settings
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=[".env", "env.config", "../env.config"],
        case_sensitive=True,
        extra="ignore"  # Ignore extra environment variables
    )
    
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
    API_PORT: int = 8001
    
    # Model Configuration
    MODEL_PATH: str = "churn_model.joblib"
    MODEL_METRICS_PATH: str = "churn_model_metrics.json"
    
    # Training Configuration
    DEFAULT_TRAINING_SAMPLES: int = 5000
    DEFAULT_TEST_SIZE: float = 0.2
    RANDOM_STATE: int = 42
    
    # LLM Configuration
    GEMINI_API_KEY: str = ""  # Set via environment variable or .env file
    GEMINI_MODEL: str = "gemini-2.5-flash"  # Options: "gemini-1.5-flash" (faster) or "gemini-1.5-pro" (higher quality)
    
    # Agent Flow Configuration
    USE_AGENT_FLOW: bool = False  # Set to True to use LangGraph agent workflow

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
if os.getenv("GEMINI_API_KEY"):
    settings.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if os.getenv("GEMINI_MODEL"):
    settings.GEMINI_MODEL = os.getenv("GEMINI_MODEL")
if os.getenv("USE_AGENT_FLOW"):
    settings.USE_AGENT_FLOW = os.getenv("USE_AGENT_FLOW", "false").lower() == "true"
