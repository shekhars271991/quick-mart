"""
User management API endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
import logging

from core.database import database_manager
from core.auth import get_current_user
from models.user import UserResponse, UserPreferences

logger = logging.getLogger(__name__)

users_router = APIRouter()

@users_router.get("/preferences", response_model=UserPreferences)
async def get_user_preferences(current_user: dict = Depends(get_current_user)):
    """Get user preferences"""
    try:
        user_record = await database_manager.get("users", current_user["user_id"])
        if not user_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        preferences = user_record.get("preferences", {})
        return UserPreferences(**preferences)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch preferences"
        )

@users_router.put("/preferences", response_model=UserPreferences)
async def update_user_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(get_current_user)
):
    """Update user preferences"""
    try:
        user_record = await database_manager.get("users", current_user["user_id"])
        if not user_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update preferences
        user_record["preferences"] = preferences.dict()
        
        success = await database_manager.put("users", current_user["user_id"], user_record)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update preferences"
            )
        
        logger.info(f"Preferences updated for user: {current_user['user_id']}")
        return preferences
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )

@users_router.get("/purchase-history")
async def get_purchase_history(current_user: dict = Depends(get_current_user)):
    """Get user's purchase history"""
    try:
        # Get user's orders
        orders_data = await database_manager.scan_set("orders")
        user_orders = []
        
        for order_data in orders_data:
            if order_data.get("user_id") == current_user["user_id"]:
                user_orders.append(order_data)
        
        # Sort by creation date (newest first)
        user_orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {"orders": user_orders, "total_orders": len(user_orders)}
        
    except Exception as e:
        logger.error(f"Error fetching purchase history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch purchase history"
        )
