"""
Admin API endpoints
"""

from fastapi import APIRouter, HTTPException, status
import logging

from core.database import database_manager

logger = logging.getLogger(__name__)

admin_router = APIRouter()


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
