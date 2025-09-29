"""
QuickMart Backend API
Main FastAPI application entry point
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from core.config import settings
from core.database import database_manager
from api.auth import auth_router
from api.products import products_router
from api.coupons import coupons_router
from api.users import users_router
from api.admin import admin_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 Starting QuickMart Backend...")
    
    # Initialize database connection
    try:
        await database_manager.connect()
        logger.info("✅ Connected to Aerospike database")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        raise
    
    
    logger.info("🎉 QuickMart Backend started successfully! (Data initialization disabled - use admin endpoints if needed)")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down QuickMart Backend...")
    await database_manager.disconnect()
    logger.info("✅ Database connection closed")

# Create FastAPI app
app = FastAPI(
    title="QuickMart Backend API",
    description="E-commerce backend with AI-powered churn prevention",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(products_router, prefix="/api/products", tags=["Products"])
app.include_router(coupons_router, prefix="/api/coupons", tags=["Coupons"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "QuickMart Backend API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_status = await database_manager.health_check()
        
        return {
            "status": "healthy",
            "database": db_status,
            "version": "1.0.0",
            "timestamp": database_manager.get_timestamp()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3010,
        reload=True
    )
