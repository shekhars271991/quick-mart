"""
Agent Tools for Churn Prediction Workflow

These tools are used by the LangGraph agent to perform various steps
in the churn prediction and nudge generation workflow.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# These will be injected at runtime from main.py
_aerospike_client = None
_churn_predictor = None
_nudge_engine = None
_message_generator = None
_namespace = "churnprediction"


def configure_tools(
    aerospike_client,
    churn_predictor,
    nudge_engine,
    message_generator,
    namespace: str = "churnprediction"
):
    """Configure the tools with required dependencies."""
    global _aerospike_client, _churn_predictor, _nudge_engine, _message_generator, _namespace
    _aerospike_client = aerospike_client
    _churn_predictor = churn_predictor
    _nudge_engine = nudge_engine
    _message_generator = message_generator
    _namespace = namespace
    logger.info("Agent tools configured with dependencies")


@tool
def retrieve_user_features_tool(user_id: str) -> Dict[str, Any]:
    """
    Retrieve all user features from the Aerospike feature store.
    
    Args:
        user_id: The unique identifier of the user
        
    Returns:
        Dictionary containing all user features and feature freshness timestamp
    """
    global _aerospike_client, _namespace
    
    if _aerospike_client is None:
        return {"error": "Aerospike client not configured", "features": {}, "freshness": None}
    
    feature_types = ["profile", "behavior", "transactional", "engagement", "support", "realtime"]
    all_features = {}
    feature_freshness = None
    
    for feature_type in feature_types:
        try:
            set_name = "user_features"
            key_name = f"{user_id}_{feature_type}"
            key = (_namespace, set_name, key_name)
            
            (key, metadata, bins) = _aerospike_client.get(key)
            if bins:
                features = {k: v for k, v in bins.items() if k not in ["timestamp", "feature_type"]}
                all_features.update(features)
                if not feature_freshness or bins.get("timestamp", "") > feature_freshness:
                    feature_freshness = bins.get("timestamp")
                    
        except Exception as e:
            if "RecordNotFound" not in str(type(e).__name__):
                logger.warning(f"Error retrieving {feature_type} features for user {user_id}: {e}")
    
    return {
        "features": all_features,
        "freshness": feature_freshness or datetime.utcnow().isoformat(),
        "feature_count": len(all_features)
    }


@tool
def predict_churn_tool(user_features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict churn probability for a user based on their features.
    
    Args:
        user_features: Dictionary of user features from the feature store
        
    Returns:
        Dictionary containing churn probability, risk segment, and reasons
    """
    global _churn_predictor
    
    if _churn_predictor is None:
        return {"error": "Churn predictor not configured"}
    
    if not user_features:
        return {"error": "No user features provided"}
    
    try:
        prediction = _churn_predictor.predict_churn(user_features)
        
        return {
            "churn_probability": prediction["churn_probability"],
            "risk_segment": prediction["risk_segment"],
            "churn_reasons": prediction["churn_reasons"],
            "confidence_score": prediction["confidence_score"]
        }
    except Exception as e:
        logger.error(f"Error predicting churn: {e}")
        return {"error": str(e)}


@tool
def decide_nudge_tool(
    user_id: str,
    churn_probability: float,
    risk_segment: str,
    churn_reasons: List[str]
) -> Dict[str, Any]:
    """
    Decide what type of nudge to send based on churn prediction results.
    
    Args:
        user_id: The user identifier
        churn_probability: Predicted churn probability (0.0-1.0)
        risk_segment: Risk segment (low_risk, medium_risk, high_risk, critical)
        churn_reasons: List of identified churn reasons
        
    Returns:
        Dictionary containing nudge decision details
    """
    global _nudge_engine
    
    # Determine if nudge should be sent based on risk
    should_nudge = churn_probability > 0.3 or risk_segment in ["medium_risk", "high_risk", "critical"]
    
    # Determine nudge type based on churn reasons
    nudge_type = "general_engagement"
    priority = "normal"
    
    if "CART_ABANDONMENT" in churn_reasons or "cart_abandon" in str(churn_reasons).lower():
        nudge_type = "cart_recovery"
        priority = "high"
    elif "INACTIVITY" in churn_reasons or "days_last_login" in str(churn_reasons).lower():
        nudge_type = "re_engagement"
        priority = "medium"
    elif "LOW_ENGAGEMENT" in churn_reasons:
        nudge_type = "engagement_boost"
        priority = "medium"
    elif "SUPPORT_ISSUES" in churn_reasons:
        nudge_type = "support_followup"
        priority = "high"
    elif risk_segment == "critical":
        nudge_type = "retention_offer"
        priority = "critical"
    elif risk_segment == "high_risk":
        nudge_type = "win_back"
        priority = "high"
    
    # Try to find matching rule from nudge engine
    rule_matched = None
    if _nudge_engine:
        try:
            test_result = _nudge_engine.test_rules(user_id, churn_probability, churn_reasons)
            rule_matched = test_result.get("matched_rule")
        except Exception as e:
            logger.warning(f"Could not test nudge rules: {e}")
    
    return {
        "should_nudge": should_nudge,
        "nudge_type": nudge_type,
        "priority": priority,
        "rule_matched": rule_matched,
        "reasoning": f"User has {risk_segment} with {churn_probability:.1%} churn probability. Primary concerns: {', '.join(churn_reasons[:3])}"
    }


@tool
async def generate_nudge_message_tool(
    user_id: str,
    nudge_type: str,
    churn_probability: float,
    churn_reasons: List[str],
    user_features: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a personalized nudge message for the user.
    
    Args:
        user_id: The user identifier
        nudge_type: Type of nudge (cart_recovery, re_engagement, etc.)
        churn_probability: The churn probability
        churn_reasons: List of churn reasons
        user_features: Optional user features for personalization
        
    Returns:
        Dictionary containing the generated message and metadata
    """
    global _message_generator, _nudge_engine
    
    message = None
    coupon_code = None
    discount_value = None
    discount_type = None
    channel = "in_app"
    
    # Try to generate message using LLM if available
    if _message_generator:
        try:
            message = await _message_generator.generate_message(
                user_id=user_id,
                churn_probability=churn_probability,
                churn_reasons=churn_reasons,
                user_features=user_features or {}
            )
        except Exception as e:
            logger.warning(f"LLM message generation failed: {e}")
    
    # Fall back to template-based messages
    if not message:
        templates = {
            "cart_recovery": "Hey! You left some great items in your cart. Complete your purchase now and enjoy free shipping!",
            "re_engagement": "We miss you! Come back and discover what's new. Here's a special offer just for you.",
            "engagement_boost": "Check out our latest deals curated just for you! Don't miss out on exclusive savings.",
            "support_followup": "We hope your recent experience has improved. Let us know if there's anything else we can help with!",
            "retention_offer": "We value you as a customer! Here's an exclusive discount as a thank you for being with us.",
            "win_back": "It's been a while! We'd love to have you back. Enjoy this special returning customer offer.",
            "general_engagement": "Discover personalized recommendations and exclusive offers waiting for you!"
        }
        message = templates.get(nudge_type, templates["general_engagement"])
    
    # Determine if coupon should be included based on risk
    if churn_probability > 0.6 or nudge_type in ["retention_offer", "win_back", "cart_recovery"]:
        discount_type = "percentage"
        if churn_probability > 0.8:
            discount_value = 25
            coupon_code = f"SAVE25_{user_id[-4:].upper()}"
        elif churn_probability > 0.6:
            discount_value = 15
            coupon_code = f"SAVE15_{user_id[-4:].upper()}"
        else:
            discount_value = 10
            coupon_code = f"SAVE10_{user_id[-4:].upper()}"
    
    # Determine channel based on nudge type
    if nudge_type in ["cart_recovery", "retention_offer"]:
        channel = "push_notification"
    elif nudge_type == "support_followup":
        channel = "email"
    
    return {
        "message": message,
        "channel": channel,
        "coupon_code": coupon_code,
        "discount_value": discount_value,
        "discount_type": discount_type,
        "nudge_type": nudge_type,
        "generated_at": datetime.utcnow().isoformat()
    }


@tool
async def send_nudge_tool(
    user_id: str,
    message: str,
    channel: str,
    nudge_type: str,
    coupon_code: Optional[str] = None,
    discount_value: Optional[float] = None,
    discount_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send the generated nudge to the user via the appropriate channel.
    
    Args:
        user_id: The user identifier
        message: The nudge message to send
        channel: Delivery channel (in_app, push_notification, email)
        nudge_type: Type of nudge being sent
        coupon_code: Optional coupon code to include
        discount_value: Optional discount value
        discount_type: Optional discount type (percentage or fixed)
        
    Returns:
        Dictionary containing send status and details
    """
    global _aerospike_client, _namespace, _nudge_engine
    
    import uuid
    
    # Create nudge record
    nudge_id = f"nudge_{uuid.uuid4().hex[:12]}"
    
    nudge_record = {
        "nudge_id": nudge_id,
        "user_id": user_id,
        "message": message,
        "channel": channel,
        "nudge_type": nudge_type,
        "coupon_code": coupon_code,
        "discount_value": discount_value,
        "discount_type": discount_type,
        "status": "sent",
        "sent_at": datetime.utcnow().isoformat()
    }
    
    # Store in Aerospike for tracking
    if _aerospike_client:
        try:
            key = (_namespace, "user_nudges", f"{user_id}_{nudge_id}")
            _aerospike_client.put(key, {"data": nudge_record})
            logger.info(f"Stored nudge {nudge_id} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to store nudge record: {e}")
    
    # If coupon was included, create it in the coupons set AND user_coupons set
    coupon_id = None
    if coupon_code and _aerospike_client:
        try:
            from datetime import timedelta
            now = datetime.utcnow()
            
            # Generate unique IDs
            coupon_id = f"cpn_{uuid.uuid4().hex[:12]}"
            user_coupon_id = f"uc_{uuid.uuid4().hex[:12]}"
            
            # Determine discount description
            discount_desc = f"{discount_value}% off" if discount_type == "percentage" else f"${discount_value} off"
            
            # 1. Store coupon in "coupons" set (wrapped in "data" bin for Aerospike)
            coupon_record = {
                "coupon_id": coupon_id,
                "code": coupon_code,
                "name": "Special Offer for You",
                "description": f"Exclusive {discount_desc} discount from your personalized offer",
                "discount_type": discount_type or "percentage",
                "discount_value": discount_value or 10,
                "min_order_val": 0,
                "max_discount": None,
                "usage_limit": 1,
                "usage_count": 0,
                "valid_from": now.isoformat(),
                "valid_until": (now + timedelta(days=7)).isoformat(),
                "is_active": True,
                "applicable_categories": [],
                "applicable_products": [],
                "created_at": now.isoformat(),
                "user_id": user_id,
                "source": "agent_nudge",
                "nudge_id": nudge_id
            }
            coupon_key = (_namespace, "coupons", coupon_id)
            _aerospike_client.put(coupon_key, {"data": coupon_record})
            logger.info(f"Created coupon {coupon_code} (id: {coupon_id}) for user {user_id}")
            
            # 2. Create UserCoupon record in "user_coupons" set (links coupon to user)
            user_coupon_record = {
                "user_coupon_id": user_coupon_id,
                "user_id": user_id,
                "coupon_id": coupon_id,
                "source": "nudge",
                "nudge_id": nudge_id,
                "churn_score": None,  # Will be populated if available
                "status": "available",
                "assigned_at": now.isoformat(),
                "used_at": None,
                "order_id": None
            }
            user_coupon_key = (_namespace, "user_coupons", user_coupon_id)
            _aerospike_client.put(user_coupon_key, {"data": user_coupon_record})
            logger.info(f"Linked coupon {coupon_id} to user {user_id} via user_coupon {user_coupon_id}")
            
        except Exception as e:
            logger.error(f"Failed to create coupon: {e}")
    
    # Store notification message in "custom_user_messages" set
    if _aerospike_client:
        try:
            now = datetime.utcnow()
            message_id = f"msg_{uuid.uuid4().hex[:12]}"
            message_key = f"{user_id}_{message_id}"
            
            message_record = {
                "user_id": user_id,
                "message_id": message_id,
                "message": message,
                "churn_prob": None,  # Shortened field name for Aerospike
                "churn_reasons": [],
                "user_ftrs": {},  # Shortened field name
                "created_at": now.isoformat(),
                "status": "generated",
                "read_at": None,
                "channel": channel,
                "nudge_type": nudge_type,
                "nudge_id": nudge_id,
                "coupon_code": coupon_code
            }
            msg_key = (_namespace, "custom_user_messages", message_key)
            _aerospike_client.put(msg_key, {"data": message_record})
            logger.info(f"Stored notification message {message_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store notification message: {e}")
    
    # Also trigger via nudge engine if available for additional actions
    if _nudge_engine:
        try:
            logger.info(f"Nudge {nudge_id} would be processed by nudge engine for {channel} delivery")
        except Exception as e:
            logger.warning(f"Nudge engine processing failed: {e}")
    
    return {
        "success": True,
        "nudge_id": nudge_id,
        "channel": channel,
        "coupon_created": coupon_code is not None,
        "sent_at": nudge_record["sent_at"]
    }

