"""
State Definition for Recommendations Graph

Defines the state that flows through the recommendations LangGraph workflow.
"""

from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage


class CartItem(TypedDict, total=False):
    """Represents an item in the user's cart."""
    product_id: str
    name: str
    description: str
    category: str
    brand: str
    price: float
    quantity: int


class RecommendedProduct(TypedDict, total=False):
    """A product recommendation with applied discount."""
    product_id: str
    name: str
    description: str
    category: str
    brand: str
    price: float
    original_price: Optional[float]
    discounted_price: float
    discount_percentage: int
    rating: float
    review_count: int
    image: Optional[str]
    similarity_score: float
    recommendation_reason: str


class RecommendationState(TypedDict, total=False):
    """
    State for the Recommendations LangGraph.
    
    This state flows through nodes that:
    1. Get cart items
    2. Get user features
    3. Estimate churn risk
    4. Vector search for similar products
    5. Rank and apply discounts
    6. Store recommendations
    """
    # Input
    user_id: str
    
    # Cart data
    cart_items: List[CartItem]
    cart_total: float
    
    # User features from store
    user_features: Dict[str, Any]
    feature_freshness: str
    
    # Churn risk assessment
    churn_probability: float
    churn_risk: str  # low_risk, medium_risk, high_risk, critical
    
    # Vector search results
    similar_products: List[Dict[str, Any]]
    
    # Final recommendations with discounts applied
    recommendations: List[RecommendedProduct]
    
    # Workflow tracking
    current_step: str
    error: Optional[str]
    completed: bool
    messages: List[BaseMessage]


def create_initial_reco_state(user_id: str) -> RecommendationState:
    """Create initial state for recommendations workflow."""
    return RecommendationState(
        user_id=user_id,
        cart_items=[],
        cart_total=0.0,
        user_features={},
        feature_freshness="",
        churn_probability=0.0,
        churn_risk="low_risk",
        similar_products=[],
        recommendations=[],
        current_step="started",
        error=None,
        completed=False,
        messages=[]
    )


# Discount tiers based on churn risk
DISCOUNT_TIERS = {
    "low_risk": {
        "min_discount": 0,
        "max_discount": 5,
        "message": "Enjoy our recommendations"
    },
    "medium_risk": {
        "min_discount": 5,
        "max_discount": 10,
        "message": "Special prices just for you"
    },
    "high_risk": {
        "min_discount": 15,
        "max_discount": 20,
        "message": "Exclusive member discounts"
    },
    "critical": {
        "min_discount": 20,
        "max_discount": 30,
        "message": "VIP pricing - Limited time offer!"
    }
}


def get_discount_for_risk(churn_risk: str, base_price: float) -> tuple[float, int]:
    """
    Calculate discounted price based on churn risk level.
    
    Args:
        churn_risk: Risk level (low_risk, medium_risk, high_risk, critical)
        base_price: Original product price
        
    Returns:
        Tuple of (discounted_price, discount_percentage)
    """
    tier = DISCOUNT_TIERS.get(churn_risk, DISCOUNT_TIERS["low_risk"])
    
    # Use average of min and max for consistent discounts
    discount_pct = (tier["min_discount"] + tier["max_discount"]) // 2
    
    if discount_pct > 0:
        discounted_price = base_price * (1 - discount_pct / 100)
        return round(discounted_price, 2), discount_pct
    
    return base_price, 0

