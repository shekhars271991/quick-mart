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

from core.database import database_manager
from core.auth import auth_manager, get_current_user
from models.user import User, UserCreate, UserLogin, UserResponse, UserProfile, UserPreferences

logger = logging.getLogger(__name__)

auth_router = APIRouter()

# RecoEngine configuration
RECO_ENGINE_BASE_URL = os.getenv("RECO_ENGINE_URL", "http://localhost:8000")

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
        user_record = None
        
        for user in users:
            if user.get("email") == login_data.email:
                user_record = user
                break
        
        if not user_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not auth_manager.verify_password(login_data.password, user_record["hashed_password"]):
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
        
        # Trigger churn prediction and get result
        user_id = user_record["user_id"]
        churn_prediction = await trigger_churn_prediction(user_id)
        
        # Prepare response
        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse(**{k: v for k, v in user_record.items() if k != "hashed_password"})
        }
        
        # Add churn prediction info if available and nudges were triggered
        if churn_prediction and churn_prediction.get('nudges_triggered'):
            has_discount_coupon = any(
                nudge.get('type') == 'Discount Coupon' 
                for nudge in churn_prediction['nudges_triggered']
            )
            if has_discount_coupon:
                response_data["special_offer"] = {
                    "message": "Special offer just for you! Check your coupons for exclusive discounts.",
                    "type": "discount_coupon",
                    "risk_segment": churn_prediction.get('risk_segment', 'unknown')
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
    """Logout user (client should discard token)"""
    logger.info(f"User logged out: {current_user['user_id']}")
    return {"message": "Successfully logged out"}
