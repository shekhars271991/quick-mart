"""
Product data models
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class Category(BaseModel):
    """Product category model"""
    category_id: str
    name: str
    description: Optional[str] = None
    parent_category: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0

class ProductCreate(BaseModel):
    """Product creation model"""
    name: str
    description: str
    category: str
    subcategory: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    brand: str
    images: List[str] = []
    specifications: Dict[str, Any] = {}
    stock_quantity: int = 0
    tags: List[str] = []
    is_featured: bool = False

class Product(BaseModel):
    """Product model"""
    product_id: str
    name: str
    description: str
    category: str
    subcategory: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    discount_percentage: float = 0
    brand: str
    image: Optional[str] = None  # Single image for backward compat
    images: List[str] = []
    specifications: Dict[str, Any] = {}
    stock_quantity: int = 0
    rating: float = 0.0
    review_count: int = 0
    tags: List[str] = []
    is_featured: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    embedding_text: Optional[str] = None  # For vector search
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ProductFilter(BaseModel):
    """Product filtering model"""
    category: Optional[str] = None
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    is_featured: Optional[bool] = None
    search: Optional[str] = None
    tags: Optional[List[str]] = None

class ProductResponse(BaseModel):
    """Product list response model"""
    products: List[Product]
    total: int
    page: int
    limit: int
    has_next: bool
