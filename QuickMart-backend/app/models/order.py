"""
Order data models
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class OrderItem(BaseModel):
    """Order item model"""
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float

class DiscountInfo(BaseModel):
    """Discount information"""
    coupon_id: Optional[str] = None
    coupon_code: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    discount_amount: float = 0

class OrderCreate(BaseModel):
    """Order creation model"""
    items: List[OrderItem]
    coupon_code: Optional[str] = None

class Order(BaseModel):
    """Order model"""
    order_id: str
    user_id: str
    items: List[OrderItem]
    subtotal: float
    discount_applied: Optional[DiscountInfo] = None
    total_amount: float
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
