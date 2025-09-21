"""
Admin API endpoints
"""

from fastapi import APIRouter, HTTPException, status
import logging

from services.data_initializer import DataInitializer
from core.database import database_manager

logger = logging.getLogger(__name__)

admin_router = APIRouter()

@admin_router.post("/init-data")
async def initialize_data():
    """Initialize test data (admin only)"""
    try:
        data_initializer = DataInitializer()
        await data_initializer.initialize_on_startup()
        
        return {"message": "Data initialization completed successfully"}
        
    except Exception as e:
        logger.error(f"Data initialization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data initialization failed: {str(e)}"
        )

@admin_router.post("/reset-data")
async def reset_data():
    """Reset all test data (admin only)"""
    try:
        data_initializer = DataInitializer()
        result = await data_initializer.reset_all_data()
        
        return result
        
    except Exception as e:
        logger.error(f"Data reset failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data reset failed: {str(e)}"
        )

@admin_router.get("/data-status")
async def get_data_status():
    """Check data initialization status"""
    try:
        # Count records in each set
        products_count = await database_manager.count_records("products")
        users_count = await database_manager.count_records("users")
        coupons_count = await database_manager.count_records("coupons")
        categories_count = await database_manager.count_records("categories")
        
        return {
            "products": products_count,
            "users": users_count,
            "coupons": coupons_count,
            "categories": categories_count,
            "is_initialized": products_count > 0 and users_count > 0
        }
        
    except Exception as e:
        logger.error(f"Error checking data status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check data status"
        )
