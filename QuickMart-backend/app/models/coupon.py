"""
Coupon data models
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class DiscountType(str, Enum):
    """Discount type enumeration"""
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    FREE_SHIPPING = "free_shipping"

class CouponStatus(str, Enum):
    """Coupon status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"

class UserCouponStatus(str, Enum):
    """User coupon status enumeration"""
    AVAILABLE = "available"
    USED = "used"
    EXPIRED = "expired"

class CouponSource(str, Enum):
    """Coupon source enumeration"""
    NUDGE = "nudge"
    GENERAL = "general"
    PROMOTION = "promotion"

class CouponCreate(BaseModel):
    """Coupon creation model"""
    code: str
    name: str
    description: str
    discount_type: DiscountType
    discount_value: float
    min_order_val: float = 0
    max_discount: Optional[float] = None
    usage_limit: Optional[int] = None
    valid_from: datetime
    valid_until: datetime
    applicable_categories: List[str] = []
    applicable_products: List[str] = []

class Coupon(BaseModel):
    """Coupon model"""
    coupon_id: str
    code: str
    name: str
    description: str
    discount_type: DiscountType
    discount_value: float
    min_order_val: float = 0
    max_discount: Optional[float] = None
    usage_limit: Optional[int] = None
    usage_count: int = 0
    valid_from: datetime
    valid_until: datetime
    is_active: bool = True
    applicable_categories: List[str] = []
    applicable_products: List[str] = []
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserCoupon(BaseModel):
    """User-specific coupon model"""
    user_coupon_id: str
    user_id: str
    coupon_id: str
    source: CouponSource
    nudge_id: Optional[str] = None
    churn_score: Optional[float] = None
    status: UserCouponStatus = UserCouponStatus.AVAILABLE
    assigned_at: datetime
    used_at: Optional[datetime] = None
    order_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserCouponWithDetails(BaseModel):
    """User coupon with full coupon details"""
    user_coupon: UserCoupon
    coupon: Coupon

class CouponValidation(BaseModel):
    """Coupon validation result"""
    is_valid: bool
    message: str
    discount_amount: Optional[float] = None
    final_amount: Optional[float] = None
