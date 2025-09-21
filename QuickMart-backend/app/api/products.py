"""
Product catalog API endpoints
"""

from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional, List
import logging

from core.database import database_manager
from core.auth import get_current_user_optional
from models.product import Product, ProductResponse, ProductFilter, Category

logger = logging.getLogger(__name__)

products_router = APIRouter()

@products_router.get("/", response_model=ProductResponse)
async def get_products(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    subcategory: Optional[str] = Query(None, description="Filter by subcategory"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    is_featured: Optional[bool] = Query(None, description="Filter featured products"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get products with filtering and pagination"""
    try:
        # Get all products
        all_products = await database_manager.scan_set("products")
        
        # Filter products
        filtered_products = []
        for product_data in all_products:
            if not product_data.get("is_active", True):
                continue
            
            # Apply filters
            if category and product_data.get("category") != category:
                continue
            if subcategory and product_data.get("subcategory") != subcategory:
                continue
            if brand and product_data.get("brand") != brand:
                continue
            if min_price and product_data.get("price", 0) < min_price:
                continue
            if max_price and product_data.get("price", 0) > max_price:
                continue
            if is_featured is not None and product_data.get("is_featured", False) != is_featured:
                continue
            
            # Search filter
            if search:
                search_lower = search.lower()
                name_match = search_lower in product_data.get("name", "").lower()
                desc_match = search_lower in product_data.get("description", "").lower()
                tag_match = any(search_lower in tag.lower() for tag in product_data.get("tags", []))
                
                if not (name_match or desc_match or tag_match):
                    continue
            
            filtered_products.append(product_data)
        
        # Sort by featured first, then by name
        filtered_products.sort(key=lambda x: (not x.get("is_featured", False), x.get("name", "")))
        
        # Pagination
        total = len(filtered_products)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_products = filtered_products[start_idx:end_idx]
        
        # Convert to Product models
        products = []
        for product_data in paginated_products:
            try:
                product = Product(**product_data)
                products.append(product)
            except Exception as e:
                logger.warning(f"Failed to parse product {product_data.get('product_id')}: {e}")
                continue
        
        has_next = end_idx < total
        
        return ProductResponse(
            products=products,
            total=total,
            page=page,
            limit=limit,
            has_next=has_next
        )
        
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch products"
        )

@products_router.get("/{product_id}", response_model=Product)
async def get_product(
    product_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get specific product by ID"""
    try:
        product_data = await database_manager.get("products", product_id)
        if not product_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        if not product_data.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not available"
            )
        
        return Product(**product_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch product"
        )

@products_router.get("/category/{category}")
async def get_products_by_category(
    category: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get products by category"""
    return await get_products(
        page=page,
        limit=limit,
        category=category,
        current_user=current_user
    )

@products_router.get("/search")
async def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Search products"""
    return await get_products(
        page=page,
        limit=limit,
        search=q,
        current_user=current_user
    )

@products_router.get("/featured")
async def get_featured_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get featured products"""
    return await get_products(
        page=page,
        limit=limit,
        is_featured=True,
        current_user=current_user
    )

@products_router.get("/categories/", response_model=List[Category])
async def get_categories():
    """Get all product categories"""
    try:
        categories_data = await database_manager.scan_set("categories")
        
        categories = []
        for category_data in categories_data:
            if category_data.get("is_active", True):
                try:
                    category = Category(**category_data)
                    categories.append(category)
                except Exception as e:
                    logger.warning(f"Failed to parse category {category_data.get('category_id')}: {e}")
                    continue
        
        # Sort by sort_order, then by name
        categories.sort(key=lambda x: (x.sort_order, x.name))
        
        return categories
        
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch categories"
        )
