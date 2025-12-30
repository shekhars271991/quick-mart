"""
Product Indexer for Vector Search

Indexes products from QuickMart backend into the AerospikeStore
with embeddings for semantic search.
"""

import logging
import httpx
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# QuickMart backend URL
QUICKMART_BACKEND_URL = os.getenv("QUICKMART_BACKEND_URL", "http://localhost:3011")


async def fetch_products_from_backend() -> List[Dict[str, Any]]:
    """Fetch all products from QuickMart backend."""
    try:
        # Use follow_redirects=True and add trailing slash to avoid 307 redirects
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(f"{QUICKMART_BACKEND_URL}/api/products/", params={"limit": 1000})
            if response.status_code == 200:
                data = response.json()
                products = data.get("products", [])
                logger.info(f"Fetched {len(products)} products from backend")
                return products
            else:
                logger.error(f"Failed to fetch products: {response.status_code}")
                return []
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        return []


def create_product_text_for_embedding(product: Dict[str, Any]) -> str:
    """
    Create a text representation of a product for embedding.
    Combines name, description, category, brand, and tags.
    """
    parts = []
    
    # Name is most important
    if product.get("name"):
        parts.append(product["name"])
    
    # Description provides context
    if product.get("description"):
        parts.append(product["description"])
    
    # Category and subcategory for categorization
    if product.get("category"):
        parts.append(f"Category: {product['category']}")
    if product.get("subcategory"):
        parts.append(f"Subcategory: {product['subcategory']}")
    
    # Brand for brand-based recommendations
    if product.get("brand"):
        parts.append(f"Brand: {product['brand']}")
    
    # Tags for additional keywords
    if product.get("tags"):
        parts.append(f"Tags: {', '.join(product['tags'])}")
    
    return " | ".join(parts)


async def index_products_in_store(store, products: Optional[List[Dict[str, Any]]] = None) -> int:
    """
    Index products in the AerospikeStore with embeddings.
    
    Args:
        store: AerospikeStore instance with embeddings configured
        products: Optional list of products. If None, fetches from backend.
        
    Returns:
        Number of products indexed
    """
    if products is None:
        products = await fetch_products_from_backend()
    
    if not products:
        logger.warning("No products to index")
        return 0
    
    indexed_count = 0
    
    for product in products:
        product_id = product.get("product_id")
        if not product_id:
            continue
        
        try:
            from datetime import datetime
            now = datetime.utcnow().isoformat()
            
            # Get image - prefer 'image' field, fallback to first in 'images' list
            image = product.get("image") or (product.get("images", [None])[0] if product.get("images") else None)
            
            # Create the value to store (full product data)
            product_value = {
                "product_id": product_id,
                "name": product.get("name", ""),
                "description": product.get("description", ""),
                "category": product.get("category", ""),
                "subcategory": product.get("subcategory"),
                "brand": product.get("brand", ""),
                "price": product.get("price", 0),
                "original_price": product.get("original_price"),
                "discount_percentage": product.get("discount_percentage", 0),
                "rating": product.get("rating", 0),
                "review_count": product.get("review_count", 0),
                "stock_quantity": product.get("stock_quantity", 0),
                "tags": product.get("tags", []),
                "image": image,
                "images": product.get("images", [image] if image else []),
                "specifications": product.get("specifications", {}),
                "is_featured": product.get("is_featured", False),
                "is_active": product.get("is_active", True),
                "created_at": now,
                "updated_at": now,
                # Embedding text field for vector search
                "embedding_text": create_product_text_for_embedding(product)
            }
            
            # Store in the products namespace with embedding
            # The store will automatically generate embeddings for the "embedding_text" field
            await store.aput(
                namespace=("products",),
                key=product_id,
                value=product_value,
                index=["embedding_text"]  # Index this field for vector search
            )
            
            indexed_count += 1
            
            if indexed_count % 10 == 0:
                logger.info(f"Indexed {indexed_count}/{len(products)} products")
                
        except Exception as e:
            logger.error(f"Failed to index product {product_id}: {e}")
            continue
    
    logger.info(f"Successfully indexed {indexed_count} products")
    return indexed_count


async def check_products_indexed(store) -> bool:
    """Check if products are already indexed in the store."""
    try:
        # Try to search for any product
        # namespace_prefix is positional-only (before /)
        results = await store.asearch(
            ("products",),  # positional argument
            limit=1
        )
        return len(results) > 0
    except Exception as e:
        logger.warning(f"Could not check product index: {e}")
        return False


async def search_similar_products(
    store,
    query: str,
    limit: int = 10,
    exclude_product_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Search for products similar to the query using vector search.
    
    Args:
        store: AerospikeStore instance
        query: Search query (e.g., product description or cart item text)
        limit: Maximum number of results
        exclude_product_ids: Product IDs to exclude from results
        
    Returns:
        List of similar products with similarity scores
    """
    try:
        logger.info(f"[Search] Starting vector search for: '{query[:50]}...'")
        
        # namespace_prefix is positional-only (before /)
        results = await store.asearch(
            ("products",),  # positional argument
            query=query,
            limit=limit + (len(exclude_product_ids) if exclude_product_ids else 0)
        )
        
        logger.info(f"[Search] Got {len(results)} results from store")
        
        # Convert to product dicts and filter excluded
        products = []
        for item in results:
            if exclude_product_ids and item.value.get("product_id") in exclude_product_ids:
                continue
            
            product = item.value.copy()
            product["similarity_score"] = item.score
            products.append(product)
            
            if len(products) >= limit:
                break
        
        logger.info(f"[Search] Returning {len(products)} products after filtering")
        return products
        
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

