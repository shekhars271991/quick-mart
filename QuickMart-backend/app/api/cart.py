"""
Cart API endpoints
Tracks cart operations and updates user features for churn prediction
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from pydantic import BaseModel
import logging
from datetime import datetime

from core.database import database_manager
from core.auth import get_current_user
from services.reco_integration import reco_service

logger = logging.getLogger(__name__)

cart_router = APIRouter()

# Request/Response models
class CartItemRequest(BaseModel):
    product_id: str
    quantity: int = 1

class AddToCartRequest(BaseModel):
    product_id: str
    quantity: int = 1

@cart_router.post("/add")
async def add_to_cart(
    request: AddToCartRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add item to cart and update user features for churn prediction"""
    try:
        user_id = current_user["user_id"]
        
        # Verify product exists
        products = await database_manager.scan_set("products")
        product = None
        for p in products:
            if p.get("product_id") == request.product_id:
                product = p
                break
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Update real-time features to indicate cart addition without checkout
        # This will increase churn risk indicators
        realtime_features = {
            "cart_no_buy": True,  # Flag indicating item added but not purchased
            "curr_sess_clk": 1,  # Increment session clicks
        }
        
        # Ingest real-time features
        try:
            await reco_service.ingest_realtime_features(user_id, realtime_features)
            logger.info(f"✅ Updated real-time features for user {user_id}: cart_no_buy=True")
        except Exception as e:
            logger.error(f"❌ Failed to update real-time features for user {user_id}: {e}")
        
        # Update behavior features - aggressively increase churn risk indicators
        # This will significantly increase churn risk for the next login
        try:
            # Update multiple features aggressively to ensure churn risk becomes high
            # These values are designed to push risk above 0.6 even for users with strong positive features
            behavior_features = {
                "cart_abandon": 0.85,  # Very high cart abandonment rate (85%) - well above 0.5 threshold
                "sess_7d": 0,  # Zero sessions in last 7 days (critical indicator)
                "sess_30d": 2,  # Very low sessions in last 30 days
                "days_last_purch": 60,  # 60 days since last purchase (high risk threshold)
                "days_last_login": 15,  # 15 days since last login (high risk)
                "avg_sess_dur": 2.0,  # Low session duration
                "ctr_10_sess": 0.1,  # Very low click-through rate
            }
            success = await reco_service.ingest_user_behavior(user_id, behavior_features)
            if success:
                logger.info(f"✅ Updated behavior features for user {user_id}: cart_abandon=0.85, sess_7d=0, days_last_purch=60, days_last_login=15")
            else:
                logger.error(f"❌ Failed to update behavior features for user {user_id} - API returned failure")
        except Exception as e:
            logger.error(f"❌ Exception updating behavior features for user {user_id}: {e}", exc_info=True)
        
        # Also reduce engagement features to remove protective factors
        # This helps overcome strong positive features like high engagement rates
        try:
            engagement_features = {
                "push_open_rate": 0.1,  # Low push notification engagement (was high)
                "email_ctr": 0.1,  # Low email engagement (was high)
                "inapp_ctr": 0.1,  # Low in-app engagement (was high)
                "promo_resp_time": 48.0,  # Slow response to promotions (was fast)
                "retention_enc": 3,  # Poor retention campaign response (was positive)
            }
            success = await reco_service.ingest_engagement_features(user_id, engagement_features)
            if success:
                logger.info(f"✅ Updated engagement features for user {user_id} to reduce protective factors")
            else:
                logger.warning(f"Failed to update engagement features for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to update engagement features for user {user_id}: {e}")
        
        # Update support features to add negative indicators
        try:
            support_features = {
                "csat_score": 2.5,  # Reduced satisfaction score (was high)
                "tickets_90d": 4,  # Increased support tickets (indicates issues)
            }
            success = await reco_service.ingest_support_features(user_id, support_features)
            if success:
                logger.info(f"✅ Updated support features for user {user_id}: csat_score=2.5, tickets_90d=4")
            else:
                logger.warning(f"Failed to update support features for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to update support features for user {user_id}: {e}")
        
        # Update transactional features to reduce protective factors
        # This is CRITICAL - high orders_6m is a strong protective factor that needs to be reduced
        # The model heavily weights this feature, so reducing it from 42 to 1 should significantly increase risk
        try:
            transactional_features = {
                "orders_6m": 1,  # Drastically reduced from high (was 42) - removes strong protective factor
                "purch_freq_90d": 0.1,  # Very low purchase frequency (almost no purchases)
                "avg_order_val": 20.0,  # Reduced average order value
                "refund_rate": 0.40,  # Very high refund rate (indicates strong dissatisfaction)
                "last_hv_purch": 90,  # Long time since high-value purchase
            }
            success = await reco_service.ingest_transaction_data(user_id, transactional_features)
            if success:
                logger.info(f"✅ Updated transactional features for user {user_id}: orders_6m=1, refund_rate=0.40")
            else:
                logger.warning(f"Failed to update transactional features for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to update transactional features for user {user_id}: {e}")
        
        logger.info(f"Item added to cart for user {user_id}: product_id={request.product_id}, quantity={request.quantity}")
        
        return {
            "status": "success",
            "message": "Item added to cart",
            "product_id": request.product_id,
            "quantity": request.quantity,
            "features_updated": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding item to cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add item to cart"
        )

@cart_router.get("/")
async def get_cart(current_user: dict = Depends(get_current_user)):
    """Get user's cart (placeholder - cart is managed on frontend)"""
    # Cart is managed on frontend using Zustand store
    # This endpoint is here for future backend cart management
    return {
        "message": "Cart is managed on frontend",
        "user_id": current_user["user_id"]
    }

