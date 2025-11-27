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

@users_router.get("/messages")
async def get_user_messages(current_user: dict = Depends(get_current_user)):
    """Get custom messages for the current user from the nudge system"""
    try:
        # Get all custom messages
        all_messages = await database_manager.scan_set("custom_user_messages")
        user_messages = []
        
        for message_data in all_messages:
            if message_data.get("user_id") == current_user["user_id"]:
                # Transform shortened field names to full names for frontend
                normalized_message = {
                    "user_id": message_data.get("user_id"),
                    "message_id": message_data.get("message_id"),
                    "message": message_data.get("message"),
                    "churn_probability": message_data.get("churn_prob", 0),  # Transform churn_prob -> churn_probability
                    "churn_reasons": message_data.get("churn_reasons", []),
                    "user_features": message_data.get("user_ftrs", {}),  # Transform user_ftrs -> user_features
                    "created_at": message_data.get("created_at"),
                    "status": message_data.get("status"),
                    "read_at": message_data.get("read_at")
                }
                user_messages.append(normalized_message)
        
        # Sort by creation date (newest first)
        user_messages.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        logger.info(f"Retrieved {len(user_messages)} messages for user {current_user['user_id']}")
        
        return {
            "messages": user_messages,
            "total_messages": len(user_messages),
            "unread_count": sum(1 for msg in user_messages if msg.get("status") == "generated")
        }
        
    except Exception as e:
        logger.error(f"Error fetching user messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch messages"
        )

@users_router.put("/messages/{message_id}/mark-read")
async def mark_message_read(message_id: str, current_user: dict = Depends(get_current_user)):
    """Mark a message as read"""
    try:
        # Get the message
        key = f"{current_user['user_id']}_{message_id}"
        message = await database_manager.get("custom_user_messages", key)
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Update status to read
        message["status"] = "read"
        message["read_at"] = database_manager.get_timestamp()
        
        success = await database_manager.put("custom_user_messages", key, message)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark message as read"
            )
        
        logger.info(f"Marked message {message_id} as read for user {current_user['user_id']}")
        return {"message": "Message marked as read", "message_id": message_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking message as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark message as read"
        )
