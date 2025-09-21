"""
User data models
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime

class UserProfile(BaseModel):
    """User profile information"""
    name: str
    age: Optional[int] = None
    location: Optional[str] = None
    loyalty_tier: str = "bronze"

class UserPreferences(BaseModel):
    """User preferences"""
    categories: List[str] = []
    brands: List[str] = []
    price_range: Dict[str, float] = {"min": 0, "max": 1000}

class UserCreate(BaseModel):
    """User creation model"""
    email: EmailStr
    password: str
    profile: UserProfile
    preferences: Optional[UserPreferences] = None

class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr
    password: str

class User(BaseModel):
    """User model"""
    user_id: str
    email: EmailStr
    profile: UserProfile
    preferences: UserPreferences
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserResponse(BaseModel):
    """User response model (without sensitive data)"""
    user_id: str
    email: EmailStr
    profile: UserProfile
    preferences: UserPreferences
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
