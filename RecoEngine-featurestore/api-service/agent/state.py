"""
Agent State Definition for Churn Prediction Workflow

Defines the state that flows through the LangGraph agent nodes.
"""

from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class UserFeatures(TypedDict, total=False):
    """User features retrieved from the feature store."""
    # Profile features
    acc_age_days: Optional[int]
    member_dur: Optional[int]
    loyalty_tier: Optional[str]
    geo_location: Optional[str]
    device_type: Optional[str]
    
    # Behavior features
    days_last_login: Optional[int]
    days_last_purch: Optional[int]
    sess_7d: Optional[int]
    sess_30d: Optional[int]
    cart_abandon: Optional[float]
    
    # Transactional features
    avg_order_val: Optional[float]
    orders_6m: Optional[int]
    refund_rate: Optional[float]
    
    # Engagement features
    push_open_rate: Optional[float]
    email_ctr: Optional[float]
    
    # Support features
    tickets_90d: Optional[int]
    csat_score: Optional[float]
    
    # Real-time features
    cart_no_buy: Optional[bool]
    cart_items: Optional[List[Dict[str, Any]]]
    abandon_count: Optional[int]


class ChurnPrediction(TypedDict, total=False):
    """Churn prediction results."""
    churn_probability: float
    risk_segment: str
    churn_reasons: List[str]
    confidence_score: float


class NudgeDecision(TypedDict, total=False):
    """Nudge decision made by the agent."""
    should_nudge: bool
    nudge_type: str
    priority: str
    rule_matched: Optional[str]


class GeneratedNudge(TypedDict, total=False):
    """Generated nudge content."""
    message: str
    channel: str
    coupon_code: Optional[str]
    discount_value: Optional[float]
    discount_type: Optional[str]


class AgentState(TypedDict):
    """
    Complete state for the churn prediction agent workflow.
    
    This state flows through all nodes in the LangGraph and is
    checkpointed to Aerospike at each step.
    """
    # LangGraph message history for agent reasoning
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User identification
    user_id: str
    
    # Step outputs
    user_features: Optional[UserFeatures]
    feature_freshness: Optional[str]
    churn_prediction: Optional[ChurnPrediction]
    nudge_decision: Optional[NudgeDecision]
    generated_nudge: Optional[GeneratedNudge]
    
    # Workflow metadata
    current_step: str
    error: Optional[str]
    completed: bool
    
    # Intermediate data for agent reasoning
    intermediate: Optional[Dict[str, Any]]


def create_initial_state(user_id: str) -> AgentState:
    """Create an initial state for a new prediction workflow."""
    return AgentState(
        messages=[],
        user_id=user_id,
        user_features=None,
        feature_freshness=None,
        churn_prediction=None,
        nudge_decision=None,
        generated_nudge=None,
        current_step="start",
        error=None,
        completed=False,
        intermediate=None,
    )

