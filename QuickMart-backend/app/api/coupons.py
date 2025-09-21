"""
Coupon management API endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from datetime import datetime
import logging
import uuid

from core.database import database_manager
from core.auth import get_current_user, get_current_user_optional
from models.coupon import (
    Coupon, UserCoupon, UserCouponWithDetails, CouponValidation,
    CouponStatus, UserCouponStatus, CouponSource
)

logger = logging.getLogger(__name__)

coupons_router = APIRouter()

@coupons_router.get("/available", response_model=List[Coupon])
async def get_available_coupons(
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get all available coupons for general use"""
    try:
        coupons_data = await database_manager.scan_set("coupons")
        
        available_coupons = []
        current_time = datetime.utcnow()
        
        for coupon_data in coupons_data:
            try:
                coupon = Coupon(**coupon_data)
                
                # Check if coupon is active and valid
                if (coupon.is_active and 
                    coupon.valid_from <= current_time <= coupon.valid_until and
                    (coupon.usage_limit is None or coupon.usage_count < coupon.usage_limit)):
                    available_coupons.append(coupon)
                    
            except Exception as e:
                logger.warning(f"Failed to parse coupon {coupon_data.get('coupon_id')}: {e}")
                continue
        
        # Sort by discount value (highest first)
        available_coupons.sort(key=lambda x: x.discount_value, reverse=True)
        
        return available_coupons
        
    except Exception as e:
        logger.error(f"Error fetching available coupons: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch available coupons"
        )

@coupons_router.get("/user", response_model=List[UserCouponWithDetails])
async def get_user_coupons(current_user: dict = Depends(get_current_user)):
    """Get user-specific coupons (from nudges and assignments)"""
    try:
        # Get user coupons
        user_coupons_data = await database_manager.scan_set("user_coupons")
        user_coupons = []
        
        current_time = datetime.utcnow()
        
        for user_coupon_data in user_coupons_data:
            if user_coupon_data.get("user_id") == current_user["user_id"]:
                try:
                    user_coupon = UserCoupon(**user_coupon_data)
                    
                    # Only include available coupons
                    if user_coupon.status == UserCouponStatus.AVAILABLE:
                        # Get the associated coupon details
                        coupon_data = await database_manager.get("coupons", user_coupon.coupon_id)
                        if coupon_data:
                            coupon = Coupon(**coupon_data)
                            
                            # Check if coupon is still valid
                            if coupon.valid_until >= current_time:
                                user_coupons.append(UserCouponWithDetails(
                                    user_coupon=user_coupon,
                                    coupon=coupon
                                ))
                            else:
                                # Mark as expired
                                user_coupon_data["status"] = UserCouponStatus.EXPIRED
                                await database_manager.put("user_coupons", user_coupon.user_coupon_id, user_coupon_data)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse user coupon {user_coupon_data.get('user_coupon_id')}: {e}")
                    continue
        
        # Sort by assigned date (newest first)
        user_coupons.sort(key=lambda x: x.user_coupon.assigned_at, reverse=True)
        
        return user_coupons
        
    except Exception as e:
        logger.error(f"Error fetching user coupons: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user coupons"
        )

@coupons_router.post("/validate")
async def validate_coupon(
    coupon_code: str,
    order_total: float,
    current_user: dict = Depends(get_current_user)
) -> CouponValidation:
    """Validate a coupon code for the current user and order"""
    try:
        # First, try to find the coupon in general coupons
        coupons_data = await database_manager.scan_set("coupons")
        coupon = None
        
        for coupon_data in coupons_data:
            if coupon_data.get("code") == coupon_code:
                coupon = Coupon(**coupon_data)
                break
        
        if not coupon:
            return CouponValidation(
                is_valid=False,
                message="Coupon code not found"
            )
        
        current_time = datetime.utcnow()
        
        # Check if coupon is active
        if not coupon.is_active:
            return CouponValidation(
                is_valid=False,
                message="Coupon is not active"
            )
        
        # Check validity period
        if current_time < coupon.valid_from or current_time > coupon.valid_until:
            return CouponValidation(
                is_valid=False,
                message="Coupon has expired"
            )
        
        # Check usage limit
        if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
            return CouponValidation(
                is_valid=False,
                message="Coupon usage limit reached"
            )
        
        # Check minimum order value
        if order_total < coupon.minimum_order_value:
            return CouponValidation(
                is_valid=False,
                message=f"Minimum order value is ${coupon.minimum_order_value:.2f}"
            )
        
        # Calculate discount
        discount_amount = 0
        final_amount = order_total
        
        if coupon.discount_type == "percentage":
            discount_amount = order_total * (coupon.discount_value / 100)
            if coupon.maximum_discount:
                discount_amount = min(discount_amount, coupon.maximum_discount)
        elif coupon.discount_type == "fixed":
            discount_amount = min(coupon.discount_value, order_total)
        elif coupon.discount_type == "free_shipping":
            # For free shipping, we'll assume a fixed shipping cost
            discount_amount = 10.0  # Assume $10 shipping
        
        final_amount = max(0, order_total - discount_amount)
        
        return CouponValidation(
            is_valid=True,
            message="Coupon is valid",
            discount_amount=discount_amount,
            final_amount=final_amount
        )
        
    except Exception as e:
        logger.error(f"Error validating coupon {coupon_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate coupon"
        )

@coupons_router.post("/apply")
async def apply_coupon(
    coupon_code: str,
    order_total: float,
    current_user: dict = Depends(get_current_user)
):
    """Apply a coupon code (marks it as used)"""
    try:
        # First validate the coupon
        validation = await validate_coupon(coupon_code, order_total, current_user)
        
        if not validation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation.message
            )
        
        # Find the coupon
        coupons_data = await database_manager.scan_set("coupons")
        coupon_data = None
        
        for c_data in coupons_data:
            if c_data.get("code") == coupon_code:
                coupon_data = c_data
                break
        
        if not coupon_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coupon not found"
            )
        
        # Update usage count
        coupon_data["usage_count"] = coupon_data.get("usage_count", 0) + 1
        await database_manager.put("coupons", coupon_data["coupon_id"], coupon_data)
        
        # Check if this is a user-specific coupon and mark it as used
        user_coupons_data = await database_manager.scan_set("user_coupons")
        for user_coupon_data in user_coupons_data:
            if (user_coupon_data.get("user_id") == current_user["user_id"] and
                user_coupon_data.get("coupon_id") == coupon_data["coupon_id"] and
                user_coupon_data.get("status") == UserCouponStatus.AVAILABLE):
                
                user_coupon_data["status"] = UserCouponStatus.USED
                user_coupon_data["used_at"] = datetime.utcnow().isoformat()
                await database_manager.put("user_coupons", user_coupon_data["user_coupon_id"], user_coupon_data)
                break
        
        logger.info(f"Coupon {coupon_code} applied by user {current_user['user_id']}")
        
        return {
            "message": "Coupon applied successfully",
            "discount_amount": validation.discount_amount,
            "final_amount": validation.final_amount
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying coupon {coupon_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply coupon"
        )

@coupons_router.get("/history")
async def get_coupon_history(current_user: dict = Depends(get_current_user)):
    """Get user's coupon usage history"""
    try:
        user_coupons_data = await database_manager.scan_set("user_coupons")
        history = []
        
        for user_coupon_data in user_coupons_data:
            if user_coupon_data.get("user_id") == current_user["user_id"]:
                try:
                    user_coupon = UserCoupon(**user_coupon_data)
                    
                    # Get coupon details
                    coupon_data = await database_manager.get("coupons", user_coupon.coupon_id)
                    if coupon_data:
                        coupon = Coupon(**coupon_data)
                        history.append(UserCouponWithDetails(
                            user_coupon=user_coupon,
                            coupon=coupon
                        ))
                        
                except Exception as e:
                    logger.warning(f"Failed to parse coupon history item: {e}")
                    continue
        
        # Sort by assigned date (newest first)
        history.sort(key=lambda x: x.user_coupon.assigned_at, reverse=True)
        
        return history
        
    except Exception as e:
        logger.error(f"Error fetching coupon history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch coupon history"
        )

# Internal endpoint for creating user-specific coupons from nudges
@coupons_router.post("/internal/assign-nudge-coupon")
async def assign_nudge_coupon(
    user_id: str,
    coupon_id: str,
    nudge_id: str,
    churn_score: float
):
    """Internal endpoint to assign a coupon from a nudge (called by RecoEngine integration)"""
    try:
        # Create user-specific coupon
        user_coupon_id = f"uc_{uuid.uuid4().hex[:12]}"
        
        user_coupon = UserCoupon(
            user_coupon_id=user_coupon_id,
            user_id=user_id,
            coupon_id=coupon_id,
            source=CouponSource.NUDGE,
            nudge_id=nudge_id,
            churn_score=churn_score,
            status=UserCouponStatus.AVAILABLE,
            assigned_at=datetime.utcnow()
        )
        
        success = await database_manager.put("user_coupons", user_coupon_id, user_coupon.dict())
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign coupon"
            )
        
        logger.info(f"Nudge coupon {coupon_id} assigned to user {user_id}")
        return {"message": "Coupon assigned successfully", "user_coupon_id": user_coupon_id}
        
    except Exception as e:
        logger.error(f"Error assigning nudge coupon: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign coupon"
        )
