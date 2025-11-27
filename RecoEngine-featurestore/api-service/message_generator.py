"""
Custom Message Generation Service using LangChain and Google Gemini
"""

import logging
from typing import Dict, Any, Optional, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from config import settings

logger = logging.getLogger(__name__)


class MessageGenerator:
    """Generate personalized marketing messages using LangChain and Gemini"""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not configured. Message generation will fail.")
        
        self.llm = None
        self.model_name = settings.GEMINI_MODEL
        if self.api_key:
            try:
                # Use configured model (default: gemini-1.5-flash for faster, cost-effective generation)
                # Alternative: "gemini-1.5-pro" for higher quality (slower, more expensive)
                self.llm = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    temperature=0.7,
                    max_output_tokens=10000  # Increased from 200 to allow for longer messages
                )
                logger.info(f"Initialized Gemini LLM ({self.model_name}) for message generation")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini LLM: {e}")
                self.llm = None
    
    def _build_user_context(self, user_features: Dict[str, Any]) -> str:
        """Build user context string from features for prompt"""
        context_parts = []
        
        # Demographic info
        if user_features.get("loyalty_tier"):
            context_parts.append(f"Loyalty Tier: {user_features.get('loyalty_tier')}")
        
        if user_features.get("geo_location"):
            context_parts.append(f"Location: {user_features.get('geo_location')}")
        
        if user_features.get("age"):
            context_parts.append(f"Age: {user_features.get('age')}")
        
        # Behavioral context
        if user_features.get("days_last_login") is not None:
            context_parts.append(f"Days since last login: {user_features.get('days_last_login')}")
        
        if user_features.get("days_last_purch") is not None:
            context_parts.append(f"Days since last purchase: {user_features.get('days_last_purch')}")
        
        if user_features.get("avg_order_val") is not None:
            context_parts.append(f"Average order value: ${user_features.get('avg_order_val'):.2f}")
        
        if user_features.get("orders_6m") is not None:
            context_parts.append(f"Orders in last 6 months: {user_features.get('orders_6m')}")
        
        # Engagement metrics
        if user_features.get("cart_abandon") is not None:
            abandon_rate = user_features.get('cart_abandon', 0) * 100
            context_parts.append(f"Cart abandonment rate: {abandon_rate:.1f}%")
        
        if user_features.get("sess_7d") is not None:
            context_parts.append(f"Sessions in last 7 days: {user_features.get('sess_7d')}")
        
        return ", ".join(context_parts) if context_parts else "Limited user information available"
    
    def _build_prompt(self, churn_probability: float, churn_reasons: List[str], 
                     user_context: str) -> str:
        """Build the prompt for Gemini"""
        reasons_text = ", ".join(churn_reasons) if churn_reasons else "General inactivity"
        probability_percent = churn_probability * 100
        
        # Check if cart abandonment is the primary reason
        is_cart_abandonment = any("cart" in reason.lower() or "abandon" in reason.lower() 
                                 for reason in churn_reasons)
        
        if is_cart_abandonment:
            prompt = f"""You are a marketing copywriter for QuickMart, an e-commerce platform. 
Create a SHORT personalized SMS text message to re-engage this customer who abandoned their cart.

{user_context}

Churn Risk: {probability_percent:.1f}%
Primary Reasons: {reasons_text}

Your Task:
1. Analyze the customer data above
2. Personalize the message based on:
   - Use their name if available
   - Reference their loyalty status if they're a valued member
   - Adjust tone based on their shopping history (new vs frequent shopper)
   - Consider their engagement level if relevant
3. Create a cart abandonment reminder that feels personal and relevant to THEM

Requirements:
- Maximum 160 characters (SMS limit)
- Friendly, conversational tone
- Clear call-to-action about completing their order
- Do NOT mention discounts/codes (handled separately)
- Use 1-2 emojis if appropriate (🛒 works well for cart)
- Make it feel like it was written specifically for this person

Generate ONE short SMS message (max 160 chars)."""
        else:
            prompt = f"""You are a marketing copywriter for QuickMart, an e-commerce platform. 
Create a SHORT personalized SMS text message to re-engage this customer at risk of churning.

{user_context}

Churn Risk: {probability_percent:.1f}%
Primary Reasons: {reasons_text}

Your Task:
1. Analyze the customer data above
2. Personalize the message based on:
   - Use their name if available
   - Reference their loyalty status, location, or shopping habits if relevant
   - Adjust tone based on their profile (age, shopping frequency, value)
   - Address the specific churn reasons mentioned
3. Create a re-engagement message that feels personal and relevant to THEM

Requirements:
- Maximum 160 characters (SMS limit)
- Friendly, conversational tone
- Clear call-to-action relevant to their churn reason
- Do NOT mention discounts/codes (handled separately)
- Use 1-2 emojis if appropriate
- Make it feel like it was written specifically for this person

Generate ONE short SMS message (max 160 chars)."""

        return prompt
    
    async def generate_message(self, user_id: str, churn_probability: float, 
                              churn_reasons: List[str], user_features: Dict[str, Any]) -> Optional[str]:
        """
        Generate a personalized marketing message using Gemini
        
        Args:
            user_id: User identifier
            churn_probability: ML churn prediction score (0.0-1.0)
            churn_reasons: List of churn reasons from ML model
            user_features: User demographic and behavioral features
            
        Returns:
            Generated message string or None if generation fails
        """
        if not self.llm:
            logger.error("LLM not initialized. Cannot generate message.")
            return None
        
        try:
            # Build user context
            user_context = self._build_user_context(user_features)
            
            # Build prompt
            prompt = self._build_prompt(churn_probability, churn_reasons, user_context)
            
            logger.info(f"Generating message for user {user_id} with churn probability {churn_probability:.2f}")
            
            # Generate message using LangChain
            messages = [
                SystemMessage(content="You are an expert marketing copywriter specializing in customer retention and re-engagement campaigns."),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Check response metadata for issues
            finish_reason = response.response_metadata.get('finish_reason', '')
            if finish_reason == 'MAX_TOKENS':
                logger.warning(f"Response hit token limit for user {user_id}. Consider increasing max_output_tokens.")
            
            # Extract message from response
            generated_message = response.content.strip() if response.content else ""
            
            # Handle empty or truncated responses
            if not generated_message:
                error_msg = f"Empty response from LLM. Finish reason: {finish_reason}"
                logger.error(f"{error_msg} for user {user_id}")
                # Try to get partial content if available
                if hasattr(response, 'response_metadata') and response.response_metadata:
                    logger.error(f"Response metadata: {response.response_metadata}")
                raise ValueError(error_msg)
            
            logger.info(f"Successfully generated message for user {user_id}: {generated_message[:100]}...")
            
            return generated_message
            
        except Exception as e:
            logger.error(f"Error generating message for user {user_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None


# Global message generator instance
message_generator = MessageGenerator()

