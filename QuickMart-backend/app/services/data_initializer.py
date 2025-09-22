"""
Data initialization service for QuickMart Backend
Loads test data on application startup from JSON files
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from faker import Faker

from core.database import database_manager
from core.auth import auth_manager
from models.product import Product, Category
from models.coupon import Coupon, DiscountType
from models.user import User, UserProfile, UserPreferences

logger = logging.getLogger(__name__)
fake = Faker()

class DataInitializer:
    """Service to initialize test data"""
    
    def __init__(self):
        # Get the directory where this file is located
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        # Data directory is relative to the backend root
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(self.current_dir)), "data")
        
    def _load_json_data(self, filename: str) -> List[Dict[str, Any]]:
        """Load data from JSON file"""
        file_path = os.path.join(self.data_dir, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} items from {filename}")
                return data
        except FileNotFoundError:
            logger.error(f"Data file not found: {file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            raise
    
    async def initialize_on_startup(self):
        """Initialize data on application startup if database is empty"""
        try:
            # Check if data already exists
            if not await self._is_database_empty():
                logger.info("Database already contains data, skipping initialization")
                return
            
            logger.info("Database is empty, initializing test data...")
            
            # Initialize data in order
            await self._load_categories()
            await self._load_products()
            await self._load_available_coupons()
            await self._load_test_users()
            
            logger.info("✅ Test data initialization completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Data initialization failed: {e}")
            raise
    
    async def _is_database_empty(self) -> bool:
        """Check if database is empty"""
        try:
            product_count = await database_manager.count_records("products")
            user_count = await database_manager.count_records("users")
            return product_count == 0 and user_count == 0
        except Exception as e:
            logger.error(f"Error checking database status: {e}")
            return True
    
    async def _load_categories(self):
        """Load product categories"""
        logger.info("Loading categories...")
        
        categories_data = self._load_json_data("categories.json")
        
        for cat_data in categories_data:
            category = Category(
                category_id=cat_data["category_id"],
                name=cat_data["name"],
                description=cat_data["description"],
                is_active=True,
                sort_order=0
            )
            
            await database_manager.put("categories", category.category_id, category.dict())
        
        logger.info(f"Loaded {len(categories_data)} categories")
    
    async def _load_products(self):
        """Load test products"""
        logger.info("Loading products...")
        
        products_data = self._load_json_data("products.json")
        
        for i, product_data in enumerate(products_data):
            product_id = f"prod_{str(i+1).zfill(3)}"
            
            # Calculate discount percentage
            discount_percentage = 0
            if product_data.get("original_price"):
                discount_percentage = round(
                    ((product_data["original_price"] - product_data["price"]) / product_data["original_price"]) * 100, 1
                )
            
            product = Product(
                product_id=product_id,
                name=product_data["name"],
                description=product_data["description"],
                category=product_data["category"],
                subcategory=product_data.get("subcategory"),
                price=product_data["price"],
                original_price=product_data.get("original_price"),
                discount_percentage=discount_percentage,
                brand=product_data["brand"],
                images=[f"{product_id}_1.jpg", f"{product_id}_2.jpg"],
                specifications=product_data.get("specifications", {}),
                stock_quantity=product_data["stock_quantity"],
                rating=product_data.get("rating", 0.0),
                review_count=product_data.get("review_count", 0),
                tags=product_data.get("tags", []),
                is_featured=product_data.get("is_featured", False),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            await database_manager.put("products", product_id, product.dict())
        
        logger.info(f"Loaded {len(products_data)} products")
    
    async def _load_available_coupons(self):
        """Load available coupons"""
        logger.info("Loading available coupons...")
        
        coupons_data = self._load_json_data("coupons.json")
        
        for i, coupon_data in enumerate(coupons_data):
            coupon_id = f"coup_{str(i+1).zfill(3)}"
            
            valid_from = datetime.utcnow()
            valid_until = valid_from + timedelta(days=coupon_data["days_valid"])
            
            # Convert string discount_type to enum
            discount_type_map = {
                "percentage": DiscountType.PERCENTAGE,
                "fixed": DiscountType.FIXED,
                "free_shipping": DiscountType.FREE_SHIPPING
            }
            discount_type = discount_type_map.get(coupon_data["discount_type"], DiscountType.PERCENTAGE)
            
            coupon = Coupon(
                coupon_id=coupon_id,
                code=coupon_data["code"],
                name=coupon_data["name"],
                description=coupon_data["description"],
                discount_type=discount_type,
                discount_value=coupon_data["discount_value"],
                minimum_order_value=coupon_data["minimum_order_value"],
                maximum_discount=coupon_data.get("maximum_discount"),
                usage_limit=coupon_data["usage_limit"],
                usage_count=0,
                valid_from=valid_from,
                valid_until=valid_until,
                is_active=True,
                applicable_categories=coupon_data.get("categories", []),
                applicable_products=[],
                created_at=datetime.utcnow()
            )
            
            await database_manager.put("coupons", coupon_id, coupon.dict())
        
        logger.info(f"Loaded {len(coupons_data)} coupons")
    
    async def _load_test_users(self):
        """Load test users"""
        logger.info("Loading test users...")
        
        test_users = self._load_json_data("users.json")
        
        for i, user_data in enumerate(test_users):
            user_id = f"user_{str(i+1).zfill(3)}"
            
            # Hash the password (using email prefix as password for demo)
            password = user_data["email"].split("@")[0]  # e.g., "john.doe"
            hashed_password = auth_manager.hash_password(password)
            
            user = User(
                user_id=user_id,
                email=user_data["email"],
                profile=UserProfile(
                    name=user_data["name"],
                    age=user_data["age"],
                    location=user_data["location"],
                    loyalty_tier=user_data["loyalty_tier"]
                ),
                preferences=UserPreferences(
                    categories=user_data["categories"],
                    brands=user_data["brands"],
                    price_range={"min": 0, "max": 1000}
                ),
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            # Store user data with hashed password
            user_data_with_password = user.dict()
            user_data_with_password["hashed_password"] = hashed_password
            
            await database_manager.put("users", user_id, user_data_with_password)
        
        logger.info(f"Loaded {len(test_users)} test users")
        logger.info("Test user credentials (email:password):")
        for user_data in test_users:
            password = user_data["email"].split("@")[0]
            logger.info(f"  {user_data['email']}:{password}")
    
    async def reset_all_data(self):
        """Reset all test data (for admin use)"""
        logger.info("Resetting all test data...")
        
        # This would require scanning and deleting all records
        # For now, we'll just log the action
        logger.warning("Data reset not implemented - requires manual database cleanup")
        
        return {"message": "Data reset requested - manual cleanup required"}
