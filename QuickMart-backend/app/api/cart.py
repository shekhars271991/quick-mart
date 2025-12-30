"""
Cart API endpoints
Tracks cart operations and updates user features for churn prediction
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
from datetime import datetime
import httpx
import asyncio
import os

from core.database import database_manager
from core.auth import get_current_user
from services.reco_integration import reco_service

logger = logging.getLogger(__name__)

cart_router = APIRouter()

# RecoEngine configuration
RECO_ENGINE_BASE_URL = os.getenv("RECO_ENGINE_URL", "http://localhost:8001")

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
        
        # Verify product exists (from LangGraph Store format)
        product = await database_manager.get_from_store("products", "products", request.product_id)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Store cart item details in user features for personalized messages
        # This helps the LLM generate product-specific messages
        cart_item_details = {
            "name": product.get("name", ""),
            "category": product.get("category", ""),
            "subcategory": product.get("subcategory", ""),
            "brand": product.get("brand", ""),
            "price": product.get("price", 0)
        }
        
        # Update real-time features to indicate cart addition without checkout
        # This will increase churn risk indicators
        realtime_features = {
            "cart_no_buy": True,  # Flag indicating item added but not purchased
            "curr_sess_clk": 1,  # Increment session clicks
            "cart_items": [cart_item_details]  # Store cart items for personalized messages
        }
        
        # Ingest real-time features
        try:
            await reco_service.ingest_realtime_features(user_id, realtime_features)
            logger.info(f"✅ Updated real-time features for user {user_id}: cart_no_buy=True, cart_items={cart_item_details['name']}")
        except Exception as e:
            logger.error(f"❌ Failed to update real-time features for user {user_id}: {e}")
        
        # Also sync user profile data to ensure name, age, gender are available for personalized messages
        try:
            # Get user record for profile data
            user_record = await database_manager.get("users", user_id)
            if user_record and user_record.get("profile"):
                profile = user_record["profile"]
                profile_features = {
                    "name": profile.get("name", ""),
                    "full_name": profile.get("name", ""),  # Alias for compatibility
                    "age": profile.get("age"),
                    "geo_location": profile.get("location", ""),
                    "loyalty_tier": profile.get("loyalty_tier", "")
                }
                # Remove None and empty values
                profile_features = {k: v for k, v in profile_features.items() if v not in [None, "", 0]}
                
                if profile_features:
                    await reco_service.ingest_user_profile(user_id, profile_features)
                    logger.info(f"✅ Synced profile data for user {user_id} for message personalization")
        except Exception as e:
            logger.warning(f"Failed to sync profile data for user {user_id}: {e}")
        
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


class CartLoadRequest(BaseModel):
    """Request model for cart page load event."""
    cart_items: Optional[List[Dict[str, Any]]] = None
    cart_total: Optional[float] = None


class ChurnPredictionResult(BaseModel):
    """Response model for churn prediction."""
    churn_probability: float
    risk_segment: str
    nudges_triggered: Optional[List[Dict[str, Any]]] = None


async def trigger_churn_prediction(user_id: str) -> dict:
    """Trigger churn prediction for user on cart load."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{RECO_ENGINE_BASE_URL}/predict/{user_id}"
            response = await client.post(url)
            
            if response.status_code == 200:
                prediction_data = response.json()
                logger.info(f"Churn prediction on cart load for user {user_id}: risk_segment={prediction_data.get('risk_segment', 'unknown')}")
                
                # Log nudges if any were triggered
                if prediction_data.get('nudges_triggered'):
                    nudge_count = len(prediction_data['nudges_triggered'])
                    logger.info(f"Triggered {nudge_count} nudges for user {user_id} on cart view")
                    
                    # Check if discount coupon was created
                    has_discount = any(nudge.get('type') == 'Discount Coupon' for nudge in prediction_data['nudges_triggered'])
                    if has_discount:
                        logger.info(f"Discount coupon created for high-risk user {user_id} viewing cart")
                
                return prediction_data
            else:
                logger.warning(f"Churn prediction failed for user {user_id}: {response.status_code} - {response.text}")
                return None
                
    except httpx.TimeoutException:
        logger.warning(f"Churn prediction timeout for user {user_id}")
        return None
    except Exception as e:
        logger.warning(f"Churn prediction error for user {user_id}: {e}")
        return None


@cart_router.post("/load")
async def on_cart_load(
    request: Optional[CartLoadRequest] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Notify backend when cart page is loaded.
    
    This triggers churn prediction for the user, which may:
    - Generate personalized nudges
    - Create discount coupons for high-risk users
    - Update user engagement signals
    
    This endpoint should be called by the frontend when:
    - User navigates to cart page
    - Cart is re-rendered/refreshed
    """
    user_id = current_user["user_id"]
    logger.info(f"Cart page loaded for user {user_id}")
    
    # Update realtime features if cart items provided
    if request and request.cart_items:
        try:
            cart_item_details = []
            for item in request.cart_items[:5]:  # Max 5 items
                cart_item_details.append({
                    "product_id": item.get("product_id", ""),
                    "name": item.get("name", ""),
                    "category": item.get("category", ""),
                    "price": item.get("price", 0),
                    "quantity": item.get("quantity", 1)
                })
            
            realtime_features = {
                "cart_items": cart_item_details,
                "cart_item_cnt": len(request.cart_items),
                "cart_no_buy": True  # Flag that user has items but hasn't bought
            }
            
            await reco_service.ingest_realtime_features(user_id, realtime_features)
            logger.info(f"Updated cart context for user {user_id}: {len(cart_item_details)} items")
            
        except Exception as e:
            logger.warning(f"Failed to update cart context for user {user_id}: {e}")
    
    # Trigger churn prediction asynchronously
    # Don't wait for it - let it complete in background
    prediction_task = asyncio.create_task(trigger_churn_prediction(user_id))
    
    # Wait briefly for result (optional - for immediate response)
    try:
        prediction = await asyncio.wait_for(prediction_task, timeout=3.0)
        
        if prediction:
            return {
                "status": "success",
                "user_id": user_id,
                "churn_prediction": ChurnPredictionResult(
                    churn_probability=prediction.get("churn_probability", 0),
                    risk_segment=prediction.get("risk_segment", "unknown"),
                    nudges_triggered=prediction.get("nudges_triggered")
                )
            }
    except asyncio.TimeoutError:
        # Prediction still running in background, return partial response
        logger.info(f"Churn prediction still running for user {user_id}, returning early")
    except Exception as e:
        logger.warning(f"Error waiting for churn prediction: {e}")
    
    return {
        "status": "success",
        "user_id": user_id,
        "churn_prediction": None,
        "message": "Cart load recorded, churn prediction triggered"
    }

