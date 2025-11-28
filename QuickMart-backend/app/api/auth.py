"""
Authentication API endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timedelta
import uuid
import logging
import httpx
import asyncio
import os
import aerospike

from core.database import database_manager
from core.auth import auth_manager, get_current_user
from models.user import User, UserCreate, UserLogin, UserResponse, UserProfile, UserPreferences

logger = logging.getLogger(__name__)

auth_router = APIRouter()

# RecoEngine configuration
RECO_ENGINE_BASE_URL = os.getenv("RECO_ENGINE_URL", "http://localhost:8001")

async def trigger_churn_prediction(user_id: str) -> dict:
    """Trigger churn prediction for user after login"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{RECO_ENGINE_BASE_URL}/predict/{user_id}"
            response = await client.post(url)
            
            if response.status_code == 200:
                prediction_data = response.json()
                logger.info(f"Churn prediction completed for user {user_id}: risk_segment={prediction_data.get('risk_segment', 'unknown')}")
                
                # Log nudges if any were triggered
                if prediction_data.get('nudges_triggered'):
                    nudge_count = len(prediction_data['nudges_triggered'])
                    logger.info(f"Triggered {nudge_count} nudges for user {user_id}")
                    
                    # Check if discount coupon was created
                    has_discount = any(nudge.get('type') == 'Discount Coupon' for nudge in prediction_data['nudges_triggered'])
                    if has_discount:
                        logger.info(f"Discount coupon created for high-risk user {user_id}")
                
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

@auth_router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_users = await database_manager.scan_set("users")
        for existing_user in existing_users:
            if existing_user.get("email") == user_data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Create new user
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        hashed_password = auth_manager.hash_password(user_data.password)
        
        user = User(
            user_id=user_id,
            email=user_data.email,
            profile=user_data.profile,
            preferences=user_data.preferences or UserPreferences(),
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        # Store user with hashed password
        user_data_with_password = user.dict()
        user_data_with_password["hashed_password"] = hashed_password
        
        success = await database_manager.put("users", user_id, user_data_with_password)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        logger.info(f"New user registered: {user.email}")
        return UserResponse(**user.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@auth_router.post("/login")
async def login_user(login_data: UserLogin):
    """Login user and return JWT token"""
    try:
        # Find user by email
        users = await database_manager.scan_set("users")
        logger.info(f"Found {len(users)} users in database")
        user_record = None
        
        for user in users:
            # Ensure user_id is set (might be stored as _key from scan)
            if not user.get("user_id") and user.get("_key"):
                user["user_id"] = user["_key"]
            
            if user.get("email") == login_data.email:
                user_record = user
                logger.info(f"Found user: {user_record.get('user_id')} - {user_record.get('email')}")
                break
        
        if not user_record:
            logger.warning(f"Login attempt with email not found: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if "hashed_password" not in user_record:
            logger.error(f"User {user_record.get('user_id')} has no hashed_password field")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        password_valid = auth_manager.verify_password(login_data.password, user_record["hashed_password"])
        if not password_valid:
            logger.warning(f"Invalid password for user: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Update last login
        user_record["last_login"] = datetime.utcnow().isoformat()
        await database_manager.put("users", user_record["user_id"], user_record)
        
        # Create access token
        token_data = {
            "sub": user_record["user_id"],
            "email": user_record["email"]
        }
        access_token = auth_manager.create_access_token(token_data)
        
        logger.info(f"User logged in: {login_data.email}")
        
        # Trigger churn prediction asynchronously (don't block login response)
        user_id = user_record["user_id"]
        asyncio.create_task(trigger_churn_prediction(user_id))
        logger.info(f"Triggered async churn prediction for user {user_id}")
        
        # Prepare response
        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse(**{k: v for k, v in user_record.items() if k != "hashed_password"})
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@auth_router.get("/profile", response_model=UserResponse)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    try:
        user_record = await database_manager.get("users", current_user["user_id"])
        if not user_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(**{k: v for k, v in user_record.items() if k != "hashed_password"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile fetch error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch profile"
        )

@auth_router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    profile_update: UserProfile,
    current_user: dict = Depends(get_current_user)
):
    """Update user profile"""
    try:
        user_record = await database_manager.get("users", current_user["user_id"])
        if not user_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update profile
        user_record["profile"] = profile_update.dict()
        
        success = await database_manager.put("users", current_user["user_id"], user_record)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile"
            )
        
        logger.info(f"Profile updated for user: {current_user['user_id']}")
        return UserResponse(**{k: v for k, v in user_record.items() if k != "hashed_password"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@auth_router.post("/logout")
async def logout_user(current_user: dict = Depends(get_current_user)):
    """Logout user - track cart abandonment if items in cart"""
    user_id = current_user['user_id']
    
    # Check if user has items in cart (cart abandonment detection)
    # Cart items are stored in realtime features when added to cart
    try:
        # Get cart items from realtime features (stored when items were added)
        realtime_key = f"{user_id}_realtime"
        cart_items = []
        cart_no_buy = False
        current_count = 0
        
        # Check if database client is connected
        if not database_manager.client:
            logger.error(f"🔍 DEBUG: Database client not connected - cannot retrieve cart items")
        else:
            try:
                key_tuple = (database_manager.namespace, "user_features", realtime_key)
                (key, metadata, bins) = database_manager.client.get(key_tuple)
                
                logger.info(f"🔍 DEBUG: Retrieved bins for {user_id}: {type(bins)} - {bins}")
                
                if bins:
                    # Data is wrapped in 'data' bin
                    realtime_data = bins.get('data', bins)  # Try 'data' bin first, fallback to bins directly
                    logger.info(f"🔍 DEBUG: Realtime data keys: {list(realtime_data.keys()) if isinstance(realtime_data, dict) else 'Not a dict'}")
                    
                    if isinstance(realtime_data, dict):
                        cart_items = realtime_data.get('cart_items', [])
                        cart_no_buy = realtime_data.get('cart_no_buy', False)
                        current_count = realtime_data.get('abandon_count', 0)
                        logger.info(f"🔍 DEBUG: cart_items={len(cart_items) if cart_items else 0} items, cart_no_buy={cart_no_buy}, abandon_count={current_count}")
                else:
                    logger.warning(f"🔍 DEBUG: bins is None for {user_id}")
                    
            except aerospike.exception.RecordNotFound:
                logger.info(f"🔍 DEBUG: No realtime features record found for {user_id}")
            except Exception as e:
                logger.error(f"🔍 DEBUG: Exception retrieving realtime features: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Check if user has cart items or cart_no_buy flag is set
        if (cart_items and len(cart_items) > 0) or cart_no_buy:
            # User has items in cart - increment abandonment counter
            items_count = len(cart_items) if cart_items else 1
            logger.warning(f"🛒 Cart abandonment detected for {user_id}: {items_count} items in cart")
            
            # Increment counter
            new_count = current_count + 1
            
            # Store updated counter in realtime features
            abandon_features = {
                "user_id": user_id,
                "abandon_count": new_count,
                "last_abandon_at": datetime.utcnow().isoformat(),
                "cart_item_cnt": items_count  # Shortened to fit 15-char limit
            }
            
            # Send to RecoEngine
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{RECO_ENGINE_BASE_URL}/ingest/realtime",
                        json=abandon_features,
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        logger.info(f"✅ Tracked cart abandonment #{new_count} for user {user_id}")
                    else:
                        logger.error(f"Failed to ingest abandonment count: {response.status_code}")
                except Exception as e:
                    logger.error(f"Failed to track abandonment count: {e}")
        else:
            logger.info(f"No cart items for {user_id} - no abandonment tracked")
    
    except Exception as e:
        logger.error(f"Error checking cart abandonment on logout: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    logger.info(f"User logged out: {user_id}")
    return {"message": "Successfully logged out"}
