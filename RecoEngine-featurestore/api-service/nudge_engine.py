from pydantic import BaseModel
from typing import List, Dict, Any
import logging
from datetime import datetime
import httpx
import asyncio
import os

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
            {"type": "Discount Coupon", "content_template": "20% Off Welcome Back", "channel": "app", "priority": 1, "discount_percent": 20, "coupon_code": "WELCOME20"},
            {"type": "Push Notification", "content_template": "We miss you! Get 20% off your next order", "channel": "push", "priority": 2}
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
            {"type": "Push Notification", "content_template": "Template 2", "channel": "push", "priority": 1},
            {"type": "Discount Coupon", "content_template": "Template 2", "channel": "email", "priority": 2}
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
            {"type": "Email", "content_template": "Template 8", "channel": "email", "priority": 1},
            {"type": "Discount Coupon", "content_template": "Template 8", "channel": "email", "priority": 2}
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
    
    async def execute_nudges(self, user_id: str, nudges: List[Dict[str, Any]]) -> List[NudgeAction]:
        """Execute nudges - create actual coupons for discount nudges"""
        executed_nudges = []
        
        for nudge in nudges:
            logger.info(f"NUDGE EXECUTED - User: {user_id}, Type: {nudge['type']}, "
                       f"Channel: {nudge['channel']}, Template: {nudge['content_template']}")
            
            # If it's a discount coupon, create it via QuickMart API
            if nudge["type"] == "Discount Coupon":
                try:
                    coupon_created = await self._create_discount_coupon(user_id, nudge)
                    if coupon_created:
                        logger.info(f"Successfully created discount coupon for user {user_id}")
                    else:
                        logger.error(f"Failed to create discount coupon for user {user_id}")
                except Exception as e:
                    logger.error(f"Error creating discount coupon for user {user_id}: {e}")
            
            executed_nudges.append(NudgeAction(
                type=nudge["type"],
                content_template=nudge["content_template"],
                channel=nudge["channel"],
                priority=nudge["priority"]
            ))
        
        return executed_nudges
    
    async def _create_discount_coupon(self, user_id: str, nudge: Dict[str, Any]) -> bool:
        """Create a discount coupon via QuickMart API"""
        try:
            # Use single URL from environment variable
            quickmart_url = os.getenv("QUICKMART_API_URL", "http://localhost:3010")
            
            # Generate unique coupon code
            import uuid
            from datetime import timedelta
            coupon_code = f"CHURN_{user_id}_{uuid.uuid4().hex[:8].upper()}"
            
            # Fix date calculation
            valid_until = datetime.utcnow() + timedelta(days=30)
            
            coupon_data = {
                "code": coupon_code,
                "name": nudge.get("content_template", "Churn Prevention Discount"),
                "description": f"Personalized discount for {user_id} - Welcome back!",
                "discount_type": "percentage",
                "discount_value": nudge.get("discount_percent", 20),
                "minimum_order_value": 50.0,
                "usage_limit": 1,
                "user_specific": True,
                "applicable_user_ids": [user_id],
                "valid_from": datetime.utcnow().isoformat(),
                "valid_until": valid_until.isoformat(),
                "is_active": True,
                "created_by_system": "churn_prevention"
            }
            
            logger.info(f"Creating coupon {coupon_code} for user {user_id} via {quickmart_url}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{quickmart_url}/api/admin/coupons",
                    json=coupon_data
                )
                
                logger.info(f"Coupon creation response: {response.status_code} - {response.text}")
                
                if response.status_code == 200:
                    logger.info(f"Successfully created coupon {coupon_code} for user {user_id}")
                    return True
                else:
                    logger.error(f"Failed to create coupon: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Exception creating coupon for user {user_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def trigger_nudges(self, user_id: str, churn_probability: float, risk_segment: str, churn_reasons: List[str]) -> NudgeResponse:
        """Trigger nudges based on churn score and reasons"""
        logger.info(f"Processing nudge request for user {user_id} "
                   f"(score: {churn_probability}, segment: {risk_segment})")
        
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
        
        # Execute nudges
        executed_nudges = await self.execute_nudges(user_id, matching_rule["nudges"])
        
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
