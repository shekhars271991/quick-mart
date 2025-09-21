"""
Data initialization service for QuickMart Backend
Loads test data on application startup
"""

import logging
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
        self.categories_data = [
            {"category_id": "electronics", "name": "Electronics", "description": "Electronic devices and gadgets"},
            {"category_id": "clothing", "name": "Clothing", "description": "Fashion and apparel"},
            {"category_id": "home_garden", "name": "Home & Garden", "description": "Home improvement and garden supplies"},
            {"category_id": "books_media", "name": "Books & Media", "description": "Books, movies, and entertainment"},
            {"category_id": "sports_fitness", "name": "Sports & Fitness", "description": "Sports equipment and fitness gear"}
        ]
    
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
        
        for cat_data in self.categories_data:
            category = Category(
                category_id=cat_data["category_id"],
                name=cat_data["name"],
                description=cat_data["description"],
                is_active=True,
                sort_order=0
            )
            
            await database_manager.put("categories", category.category_id, category.dict())
        
        logger.info(f"Loaded {len(self.categories_data)} categories")
    
    async def _load_products(self):
        """Load test products"""
        logger.info("Loading products...")
        
        products_data = [
            # Electronics
            {
                "name": "iPhone 15 Pro", "category": "electronics", "subcategory": "smartphones",
                "price": 999.99, "original_price": 1099.99, "brand": "Apple",
                "description": "Latest iPhone with advanced camera system and A17 Pro chip",
                "specifications": {"storage": "128GB", "color": "Natural Titanium", "display": "6.1-inch"},
                "stock_quantity": 50, "rating": 4.8, "review_count": 1250,
                "tags": ["smartphone", "apple", "premium", "5g"], "is_featured": True
            },
            {
                "name": "Samsung Galaxy S24", "category": "electronics", "subcategory": "smartphones",
                "price": 899.99, "original_price": 999.99, "brand": "Samsung",
                "description": "Flagship Android phone with AI-powered features",
                "specifications": {"storage": "256GB", "color": "Phantom Black", "display": "6.2-inch"},
                "stock_quantity": 75, "rating": 4.6, "review_count": 890,
                "tags": ["smartphone", "samsung", "android", "ai"], "is_featured": True
            },
            {
                "name": "MacBook Air M3", "category": "electronics", "subcategory": "laptops",
                "price": 1299.99, "brand": "Apple",
                "description": "Ultra-thin laptop with M3 chip for exceptional performance",
                "specifications": {"processor": "M3", "memory": "8GB", "storage": "256GB SSD"},
                "stock_quantity": 30, "rating": 4.9, "review_count": 567,
                "tags": ["laptop", "apple", "m3", "ultrabook"], "is_featured": True
            },
            {
                "name": "Sony WH-1000XM5", "category": "electronics", "subcategory": "headphones",
                "price": 349.99, "original_price": 399.99, "brand": "Sony",
                "description": "Industry-leading noise canceling wireless headphones",
                "specifications": {"type": "Over-ear", "battery": "30 hours", "connectivity": "Bluetooth 5.2"},
                "stock_quantity": 100, "rating": 4.7, "review_count": 2340,
                "tags": ["headphones", "sony", "noise-canceling", "wireless"]
            },
            
            # Clothing
            {
                "name": "Nike Air Max 270", "category": "clothing", "subcategory": "shoes",
                "price": 129.99, "original_price": 149.99, "brand": "Nike",
                "description": "Comfortable running shoes with Max Air unit",
                "specifications": {"size_range": "6-13", "color": "Black/White", "material": "Mesh upper"},
                "stock_quantity": 200, "rating": 4.4, "review_count": 1890,
                "tags": ["shoes", "nike", "running", "comfortable"]
            },
            {
                "name": "Levi's 501 Original Jeans", "category": "clothing", "subcategory": "jeans",
                "price": 79.99, "brand": "Levi's",
                "description": "Classic straight-leg jeans with authentic fit",
                "specifications": {"fit": "Straight", "material": "100% Cotton", "wash": "Medium Blue"},
                "stock_quantity": 150, "rating": 4.5, "review_count": 3456,
                "tags": ["jeans", "levis", "classic", "denim"]
            },
            
            # Home & Garden
            {
                "name": "Instant Pot Duo 7-in-1", "category": "home_garden", "subcategory": "kitchen",
                "price": 89.99, "original_price": 119.99, "brand": "Instant Pot",
                "description": "Multi-functional electric pressure cooker",
                "specifications": {"capacity": "6 quarts", "functions": "7-in-1", "material": "Stainless steel"},
                "stock_quantity": 80, "rating": 4.6, "review_count": 12000,
                "tags": ["kitchen", "pressure-cooker", "instant-pot", "cooking"], "is_featured": True
            },
            {
                "name": "Dyson V15 Detect", "category": "home_garden", "subcategory": "cleaning",
                "price": 649.99, "brand": "Dyson",
                "description": "Cordless vacuum with laser dust detection",
                "specifications": {"type": "Cordless", "runtime": "60 minutes", "filtration": "HEPA"},
                "stock_quantity": 45, "rating": 4.8, "review_count": 789,
                "tags": ["vacuum", "dyson", "cordless", "laser-detection"]
            },
            
            # Books & Media
            {
                "name": "The Psychology of Money", "category": "books_media", "subcategory": "books",
                "price": 14.99, "brand": "Harriman House",
                "description": "Timeless lessons on wealth, greed, and happiness by Morgan Housel",
                "specifications": {"pages": "256", "format": "Paperback", "language": "English"},
                "stock_quantity": 300, "rating": 4.7, "review_count": 5670,
                "tags": ["book", "finance", "psychology", "bestseller"]
            },
            
            # Sports & Fitness
            {
                "name": "Peloton Bike+", "category": "sports_fitness", "subcategory": "exercise",
                "price": 2495.00, "brand": "Peloton",
                "description": "Premium indoor cycling bike with rotating touchscreen",
                "specifications": {"screen": "23.8-inch HD", "resistance": "Magnetic", "weight": "140 lbs"},
                "stock_quantity": 15, "rating": 4.3, "review_count": 234,
                "tags": ["exercise-bike", "peloton", "fitness", "premium"], "is_featured": True
            }
        ]
        
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
        
        coupons_data = [
            {
                "code": "WELCOME10", "name": "Welcome Discount", 
                "description": "10% off your first order",
                "discount_type": DiscountType.PERCENTAGE, "discount_value": 10,
                "minimum_order_value": 50, "maximum_discount": 100,
                "usage_limit": 1000, "days_valid": 365
            },
            {
                "code": "SAVE20", "name": "Save $20", 
                "description": "$20 off orders over $100",
                "discount_type": DiscountType.FIXED, "discount_value": 20,
                "minimum_order_value": 100, "usage_limit": 500, "days_valid": 90
            },
            {
                "code": "FREESHIP", "name": "Free Shipping", 
                "description": "Free shipping on any order",
                "discount_type": DiscountType.FREE_SHIPPING, "discount_value": 0,
                "minimum_order_value": 25, "usage_limit": 2000, "days_valid": 180
            },
            {
                "code": "ELECTRONICS15", "name": "Electronics Sale", 
                "description": "15% off electronics",
                "discount_type": DiscountType.PERCENTAGE, "discount_value": 15,
                "minimum_order_value": 200, "maximum_discount": 150,
                "usage_limit": 300, "days_valid": 30, "categories": ["electronics"]
            },
            {
                "code": "SUMMER25", "name": "Summer Sale", 
                "description": "25% off summer collection",
                "discount_type": DiscountType.PERCENTAGE, "discount_value": 25,
                "minimum_order_value": 75, "maximum_discount": 200,
                "usage_limit": 1000, "days_valid": 60, "categories": ["clothing", "sports_fitness"]
            }
        ]
        
        for i, coupon_data in enumerate(coupons_data):
            coupon_id = f"coup_{str(i+1).zfill(3)}"
            
            valid_from = datetime.utcnow()
            valid_until = valid_from + timedelta(days=coupon_data["days_valid"])
            
            coupon = Coupon(
                coupon_id=coupon_id,
                code=coupon_data["code"],
                name=coupon_data["name"],
                description=coupon_data["description"],
                discount_type=coupon_data["discount_type"],
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
        
        test_users = [
            {
                "email": "john.doe@example.com", "name": "John Doe", "age": 28,
                "location": "New York, NY", "loyalty_tier": "gold",
                "categories": ["electronics", "books_media"], "brands": ["Apple", "Samsung"]
            },
            {
                "email": "jane.smith@example.com", "name": "Jane Smith", "age": 34,
                "location": "Los Angeles, CA", "loyalty_tier": "platinum",
                "categories": ["clothing", "home_garden"], "brands": ["Nike", "Dyson"]
            },
            {
                "email": "mike.johnson@example.com", "name": "Mike Johnson", "age": 22,
                "location": "Chicago, IL", "loyalty_tier": "bronze",
                "categories": ["sports_fitness", "electronics"], "brands": ["Peloton", "Sony"]
            },
            {
                "email": "sarah.wilson@example.com", "name": "Sarah Wilson", "age": 45,
                "location": "Houston, TX", "loyalty_tier": "silver",
                "categories": ["home_garden", "books_media"], "brands": ["Instant Pot", "Levi's"]
            },
            {
                "email": "demo@quickmart.com", "name": "Demo User", "age": 30,
                "location": "San Francisco, CA", "loyalty_tier": "gold",
                "categories": ["electronics", "clothing"], "brands": ["Apple", "Nike"]
            }
        ]
        
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
