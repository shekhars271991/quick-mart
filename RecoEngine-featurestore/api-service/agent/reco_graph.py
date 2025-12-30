"""
Recommendations LangGraph

A LangGraph workflow that generates personalized product recommendations
based on cart items, user features, and churn risk using vector search.

Triggered on user login.
"""

import logging
from typing import Dict, Any, Optional

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage

from .reco_state import (
    RecommendationState,
    RecommendedProduct,
    create_initial_reco_state,
    get_discount_for_risk,
    DISCOUNT_TIERS
)
from .store_helper import retrieve_all_user_features_async
from .product_indexer import search_similar_products
from .graph_logger import get_reco_logger, log_graph_start, log_graph_end, log_node

# Use dedicated recommendations graph logger
logger = get_reco_logger()


# ============== Node Factory Functions ==============

def create_get_cart_items_node():
    """Factory to create cart items fetching node."""
    
    async def get_cart_items_node(state: RecommendationState) -> RecommendationState:
        """Node: Use cart items passed from frontend (cart is managed client-side)."""
        user_id = state["user_id"]
        log_node(logger, "Cart", f"Processing cart for user {user_id}")
        
        try:
            # Cart items are passed from the frontend (managed by Zustand store)
            # They're already in state from the initial workflow call
            cart_items = state.get("cart_items", [])
            
            if cart_items:
                log_node(logger, "Cart", f"Received {len(cart_items)} items from frontend")
                for item in cart_items[:3]:  # Log first 3 items
                    logger.info(f"  - {item.get('name', 'Unknown')} (${item.get('price', 0):.2f})")
            else:
                log_node(logger, "Cart", "No cart items (cart is empty or not passed)")
            
            cart_total = sum(
                item.get("price", 0) * item.get("quantity", 1) 
                for item in cart_items
            )
            
            state["cart_items"] = cart_items
            state["cart_total"] = cart_total
            state["current_step"] = "cart_fetched"
            
            state["messages"].append(
                AIMessage(content=f"[Cart] Found {len(cart_items)} items (${cart_total:.2f} total)")
            )
            
            log_node(logger, "Cart", f"Total: {len(cart_items)} items, ${cart_total:.2f}")
            
        except Exception as e:
            logger.warning(f"[Reco] Error processing cart: {e}")
            state["cart_items"] = []
            state["cart_total"] = 0.0
            state["current_step"] = "cart_fetched"
        
        return state
    
    return get_cart_items_node


def create_get_user_features_node(store):
    """Factory to create user features retrieval node with store injected."""
    
    async def get_user_features_node(state: RecommendationState) -> RecommendationState:
        """Node: Retrieve user features from AerospikeStore."""
        user_id = state["user_id"]
        log_node(logger, "Features", f"Retrieving for user {user_id}")
        
        try:
            features, freshness = await retrieve_all_user_features_async(store, user_id)
            
            state["user_features"] = features
            state["feature_freshness"] = freshness
            state["current_step"] = "features_retrieved"
            
            state["messages"].append(
                AIMessage(content=f"[Features] Retrieved {len(features)} user features")
            )
            
            log_node(logger, "Features", f"Retrieved {len(features)} features")
            
        except Exception as e:
            logger.warning(f"[Reco] Could not get features: {e}")
            state["user_features"] = {}
            state["feature_freshness"] = ""
            state["current_step"] = "features_retrieved"
        
        return state
    
    return get_user_features_node


def create_estimate_churn_risk_node(churn_predictor=None):
    """Factory to create churn risk estimation node."""
    
    def estimate_churn_risk_node(state: RecommendationState) -> RecommendationState:
        """Node: Estimate churn risk based on user features."""
        user_id = state["user_id"]
        features = state.get("user_features", {})
        
        log_node(logger, "Churn", f"Estimating risk for user {user_id}")
        
        # Default to low risk if prediction fails
        churn_probability = 0.0
        churn_risk = "low_risk"
        
        try:
            if churn_predictor and features:
                prediction = churn_predictor.predict_churn(features)
                churn_probability = prediction.get("churn_probability", 0.0)
                churn_risk = prediction.get("risk_segment", "low_risk")
                log_node(logger, "Churn", f"Risk: {churn_risk} ({churn_probability:.1%})")
            else:
                # No predictor or no features - skip with warning
                if not churn_predictor:
                    log_node(logger, "Churn", "Skipped - no predictor configured")
                elif not features:
                    log_node(logger, "Churn", "Skipped - no user features available")
        
        except Exception as e:
            logger.warning(f"Churn estimation failed: {e}")
            log_node(logger, "Churn", f"Failed: {e}")
        
        state["churn_probability"] = churn_probability
        state["churn_risk"] = churn_risk
        state["current_step"] = "churn_estimated"
        
        state["messages"].append(
            AIMessage(content=f"[Churn] Risk: {churn_risk} ({churn_probability:.1%})")
        )
        
        return state
    
    return estimate_churn_risk_node


def create_vector_search_node(store):
    """Factory to create vector search node with store injected."""
    
    async def vector_search_products_node(state: RecommendationState) -> RecommendationState:
        """Node: Search for similar products using vector search."""
        user_id = state["user_id"]
        cart_items = state.get("cart_items", [])
        user_features = state.get("user_features", {})
        
        log_node(logger, "Search", f"Vector searching products for user {user_id}")
        
        similar_products = []
        cart_product_ids = set(item.get("product_id") for item in cart_items)
        
        try:
            # Build search query from cart items
            search_queries = []
            cart_categories = set()
            cart_brands = set()
            
            if cart_items:
                # Add queries based on cart items
                for item in cart_items[:3]:  # Top 3 cart items
                    query_parts = []
                    if item.get("name"):
                        query_parts.append(item["name"])
                    if item.get("category"):
                        query_parts.append(f"Category: {item['category']}")
                        cart_categories.add(item["category"])
                    if item.get("brand"):
                        query_parts.append(f"Brand: {item['brand']}")
                        cart_brands.add(item["brand"])
                    if query_parts:
                        search_queries.append(" | ".join(query_parts))
                
                # If cart has categories, add a category-focused search
                if cart_categories:
                    search_queries.append(f"Category: {', '.join(list(cart_categories)[:3])}")
                    
                log_node(logger, "Search", f"Searching based on {len(cart_items)} cart items")
            else:
                # No cart items - use user's purchase history from features or generic search
                log_node(logger, "Search", "Cart is empty, using user history or popular products")
                
                # Try to get categories from user's recent orders
                recent_categories = user_features.get("recent_order_categories", [])
                if recent_categories:
                    search_queries.append(f"Category: {', '.join(recent_categories[:3])}")
                    log_node(logger, "Search", f"Using user's recent order categories: {recent_categories[:3]}")
                
                # Add variety with different product types
                search_queries.extend([
                    "trending popular products best sellers",
                    "electronics gadgets tech accessories",
                    "home kitchen essentials deals"
                ])
            
            # Run vector searches
            all_results = []
            for query in search_queries[:3]:  # Max 3 searches
                results = await search_similar_products(
                    store=store,
                    query=query,
                    limit=10,
                    exclude_product_ids=list(cart_product_ids)
                )
                all_results.extend(results)
            
            # Deduplicate by product_id and sort by similarity
            seen_ids = set()
            for product in all_results:
                pid = product.get("product_id")
                if pid and pid not in seen_ids and pid not in cart_product_ids:
                    seen_ids.add(pid)
                    similar_products.append(product)
            
            # Sort by similarity score
            similar_products.sort(
                key=lambda p: p.get("similarity_score", 0), 
                reverse=True
            )
            similar_products = similar_products[:15]  # Top 15
            
            state["similar_products"] = similar_products
            state["current_step"] = "products_searched"
            
            state["messages"].append(
                AIMessage(content=f"[Search] Found {len(similar_products)} similar products")
            )
            
            log_node(logger, "Search", f"Found {len(similar_products)} similar products")
            
        except Exception as e:
            logger.error(f"[Reco] Vector search failed: {e}")
            state["similar_products"] = []
            state["current_step"] = "products_searched"
            state["messages"].append(
                AIMessage(content=f"[Search] Vector search failed: {str(e)}")
            )
        
        return state
    
    return vector_search_products_node


def rank_and_discount_node(state: RecommendationState) -> RecommendationState:
    """Node: Rank products and apply discounts based on churn risk."""
    user_id = state["user_id"]
    similar_products = state.get("similar_products", [])
    churn_risk = state.get("churn_risk", "low_risk")
    cart_items = state.get("cart_items", [])
    
    log_node(logger, "Rank", f"Ranking and applying discounts for user {user_id}")
    
    recommendations = []
    cart_categories = set(item.get("category") for item in cart_items if item.get("category"))
    cart_brands = set(item.get("brand") for item in cart_items if item.get("brand"))
    
    discount_info = DISCOUNT_TIERS.get(churn_risk, DISCOUNT_TIERS["low_risk"])
    
    for product in similar_products:
        price = product.get("price", 0)
        if price <= 0:
            continue
        
        # Calculate discount based on churn risk
        discounted_price, discount_pct = get_discount_for_risk(churn_risk, price)
        
        # Determine recommendation reason
        reasons = []
        if product.get("category") in cart_categories:
            reasons.append(f"Similar to items in your cart")
        if product.get("brand") in cart_brands:
            reasons.append(f"From {product.get('brand')}, a brand you like")
        if product.get("similarity_score", 0) > 0.7:
            reasons.append("Highly relevant to your interests")
        if product.get("rating", 0) >= 4.5:
            reasons.append("Top-rated by customers")
        
        if not reasons:
            reasons.append("Recommended for you")
        
        reco = RecommendedProduct(
            product_id=product.get("product_id", ""),
            name=product.get("name", ""),
            description=product.get("description", ""),
            category=product.get("category", ""),
            brand=product.get("brand", ""),
            price=price,
            original_price=product.get("original_price"),
            discounted_price=discounted_price,
            discount_percentage=discount_pct,
            rating=product.get("rating", 0),
            review_count=product.get("review_count", 0),
            image=product.get("image"),
            similarity_score=product.get("similarity_score", 0),
            recommendation_reason=reasons[0]
        )
        
        recommendations.append(reco)
    
    # Sort by a combination of similarity and rating
    recommendations.sort(
        key=lambda r: (r.get("similarity_score", 0) * 0.6 + r.get("rating", 0) / 5 * 0.4),
        reverse=True
    )
    
    # Take top 8 recommendations
    recommendations = recommendations[:8]
    
    state["recommendations"] = recommendations
    state["current_step"] = "ranked"
    
    state["messages"].append(
        AIMessage(content=f"[Rank] Created {len(recommendations)} recommendations with {churn_risk} discounts")
    )
    
    log_node(logger, "Rank", f"Created {len(recommendations)} recommendations")
    
    return state


def create_store_recommendations_node(store):
    """Factory to create recommendations storage node."""
    
    async def store_recommendations_node(state: RecommendationState) -> RecommendationState:
        """Node: Store recommendations in AerospikeStore for later retrieval."""
        user_id = state["user_id"]
        recommendations = state.get("recommendations", [])
        
        log_node(logger, "Store", f"Saving {len(recommendations)} recommendations")
        
        try:
            from datetime import datetime
            
            reco_data = {
                "user_id": user_id,
                "recommendations": [dict(r) for r in recommendations],
                "churn_risk": state.get("churn_risk", "low_risk"),
                "churn_probability": state.get("churn_probability", 0),
                "cart_item_count": len(state.get("cart_items", [])),
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Store in user_recommendations namespace
            await store.aput(
                namespace=("user_recommendations",),
                key=user_id,
                value=reco_data,
                index=False  # No vector indexing needed
            )
            
            state["current_step"] = "stored"
            state["completed"] = True
            
            state["messages"].append(
                AIMessage(content=f"[Store] Cached recommendations for user {user_id}")
            )
            
            log_node(logger, "Store", f"Saved for user {user_id}")
            
        except Exception as e:
            logger.error(f"[Reco] Failed to store recommendations: {e}")
            state["error"] = str(e)
            state["current_step"] = "error"
        
        return state
    
    return store_recommendations_node


def error_handler_node(state: RecommendationState) -> RecommendationState:
    """Node: Handle errors in the workflow."""
    error = state.get("error", "Unknown error")
    logger.error(f"[Reco] Workflow error: {error}")
    
    state["messages"].append(
        AIMessage(content=f"[Error] Recommendation workflow failed: {error}")
    )
    state["completed"] = True
    return state


# ============== Routing Functions ==============

def should_continue(state: RecommendationState) -> str:
    """Route based on error state."""
    if state.get("error"):
        return "error"
    return "continue"


# ============== Graph Builder ==============

def create_recommendations_graph(
    product_store=None,
    features_store=None,
    churn_predictor=None,
    checkpointer=None
) -> StateGraph:
    """
    Create the LangGraph for product recommendations.
    
    Args:
        product_store: AerospikeStore for products (set="products", vector search)
        features_store: AerospikeStore for user features (set="user_features")
        churn_predictor: Optional churn prediction model
        checkpointer: Optional checkpointer for state persistence
        
    Returns:
        Compiled StateGraph
    """
    builder = StateGraph(RecommendationState)
    
    # Create nodes with injected dependencies
    get_cart_node = create_get_cart_items_node()
    
    # Features node uses features_store (set="user_features")
    if features_store:
        get_features_node = create_get_user_features_node(features_store)
    else:
        async def get_features_node(state):
            state["user_features"] = {}
            state["current_step"] = "features_retrieved"
            logger.warning("Features store not configured - no user features available")
            return state
    
    # Vector search and storage use product_store (set="products")
    if product_store:
        vector_search_node = create_vector_search_node(product_store)
        store_recos_node = create_store_recommendations_node(product_store)
    else:
        # Fallback nodes when product store not configured
        async def vector_search_node(state):
            state["similar_products"] = []
            state["current_step"] = "products_searched"
            state["messages"].append(AIMessage(content="[Search] Product store not configured"))
            logger.warning("Product store not configured - no vector search available")
            return state
        
        async def store_recos_node(state):
            state["completed"] = True
            state["current_step"] = "completed"
            return state
    
    estimate_churn_node = create_estimate_churn_risk_node(churn_predictor)
    
    # Add nodes
    builder.add_node("get_cart", get_cart_node)
    builder.add_node("get_features", get_features_node)
    builder.add_node("estimate_churn", estimate_churn_node)
    builder.add_node("vector_search", vector_search_node)
    builder.add_node("rank_discount", rank_and_discount_node)
    builder.add_node("store_recommendations", store_recos_node)
    builder.add_node("error_handler", error_handler_node)
    
    # Set entry point
    builder.set_entry_point("get_cart")
    
    # Define edges (linear flow with error handling)
    builder.add_conditional_edges(
        "get_cart",
        should_continue,
        {"continue": "get_features", "error": "error_handler"}
    )
    
    builder.add_conditional_edges(
        "get_features",
        should_continue,
        {"continue": "estimate_churn", "error": "error_handler"}
    )
    
    builder.add_conditional_edges(
        "estimate_churn",
        should_continue,
        {"continue": "vector_search", "error": "error_handler"}
    )
    
    builder.add_conditional_edges(
        "vector_search",
        should_continue,
        {"continue": "rank_discount", "error": "error_handler"}
    )
    
    builder.add_conditional_edges(
        "rank_discount",
        should_continue,
        {"continue": "store_recommendations", "error": "error_handler"}
    )
    
    # Terminal edges
    builder.add_edge("store_recommendations", END)
    builder.add_edge("error_handler", END)
    
    # Compile
    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer
    
    graph = builder.compile(**compile_kwargs)
    
    logger.info(f"Recommendations graph compiled (product_store: {product_store is not None}, features_store: {features_store is not None})")
    return graph


async def run_recommendations_workflow(
    user_id: str,
    product_store=None,
    features_store=None,
    churn_predictor=None,
    checkpointer=None,
    cart_items: Optional[list] = None
) -> Dict[str, Any]:
    """
    Run the recommendations workflow for a user.
    
    Args:
        user_id: User to generate recommendations for
        product_store: AerospikeStore for products (vector search)
        features_store: AerospikeStore for user features
        churn_predictor: Optional churn predictor
        checkpointer: Optional checkpointer
        cart_items: Optional cart items (if not fetching from backend)
        
    Returns:
        Dictionary with recommendations and metadata
    """
    log_graph_start(logger, "Recommendations", user_id,
                   product_store=product_store is not None,
                   features_store=features_store is not None,
                   cart_items=len(cart_items) if cart_items else 0)
    
    graph = create_recommendations_graph(
        product_store=product_store,
        features_store=features_store,
        churn_predictor=churn_predictor,
        checkpointer=checkpointer
    )
    
    # Create initial state
    initial_state = create_initial_reco_state(user_id)
    if cart_items:
        initial_state["cart_items"] = cart_items
    
    initial_state["messages"].append(
        HumanMessage(content=f"Generate product recommendations for user {user_id}")
    )
    
    config = {"configurable": {"thread_id": f"reco_{user_id}"}}
    
    try:
        result = await graph.ainvoke(initial_state, config=config)
        
        reco_count = len(result.get("recommendations", []))
        churn_risk = result.get("churn_risk", "low_risk")
        
        log_graph_end(logger, "Recommendations", user_id, success=True,
                     recommendations=reco_count,
                     churn_risk=churn_risk)
        
        return {
            "user_id": user_id,
            "recommendations": result.get("recommendations", []),
            "churn_risk": result.get("churn_risk", "low_risk"),
            "churn_probability": result.get("churn_probability", 0),
            "completed": result.get("completed", False),
            "error": result.get("error"),
            "reasoning": [msg.content for msg in result.get("messages", [])]
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Workflow failed: {e}")
        log_graph_end(logger, "Recommendations", user_id, success=False,
                     error=str(e))
        return {
            "user_id": user_id,
            "recommendations": [],
            "error": str(e),
            "completed": False
        }

