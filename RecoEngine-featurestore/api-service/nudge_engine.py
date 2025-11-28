from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import httpx
import asyncio
import os
from config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Pydantic models
class NudgeRequest(BaseModel):
    user_id: str
    churn_probability: float
    risk_segment: str
    churn_reasons: List[str]

class NudgeAction(BaseModel):
    type: str
    content_template: str
    channel: str
    priority: int

class NudgeResponse(BaseModel):
    user_id: str
    nudges_triggered: List[NudgeAction]
    rule_matched: str
    timestamp: str

# Nudge Rules as defined in the plan
NUDGE_RULES = [
    {
        "rule_id": "high_risk_inactive_user",
        "churn_score_range": [0.7, 1.0],
        "churn_reasons": ["Inactive", "No purchase", "High risk factor"],
        "nudges": [
            {"type": "Custom Message", "content_template": "AI-Generated Personalized Message", "channel": "sms", "priority": 1},
            {"type": "Discount Coupon", "content_template": "20% Off Welcome Back", "channel": "app", "priority": 2, "discount_percent": 20, "coupon_code": "WELCOME20"},
            {"type": "Push Notification", "content_template": "We miss you! Get 20% off your next order", "channel": "push", "priority": 3}
        ]
    },
    {
        "rule_id": "low_risk_engagement",
        "churn_score_range": [0.0, 0.4],
        "churn_reasons": [],  # Matches all reasons (catch-all for low risk)
        "nudges": [
            {"type": "Custom Message", "content_template": "AI-Generated Engagement Message", "channel": "sms", "priority": 1}
        ]
    },
    {
        "rule_id": "medium_risk_cart_abandonment",
        "churn_score_range": [0.3, 0.6],
        "churn_reasons": ["cart", "abandon"],  # Will match any reason containing these words
        "nudges": [
            {"type": "Custom Message", "content_template": "AI-Generated Cart Reminder", "channel": "sms", "priority": 1}
        ]
    },
    {
        "rule_id": "rule_1",
        "churn_score_range": [0.6, 0.8],
        "churn_reasons": ["INACTIVITY", "DELIVERY_ISSUES"],
        "nudges": [
            {"type": "Email", "content_template": "Template 1", "channel": "email", "priority": 1}
        ]
    },
    {
        "rule_id": "rule_2", 
        "churn_score_range": [0.8, 1.0],
        "churn_reasons": ["CART_ABANDONMENT"],
        "nudges": [
            {"type": "Custom Message", "content_template": "AI-Generated Cart Recovery Message", "channel": "sms", "priority": 1},
            {"type": "Push Notification", "content_template": "Template 2", "channel": "push", "priority": 2},
            {"type": "Discount Coupon", "content_template": "Template 2", "channel": "email", "priority": 3}
        ]
    },
    {
        "rule_id": "rule_3",
        "churn_score_range": [0.7, 0.9],
        "churn_reasons": ["LOW_ENGAGEMENT"],
        "nudges": [
            {"type": "Email", "content_template": "Template 3", "channel": "email", "priority": 1}
        ]
    },
    {
        "rule_id": "rule_4",
        "churn_score_range": [0.6, 0.75],
        "churn_reasons": ["PRICE_SENSITIVITY"],
        "nudges": [
            {"type": "Discount Coupon", "content_template": "Template 4", "channel": "email", "priority": 1}
        ]
    },
    {
        "rule_id": "rule_5",
        "churn_score_range": [0.85, 1.0],
        "churn_reasons": ["PAYMENT_FAILURE"],
        "nudges": [
            {"type": "Push Notification", "content_template": "Template 5", "channel": "push", "priority": 1},
            {"type": "Email", "content_template": "Template 5", "channel": "email", "priority": 2}
        ]
    },
    {
        "rule_id": "rule_6",
        "churn_score_range": [0.65, 0.8],
        "churn_reasons": ["PRODUCT_AVAILABILITY"],
        "nudges": [
            {"type": "Push Notification", "content_template": "Template 6", "channel": "push", "priority": 1}
        ]
    },
    {
        "rule_id": "rule_7",
        "churn_score_range": [0.7, 0.9],
        "churn_reasons": ["INACTIVITY"],
        "nudges": [
            {"type": "Push Notification", "content_template": "Template 7", "channel": "push", "priority": 1}
        ]
    },
    {
        "rule_id": "rule_8",
        "churn_score_range": [0.6, 0.8],
        "churn_reasons": ["CART_ABANDONMENT", "LOW_ENGAGEMENT"],
        "nudges": [
            {"type": "Custom Message", "content_template": "AI-Generated Cart Abandonment Message", "channel": "sms", "priority": 1},
            {"type": "Email", "content_template": "Template 8", "channel": "email", "priority": 2},
            {"type": "Discount Coupon", "content_template": "Template 8", "channel": "email", "priority": 3}
        ]
    },
    {
        "rule_id": "rule_9",
        "churn_score_range": [0.75, 0.95],
        "churn_reasons": ["DELIVERY_ISSUES", "PRICE_SENSITIVITY"],
        "nudges": [
            {"type": "Push Notification", "content_template": "Template 9", "channel": "push", "priority": 1}
        ]
    },
    {
        "rule_id": "rule_10",
        "churn_score_range": [0.8, 1.0],
        "churn_reasons": ["PAYMENT_FAILURE", "CART_ABANDONMENT"],
        "nudges": [
            {"type": "Push Notification", "content_template": "Template 10", "channel": "push", "priority": 1},
            {"type": "Discount Coupon", "content_template": "Template 10", "channel": "email", "priority": 2},
            {"type": "Email", "content_template": "Template 10", "channel": "email", "priority": 3}
        ]
    }
]

class NudgeEngine:
    """Nudge engine for triggering retention nudges based on churn predictions"""
    
    def __init__(self):
        self.rules = NUDGE_RULES
        logger.info(f"Nudge engine initialized with {len(self.rules)} rules")
    
    def find_matching_rule(self, churn_probability: float, churn_reasons: List[str]) -> Dict[str, Any]:
        """Find the first matching nudge rule based on churn score and reasons"""
        
        # Sort rules by priority (rule_10 has highest priority)
        sorted_rules = sorted(self.rules, key=lambda x: int(x["rule_id"].split("_")[1]) if x["rule_id"].startswith("rule_") else 999, reverse=True)
        
        for rule in sorted_rules:
            # Check if churn probability is in range
            score_min, score_max = rule["churn_score_range"]
            if not (score_min <= churn_probability <= score_max):
                continue
            
            # Check if any churn reason matches (using flexible substring matching)
            rule_reasons = rule["churn_reasons"]
            reason_matched = False
            
            # If rule_reasons is empty, it's a catch-all rule (matches any reason)
            if not rule_reasons or len(rule_reasons) == 0:
                reason_matched = True
                logger.info(f"Rule {rule['rule_id']} matched (catch-all): score={churn_probability} in {rule['churn_score_range']}")
                return rule
            
            for rule_reason in rule_reasons:
                for churn_reason in churn_reasons:
                    # Convert to lowercase for case-insensitive matching
                    rule_reason_lower = rule_reason.lower()
                    churn_reason_lower = churn_reason.lower()
                    
                    # Check for substring matches in both directions
                    if (rule_reason_lower in churn_reason_lower or 
                        churn_reason_lower in rule_reason_lower or
                        self._reasons_semantically_match(rule_reason_lower, churn_reason_lower)):
                        reason_matched = True
                        break
                
                if reason_matched:
                    break
            
            if reason_matched:
                logger.info(f"Rule {rule['rule_id']} matched: score={churn_probability} in {rule['churn_score_range']}, reasons matched")
                return rule
        
        logger.info(f"No matching rule found for score={churn_probability}, reasons={churn_reasons}")
        return None
    
    def _reasons_semantically_match(self, rule_reason: str, churn_reason: str) -> bool:
        """Check if reasons are semantically similar"""
        # Define semantic mappings
        semantic_mappings = {
            "inactive": ["inactive", "inactivity", "no login", "not active"],
            "no purchase": ["no purchase", "no recent purchase", "purchase", "buying"],
            "high risk factor": ["high risk", "risk factor", "risk"],
            "cart abandonment": ["cart abandon", "abandonment", "cart"],
            "low engagement": ["engagement", "low engagement", "not engaged"],
            "delivery issues": ["delivery", "shipping", "fulfillment"],
            "price sensitivity": ["price", "cost", "expensive", "pricing"],
            "payment failure": ["payment", "billing", "card", "transaction"]
        }
        
        for key, synonyms in semantic_mappings.items():
            if (any(syn in rule_reason for syn in synonyms) and 
                any(syn in churn_reason for syn in synonyms)):
                return True
        
        return False
    
    async def execute_nudges(self, user_id: str, nudges: List[Dict[str, Any]], 
                            user_features: Optional[Dict[str, Any]] = None) -> List[NudgeAction]:
        """Execute nudges - create actual coupons for discount nudges and send custom messages"""
        executed_nudges = []
        
        # Get churn context from the nudge execution context
        churn_reasons = getattr(self, '_current_churn_reasons', [])
        churn_probability = getattr(self, '_current_churn_probability', 0.8)
        
        # Send custom message for all nudge triggers
        try:
            await self._send_custom_message(user_id, churn_probability, churn_reasons, user_features)
        except Exception as e:
            logger.error(f"Error sending custom message to user {user_id}: {e}")
        
        for nudge in nudges:
            logger.info(f"NUDGE EXECUTED - User: {user_id}, Type: {nudge['type']}, "
                       f"Channel: {nudge['channel']}, Template: {nudge['content_template']}")
            
            # If it's a discount coupon, assign it to the user via QuickMart API
            if nudge["type"] == "Discount Coupon":
                try:
                    coupon_assigned = await self._assign_discount_coupon(
                        user_id, nudge, churn_reasons, churn_probability
                    )
                    if coupon_assigned:
                        logger.info(f"Successfully assigned discount coupon to user {user_id}")
                    else:
                        logger.error(f"Failed to assign discount coupon to user {user_id}")
                except Exception as e:
                    logger.error(f"Error assigning discount coupon to user {user_id}: {e}")
            
            executed_nudges.append(NudgeAction(
                type=nudge["type"],
                content_template=nudge["content_template"],
                channel=nudge["channel"],
                priority=nudge["priority"]
            ))
        
        return executed_nudges
    
    async def _assign_discount_coupon(self, user_id: str, nudge: Dict[str, Any], churn_reasons: List[str] = None, churn_probability: float = 0.8) -> bool:
        """Assign a discount coupon to user via QuickMart API based on churn reasons"""
        try:
            # Use single URL from environment variable
            quickmart_url = settings.QUICKMART_API_URL
            
            # Select coupon based on churn reasons and probability
            # Duplicate prevention is handled at the backend level
            coupon_id = self._select_coupon_based_on_reasons(churn_reasons, churn_probability)
            
            # Generate unique nudge ID for tracking
            import uuid
            nudge_id = f"nudge_{uuid.uuid4().hex[:8]}"
            
            logger.info(f"Selected coupon {coupon_id} for user {user_id} based on reasons: {churn_reasons}")
            
            # Prepare assignment data
            assignment_data = {
                "user_id": user_id,
                "coupon_id": coupon_id,
                "nudge_id": nudge_id,
                "churn_score": churn_probability
            }
            
            logger.info(f"Assigning coupon {coupon_id} to user {user_id} via {quickmart_url}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{quickmart_url}/api/coupons/internal/assign-nudge-coupon",
                    params=assignment_data
                )
                
                logger.info(f"Coupon assignment response: {response.status_code} - {response.text}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get("duplicate"):
                        logger.info(f"Coupon {coupon_id} already assigned to user {user_id}, skipping")
                    else:
                        logger.info(f"Successfully assigned new coupon {coupon_id} to user {user_id}")
                    return True
                else:
                    logger.error(f"Failed to assign coupon: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Exception assigning coupon to user {user_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def _send_custom_message(self, user_id: str, churn_probability: float, 
                                   churn_reasons: List[str], user_features: Optional[Dict[str, Any]] = None) -> bool:
        """Send custom personalized message via the custom message API"""
        try:
            # Use the RecoEngine's own API (internal call to /messages/custom endpoint)
            # Build URL using settings to ensure we use the correct host and port
            api_url = f"http://{settings.API_HOST}:{settings.API_PORT}"
            
            request_data = {
                "user_id": user_id,
                "churn_probability": churn_probability,
                "churn_reasons": churn_reasons,
                "user_features": user_features,
                "store_in_db": True  # Always store when triggered by nudge engine
            }
            
            logger.info(f"Sending custom message request for user {user_id} via {api_url}/messages/custom")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{api_url}/messages/custom",
                    json=request_data
                )
                
                logger.info(f"Custom message response: {response.status_code} - {response.text[:200]}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    message_id = response_data.get("message_id", "unknown")
                    logger.info(f"Successfully sent custom message {message_id} to user {user_id}")
                    return True
                else:
                    logger.error(f"Failed to send custom message: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Exception sending custom message to user {user_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def _get_user_existing_coupons(self, user_id: str, quickmart_url: str) -> List[str]:
        """Get list of coupon codes already assigned to the user"""
        try:
            # For now, we'll use a simple approach - check if user has been assigned coupons before
            # by maintaining a simple in-memory cache or checking assignment history
            # This is a simplified implementation - in production, you'd want proper user session management
            
            # Since we don't have user authentication context here, we'll use a different approach:
            # Check the assignment history by looking at recent assignments for this user
            # For now, return empty list and let the assignment proceed
            # The actual duplicate prevention will happen at the database level in QuickMart
            
            logger.info(f"Checking existing coupons for user {user_id} (simplified check)")
            return []  # Simplified approach - let QuickMart handle duplicates
                    
        except Exception as e:
            logger.warning(f"Error getting existing coupons for user {user_id}: {e}")
            return []  # Return empty list on error to allow coupon assignment
    
    def _select_coupon_based_on_reasons(self, churn_reasons: List[str], churn_probability: float) -> str:
        """Select the most appropriate coupon based on churn reasons and probability"""
        
        # Convert reasons to lowercase for matching
        reasons_lower = [reason.lower() for reason in churn_reasons] if churn_reasons else []
        
        # Define coupon selection logic based on churn reasons
        coupon_mapping = {
            # Price sensitivity - offer percentage discount
            "price": "SUMMER25",  # 25% off
            "expensive": "SUMMER25",
            "cost": "SUMMER25",
            "discount": "SUMMER25",
            
            # Inactivity/engagement issues - welcome back offer
            "inactive": "WELCOME_BACK20",  # 20% welcome back
            "login": "WELCOME_BACK20",
            "engagement": "WELCOME_BACK20",
            "session": "WELCOME_BACK20",
            
            # Purchase behavior - fixed amount discount
            "purchase": "SAVE20",  # $20 off orders over $100
            "order": "SAVE20",
            "buying": "SAVE20",
            "transaction": "SAVE20",
            
            # Shipping/delivery issues - free shipping
            "shipping": "FREESHIP",  # Free shipping
            "delivery": "FREESHIP",
            "fulfillment": "FREESHIP",
            
            # Electronics category issues - category specific
            "electronics": "ELECTRONICS15",  # 15% off electronics
            "tech": "ELECTRONICS15",
            "device": "ELECTRONICS15",
        }
        
        # Score each coupon based on reason matches
        coupon_scores = {}
        for reason in reasons_lower:
            for keyword, coupon in coupon_mapping.items():
                if keyword in reason:
                    coupon_scores[coupon] = coupon_scores.get(coupon, 0) + 1
        
        # Select coupon with highest score
        if coupon_scores:
            best_coupon = max(coupon_scores.items(), key=lambda x: x[1])[0]
            logger.info(f"Selected coupon {best_coupon} based on reason matching (scores: {coupon_scores})")
            return best_coupon
        
        # Fallback based on churn probability
        if churn_probability >= 0.9:
            return "SUMMER25"  # Highest discount for critical risk
        elif churn_probability >= 0.7:
            return "WELCOME_BACK20"  # Standard welcome back
        elif churn_probability >= 0.5:
            return "SAVE20"  # Moderate fixed discount
        else:
            return "WELCOME10"  # Light discount for low risk
    
    async def trigger_nudges(self, user_id: str, churn_probability: float, risk_segment: str, 
                            churn_reasons: List[str], user_features: Optional[Dict[str, Any]] = None) -> NudgeResponse:
        """Trigger nudges based on churn score and reasons"""
        logger.info(f"Processing nudge request for user {user_id} "
                   f"(score: {churn_probability}, segment: {risk_segment})")
        
        # Store churn context for coupon selection
        self._current_churn_reasons = churn_reasons
        self._current_churn_probability = churn_probability
        
        # Find matching rule
        matching_rule = self.find_matching_rule(churn_probability, churn_reasons)
        
        if not matching_rule:
            logger.info(f"No matching nudge rule found for user {user_id}")
            return NudgeResponse(
                user_id=user_id,
                nudges_triggered=[],
                rule_matched="none",
                timestamp=datetime.utcnow().isoformat()
            )
        
        # Execute nudges (this will also send custom message)
        executed_nudges = await self.execute_nudges(user_id, matching_rule["nudges"], user_features)
        
        logger.info(f"Triggered {len(executed_nudges)} nudges for user {user_id} "
                   f"using {matching_rule['rule_id']}")
        
        return NudgeResponse(
            user_id=user_id,
            nudges_triggered=executed_nudges,
            rule_matched=matching_rule["rule_id"],
            timestamp=datetime.utcnow().isoformat()
        )
    
    def get_rules(self) -> Dict[str, Any]:
        """Get all nudge rules"""
        return {"rules": self.rules, "total_rules": len(self.rules)}
    
    def get_rule(self, rule_id: str) -> Dict[str, Any]:
        """Get specific nudge rule by ID"""
        for rule in self.rules:
            if rule["rule_id"] == rule_id:
                return rule
        return None
    
    def test_rules(self, user_id: str, churn_probability: float, churn_reasons: List[str]) -> Dict[str, Any]:
        """Test which rule would match for given parameters"""
        matching_rule = self.find_matching_rule(churn_probability, churn_reasons)
        
        if not matching_rule:
            return {
                "user_id": user_id,
                "matching_rule": None,
                "message": "No rule matches the given parameters"
            }
        
        return {
            "user_id": user_id,
            "matching_rule": matching_rule["rule_id"],
            "rule_details": matching_rule,
            "would_trigger": len(matching_rule["nudges"])
        }

# Global nudge engine instance
nudge_engine = NudgeEngine()

def get_nudge_health() -> Dict[str, Any]:
    """Get nudge engine health status"""
    return {
        "rules_loaded": len(nudge_engine.rules),
        "timestamp": datetime.utcnow().isoformat()
    }
