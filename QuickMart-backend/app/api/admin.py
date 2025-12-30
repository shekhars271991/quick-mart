"""
Admin API endpoints
"""

from fastapi import APIRouter, HTTPException, status
import logging
import json
import os
from pathlib import Path
from datetime import datetime
import httpx
import asyncio
import uuid

from core.database import database_manager
from core.auth import auth_manager
from models.product import Category, Product
from models.user import User, UserProfile, UserPreferences

logger = logging.getLogger(__name__)

admin_router = APIRouter()

# RecoEngine API configuration
RECO_ENGINE_BASE_URL = os.getenv("RECO_ENGINE_URL", "http://localhost:8001")

async def upload_user_features_to_reco_engine(user_id: str, features: dict):
    """Upload user features to RecoEngine API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            feature_types = ["profile", "behavior", "transactional", "engagement", "support", "realtime"]
            
            for feature_type in feature_types:
                if feature_type in features:
                    feature_data = features[feature_type].copy()
                    feature_data["user_id"] = user_id
                    
                    url = f"{RECO_ENGINE_BASE_URL}/ingest/{feature_type}"
                    response = await client.post(url, json=feature_data)
                    
                    if response.status_code != 200:
                        logger.warning(f"Failed to upload {feature_type} features for user {user_id}: {response.text}")
                        return False
                    else:
                        logger.info(f"Successfully uploaded {feature_type} features for user {user_id}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error uploading features for user {user_id}: {str(e)}")
        return False


@admin_router.post("/load-data")
async def load_all_data():
    """Load all data (categories, products, users) from JSON files into Aerospike"""
    try:
        # Get the data directory path
        current_dir = Path(__file__).parent
        backend_root = current_dir.parent.parent
        data_dir = backend_root / "data"
        
        results = {
            "message": "Data loading completed",
            "categories": {"loaded": 0, "total": 0, "success": False},
            "products": {"loaded": 0, "total": 0, "success": False},
            "users": {"loaded": 0, "total": 0, "success": False},
            "coupons": {"loaded": 0, "total": 0, "success": False},
            "errors": []
        }
        
        # Load Categories
        try:
            categories_file = data_dir / "categories.json"
            if categories_file.exists():
                with open(categories_file, 'r', encoding='utf-8') as f:
                    categories_data = json.load(f)
                
                logger.info(f"Loading {len(categories_data)} categories")
                loaded_categories = []
                
                for cat_data in categories_data:
                    category = Category(
                        category_id=cat_data["category_id"],
                        name=cat_data["name"],
                        description=cat_data.get("description"),
                        is_active=True,
                        sort_order=0
                    )
                    
                    success = await database_manager.put("categories", category.category_id, category.dict())
                    if success:
                        loaded_categories.append(category.category_id)
                
                results["categories"] = {
                    "loaded": len(loaded_categories),
                    "total": len(categories_data),
                    "success": True,
                    "items": loaded_categories
                }
                logger.info(f"✅ Loaded {len(loaded_categories)} categories")
            else:
                results["errors"].append("Categories file not found")
                
        except Exception as e:
            logger.error(f"Failed to load categories: {e}")
            results["errors"].append(f"Categories loading failed: {str(e)}")
        
        # Load Products - delegate to load_products() to use LangGraph Store
        try:
            products_result = await load_products()
            results["products"] = {
                "loaded": products_result.get("loaded_products", 0),
                "total": products_result.get("total_products", 0),
                "success": True,
                "items": products_result.get("products", []),
                "vector_index": products_result.get("vector_index")
            }
            logger.info(f"✅ Loaded products via load_products()")
        except Exception as e:
            logger.error(f"Failed to load products: {e}")
            results["errors"].append(f"Products loading failed: {str(e)}")
        
        # Load Users
        try:
            users_file = data_dir / "users.json"
            if users_file.exists():
                with open(users_file, 'r', encoding='utf-8') as f:
                    users_data = json.load(f)
                
                logger.info(f"Loading {len(users_data)} users")
                loaded_users = []
                
                for i, user_data in enumerate(users_data):
                    user_id = f"user_{str(i+1).zfill(3)}"
                    
                    # Hash the password (using default password for demo)
                    password = "admin"
                    logger.info(f"About to hash password: '{password}' (length: {len(password)})")
                    try:
                        hashed_password = auth_manager.hash_password(password)
                        logger.info(f"Successfully hashed password for user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to hash password for user {user_id}: {e}")
                        raise
                    
                    user = User(
                        user_id=user_id,
                        email=user_data["email"],
                        profile=UserProfile(
                            name=user_data["name"],
                            age=user_data.get("age"),
                            location=user_data.get("location"),
                            loyalty_tier=user_data.get("loyalty_tier", "bronze")
                        ),
                        preferences=UserPreferences(
                            categories=user_data.get("categories", []),
                            brands=user_data.get("brands", []),
                            price_range={"min": 0, "max": 1000}
                        ),
                        created_at=datetime.utcnow(),
                        is_active=True
                    )
                    
                    # Store user data with hashed password
                    user_data_with_password = user.dict()
                    user_data_with_password["hashed_password"] = hashed_password
                    
                    success = await database_manager.put("users", user_id, user_data_with_password)
                    if success:
                        # Upload features to RecoEngine if they exist
                        if "features" in user_data:
                            feature_upload_success = await upload_user_features_to_reco_engine(user_id, user_data["features"])
                            if not feature_upload_success:
                                logger.warning(f"Failed to upload features for user {user_id}")
                        
                        loaded_users.append({
                            "user_id": user_id,
                            "email": user_data["email"],
                            "password": password
                        })
                
                results["users"] = {
                    "loaded": len(loaded_users),
                    "total": len(users_data),
                    "success": True,
                    "items": loaded_users
                }
                logger.info(f"✅ Loaded {len(loaded_users)} users")
            else:
                results["errors"].append("Users file not found")
                
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
            results["errors"].append(f"Users loading failed: {str(e)}")
        
        # Load Coupons
        try:
            coupons_file = data_dir / "coupons.json"
            if coupons_file.exists():
                with open(coupons_file, 'r', encoding='utf-8') as f:
                    coupons_data = json.load(f)
                
                logger.info(f"Loading {len(coupons_data)} coupons")
                loaded_coupons = []
                
                # Import here to avoid circular imports
                from models.coupon import Coupon
                from datetime import timedelta
                
                for coupon_data in coupons_data:
                    # Generate unique coupon ID
                    coupon_id = f"coupon_{uuid.uuid4().hex[:12]}"
                    
                    # Calculate valid dates
                    valid_from = datetime.utcnow()
                    valid_until = valid_from + timedelta(days=coupon_data.get("days_valid", 30))
                    
                    coupon = Coupon(
                        coupon_id=coupon_id,
                        code=coupon_data["code"],
                        name=coupon_data["name"],
                        description=coupon_data.get("description", ""),
                        discount_type=coupon_data["discount_type"],
                        discount_value=coupon_data["discount_value"],
                        min_order_val=coupon_data.get("min_order_val", 0.0),
                        max_discount=coupon_data.get("max_discount"),
                        usage_limit=coupon_data.get("usage_limit", 1),
                        usage_count=0,
                        valid_from=valid_from,
                        valid_until=valid_until,
                        is_active=True,
                        applicable_categories=coupon_data.get("categories", []),
                        applicable_products=coupon_data.get("applicable_products", []),
                        created_at=datetime.utcnow()
                    )
                    
                    success = await database_manager.store_coupon(coupon)
                    if success:
                        loaded_coupons.append(coupon.code)
                
                results["coupons"] = {
                    "loaded": len(loaded_coupons),
                    "total": len(coupons_data),
                    "success": True,
                    "items": loaded_coupons
                }
                logger.info(f"✅ Loaded {len(loaded_coupons)} coupons")
            else:
                results["errors"].append("Coupons file not found")
                
        except Exception as e:
            logger.error(f"Failed to load coupons: {e}")
            results["errors"].append(f"Coupons loading failed: {str(e)}")
        
        # Determine overall success
        successful_loads = sum([
            results["categories"]["success"],
            results["products"]["success"], 
            results["users"]["success"],
            results["coupons"]["success"]
        ])
        
        if successful_loads == 4:
            results["message"] = "🎉 All data loaded successfully!"
            results["status"] = "complete"
        elif successful_loads > 0:
            results["message"] = f"⚠️ Partial success: {successful_loads}/4 data types loaded"
            results["status"] = "partial"
        else:
            results["message"] = "❌ Failed to load any data"
            results["status"] = "failed"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load any data"
            )
        
        # Add summary
        total_loaded = (
            results["categories"]["loaded"] + 
            results["products"]["loaded"] + 
            results["users"]["loaded"] +
            results["coupons"]["loaded"]
        )
        results["summary"] = {
            "total_items_loaded": total_loaded,
            "categories_loaded": results["categories"]["loaded"],
            "products_loaded": results["products"]["loaded"],
            "users_loaded": results["users"]["loaded"],
            "coupons_loaded": results["coupons"]["loaded"]
        }
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Critical error in load_all_data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Critical error during data loading: {str(e)}"
        )


@admin_router.post("/load-categories")
async def load_categories():
    """Load categories from categories.json into Aerospike"""
    try:
        # Get the data directory path
        current_dir = Path(__file__).parent
        backend_root = current_dir.parent.parent
        data_file = backend_root / "data" / "categories.json"
        
        
        if not data_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Categories file not found: {data_file}"
            )
        
        # Load categories from JSON file
        with open(data_file, 'r', encoding='utf-8') as f:
            categories_data = json.load(f)
        
        logger.info(f"Loading {len(categories_data)} categories from {data_file}")
        
        # Insert each category into Aerospike
        loaded_categories = []
        for cat_data in categories_data:
            # Create Category model instance
            category = Category(
                category_id=cat_data["category_id"],
                name=cat_data["name"],
                description=cat_data.get("description"),
                is_active=True,
                sort_order=0
            )
            
            # Store in Aerospike
            success = await database_manager.put("categories", category.category_id, category.dict())
            if success:
                loaded_categories.append(category.category_id)
                logger.info(f"Loaded category: {category.category_id}")
            else:
                logger.error(f"Failed to load category: {category.category_id}")
        
        return {
            "message": "Categories loaded successfully",
            "total_categories": len(categories_data),
            "loaded_categories": len(loaded_categories),
            "categories": loaded_categories
        }
        
    except FileNotFoundError:
        logger.error(f"Categories file not found: {data_file}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categories file not found"
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in categories file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON in categories file: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to load categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load categories: {str(e)}"
        )


@admin_router.post("/load-products")
async def load_products():
    """Load products from products.json into Aerospike"""
    try:
        # Get the data directory path
        current_dir = Path(__file__).parent
        backend_root = current_dir.parent.parent
        data_file = backend_root / "data" / "products.json"
        
        if not data_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Products file not found: {data_file}"
            )
        
        # Load products from JSON file
        with open(data_file, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
        
        logger.info(f"Loading {len(products_data)} products from {data_file}")
        
        # Insert each product into Aerospike
        loaded_products = []
        for i, product_data in enumerate(products_data):
            product_id = f"prod_{str(i+1).zfill(3)}"
            
            # Calculate discount percentage
            discount_percentage = 0
            if product_data.get("original_price"):
                discount_percentage = round(
                    ((product_data["original_price"] - product_data["price"]) / product_data["original_price"]) * 100, 1
                )
            
            # Create Product model instance
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
                images=[product_data["image"]] if product_data.get("image") else [],
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
            
            # Products are stored via RecoEngine in LangGraph Store format
            # (with embeddings for vector search)
            loaded_products.append(product_id)
            logger.info(f"Prepared product: {product_id}")
        
        # Store products in RecoEngine (LangGraph Store with embeddings)
        # This is the single source of truth for products
        index_result = None
        try:
            # Prepare products for RecoEngine with all fields needed
            products_for_indexing = []
            for i, product_data in enumerate(products_data):
                product_id = f"prod_{str(i+1).zfill(3)}"
                
                # Calculate discount percentage if we have original_price
                discount_percentage = 0
                if product_data.get("original_price") and product_data.get("original_price") > product_data["price"]:
                    discount_percentage = round(
                        ((product_data["original_price"] - product_data["price"]) / product_data["original_price"]) * 100
                    )
                
                products_for_indexing.append({
                    "product_id": product_id,
                    "name": product_data["name"],
                    "description": product_data["description"],
                    "category": product_data["category"],
                    "subcategory": product_data.get("subcategory"),
                    "brand": product_data["brand"],
                    "price": product_data["price"],
                    "original_price": product_data.get("original_price"),
                    "discount_percentage": discount_percentage,
                    "rating": product_data.get("rating", 0.0),
                    "review_count": product_data.get("review_count", 0),
                    "stock_quantity": product_data["stock_quantity"],
                    "tags": product_data.get("tags", []),
                    "image": product_data.get("image"),
                    "images": [product_data["image"]] if product_data.get("image") else [],
                    "specifications": product_data.get("specifications", {}),
                    "is_featured": product_data.get("is_featured", False),
                    "is_active": True
                })
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{RECO_ENGINE_BASE_URL}/recommendations/index",
                    json={"products": products_for_indexing}
                )
                if response.status_code == 200:
                    index_result = response.json()
                    logger.info(f"✅ Products stored in LangGraph Store: {index_result.get('products_indexed', 0)} products")
                else:
                    logger.warning(f"⚠️ Product storage returned {response.status_code}: {response.text}")
        except Exception as e:
            logger.warning(f"⚠️ Could not store products: {e}")
        
        return {
            "message": "Products loaded successfully",
            "total_products": len(products_data),
            "loaded_products": len(loaded_products),
            "products": loaded_products,
            "vector_index": index_result
        }
        
    except FileNotFoundError:
        logger.error(f"Products file not found: {data_file}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Products file not found"
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in products file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON in products file: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to load products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load products: {str(e)}"
        )


@admin_router.get("/products")
async def get_products():
    """Get all products from LangGraph Store"""
    try:
        # Read from LangGraph Store format (products namespace)
        products = await database_manager.scan_store_set("products", "products")
        return {
            "message": "Products retrieved successfully",
            "count": len(products),
            "products": products
        }
    except Exception as e:
        logger.error(f"Failed to retrieve products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve products: {str(e)}"
        )


@admin_router.post("/load-users")
async def load_users():
    """Load users from users.json into Aerospike"""
    try:
        # Get the data directory path
        current_dir = Path(__file__).parent
        backend_root = current_dir.parent.parent
        data_file = backend_root / "data" / "users.json"
        
        if not data_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Users file not found: {data_file}"
            )
        
        # Load users from JSON file
        with open(data_file, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        
        logger.info(f"Loading {len(users_data)} users from {data_file}")
        
        # Insert each user into Aerospike
        loaded_users = []
        for i, user_data in enumerate(users_data):
            user_id = f"user_{str(i+1).zfill(3)}"
            
            # Hash the password (using default password for demo)
            password = "admin"
            hashed_password = auth_manager.hash_password(password)
            
            # Create User model instance
            user = User(
                user_id=user_id,
                email=user_data["email"],
                profile=UserProfile(
                    name=user_data["name"],
                    age=user_data.get("age"),
                    location=user_data.get("location"),
                    loyalty_tier=user_data.get("loyalty_tier", "bronze")
                ),
                preferences=UserPreferences(
                    categories=user_data.get("categories", []),
                    brands=user_data.get("brands", []),
                    price_range={"min": 0, "max": 1000}
                ),
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            # Store user data with hashed password
            user_data_with_password = user.dict()
            user_data_with_password["hashed_password"] = hashed_password
            
            # Store in Aerospike
            try:
                success = await database_manager.put("users", user_id, user_data_with_password)
                if success:
                    # Upload features to RecoEngine if they exist (don't block on this)
                    if "features" in user_data:
                        try:
                            feature_upload_success = await upload_user_features_to_reco_engine(user_id, user_data["features"])
                            if not feature_upload_success:
                                logger.warning(f"Failed to upload features for user {user_id}")
                        except Exception as e:
                            logger.warning(f"Exception uploading features for user {user_id}: {e}")
                    
                    loaded_users.append({
                        "user_id": user_id,
                        "email": user_data["email"],
                        "password": password  # Include demo password in response
                    })
                    logger.info(f"✅ Loaded user: {user_id} ({user_data['email']})")
                else:
                    logger.error(f"❌ Failed to store user {user_id} in database")
            except Exception as e:
                logger.error(f"❌ Exception while storing user {user_id}: {e}", exc_info=True)
        
        return {
            "message": "Users loaded successfully",
            "total_users": len(users_data),
            "loaded_users": len(loaded_users),
            "users": loaded_users,
            "note": "All demo users have the default password: admin"
        }
        
    except FileNotFoundError:
        logger.error(f"Users file not found: {data_file}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Users file not found"
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in users file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON in users file: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to load users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load users: {str(e)}"
        )


@admin_router.get("/users")
async def get_users():
    """Get all users from Aerospike (without passwords)"""
    try:
        users = await database_manager.scan_set("users")
        
        # Remove hashed_password from response for security
        safe_users = []
        for user in users:
            if isinstance(user, dict) and "hashed_password" in user:
                safe_user = {k: v for k, v in user.items() if k != "hashed_password"}
                safe_users.append(safe_user)
            else:
                safe_users.append(user)
        
        return {
            "message": "Users retrieved successfully",
            "count": len(safe_users),
            "users": safe_users
        }
    except Exception as e:
        logger.error(f"Failed to retrieve users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}"
        )


@admin_router.get("/categories")
async def get_categories():
    """Get all categories from Aerospike"""
    try:
        categories = await database_manager.scan_set("categories")
        return {
            "message": "Categories retrieved successfully",
            "count": len(categories),
            "categories": categories
        }
    except Exception as e:
        logger.error(f"Failed to retrieve categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve categories: {str(e)}"
        )


@admin_router.get("/data-status")
async def get_data_status():
    """Check data initialization status"""
    try:
        # Count records in each set
        products_count = await database_manager.count_records("products")
        users_count = await database_manager.count_records("users")
        coupons_count = await database_manager.count_records("coupons")
        categories_count = await database_manager.count_records("categories")
        
        return {
            "products": products_count,
            "users": users_count,
            "coupons": coupons_count,
            "categories": categories_count,
            "is_initialized": products_count > 0 and users_count > 0
        }
        
    except Exception as e:
        logger.error(f"Error checking data status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check data status"
        )

@admin_router.post("/coupons")
async def create_coupon(coupon_data: dict):
    """Create a new coupon (used by RecoEngine for churn prevention)"""
    try:
        # Import here to avoid circular imports
        from models.coupon import Coupon
        
        # Create coupon instance
        coupon = Coupon(
            code=coupon_data["code"],
            name=coupon_data["name"],
            description=coupon_data.get("description", ""),
            discount_type=coupon_data["discount_type"],
            discount_value=coupon_data["discount_value"],
            minimum_order_value=coupon_data.get("minimum_order_value", 0.0),
            usage_limit=coupon_data.get("usage_limit", 1),
            user_specific=coupon_data.get("user_specific", False),
            applicable_user_ids=coupon_data.get("applicable_user_ids", []),
            valid_from=coupon_data.get("valid_from"),
            valid_until=coupon_data.get("valid_until"),
            is_active=coupon_data.get("is_active", True),
            created_by_system=coupon_data.get("created_by_system", "admin")
        )
        
        # Store in database
        await database_manager.store_coupon(coupon)
        
        logger.info(f"Created coupon {coupon.code} via admin API")
        
        return {
            "message": "Coupon created successfully",
            "coupon": {
                "code": coupon.code,
                "name": coupon.name,
                "discount_type": coupon.discount_type,
                "discount_value": coupon.discount_value,
                "valid_until": coupon.valid_until,
                "user_specific": coupon.user_specific,
                "applicable_user_ids": coupon.applicable_user_ids
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating coupon: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create coupon: {str(e)}"
        )
