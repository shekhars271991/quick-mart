"""
Custom Message Generation Service using LangChain and Google Gemini
"""

import logging
from typing import Dict, Any, Optional, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from config import settings
import aerospike

logger = logging.getLogger(__name__)


class MessageGenerator:
    """Generate personalized marketing messages using LangChain and Gemini"""
    
    def __init__(self, aerospike_client=None):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not configured. Message generation will fail.")
        
        self.llm = None
        self.model_name = settings.GEMINI_MODEL
        self.aerospike_client = aerospike_client  # Store reference to Aerospike client
        
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
        """Build rich user context string from features for personalization"""
        context_parts = []
        
        # Personal info - CRITICAL for personalization
        name = user_features.get('name') or user_features.get('full_name', '')
        if name:
            context_parts.append(f"Name: {name}")
        
        age = user_features.get("age")
        if age:
            context_parts.append(f"Age: {age}")
        
        # Cart information - CRITICAL for cart abandonment messages
        cart_items = user_features.get('cart_items', [])
        if cart_items and len(cart_items) > 0:
            if len(cart_items) == 1:
                product_name = cart_items[0].get('name', 'item')
                product_category = cart_items[0].get('category', '')
                product_brand = cart_items[0].get('brand', '')
                context_parts.append(f"Cart Item: {product_name}")
                if product_category:
                    context_parts.append(f"Category: {product_category}")
                if product_brand:
                    context_parts.append(f"Brand: {product_brand}")
            else:
                product_names = [item.get('name', 'item') for item in cart_items[:2]]
                context_parts.append(f"Cart Items ({len(cart_items)}): {', '.join(product_names)}")
        
        # Customer value & loyalty
        loyalty_tier = user_features.get("loyalty_tier")
        if loyalty_tier:
            context_parts.append(f"Loyalty: {loyalty_tier}")
            
        orders_6m = user_features.get("orders_6m")
        if orders_6m is not None:
            if orders_6m == 0:
                context_parts.append("Type: First-time visitor")
            elif orders_6m < 3:
                context_parts.append(f"Type: Occasional ({orders_6m} orders)")
            else:
                context_parts.append(f"Type: Frequent ({orders_6m} orders)")
        
        avg_order_val = user_features.get("avg_order_val")
        if avg_order_val and avg_order_val > 0:
            context_parts.append(f"Avg Order: ${avg_order_val:.0f}")
        
        # Timing context
        days_last_purch = user_features.get("days_last_purch")
        if days_last_purch is not None and days_last_purch > 0:
            context_parts.append(f"Last Purchase: {days_last_purch} days ago")
        
        return "\n".join(context_parts) if context_parts else "Limited customer information"
    
    def _build_prompt(self, churn_probability: float, churn_reasons: List[str], 
                     user_context: str, user_features: Dict[str, Any]) -> str:
        """Build the prompt for Gemini"""
        reasons_text = ", ".join(churn_reasons) if churn_reasons else "General inactivity"
        probability_percent = churn_probability * 100
        
        # Check if cart abandonment is the primary reason
        is_cart_abandonment = any("cart" in reason.lower() or "abandon" in reason.lower() 
                                 for reason in churn_reasons)
        
        if is_cart_abandonment:
            # Extract name and cart item for explicit use
            name = user_features.get('name') or user_features.get('full_name', '')
            cart_items = user_features.get('cart_items', [])
            product_name = cart_items[0].get('name', '') if cart_items else ''
            age = user_features.get('age', 30)
            
            prompt = f"""Create a personalized SMS for cart abandonment. Use the customer's name and reference their specific product.

CUSTOMER DATA:
Name: {name if name else 'NOT PROVIDED'}
Age: {age}
Cart Item: {product_name if product_name else 'NOT PROVIDED'}
{user_context}

STRICT RULES:
1. START WITH NAME: If name provided, begin message with it. Examples:
   - "Hey Sarah!" or "Sarah,"
   - "Mike," or "Hi Mike!"
   
2. MENTION PRODUCT: If cart item provided, reference it specifically:
   - "your Nike sneakers"
   - "that laptop you picked"
   - "the wireless earbuds"

3. AGE-APPROPRIATE TONE:
   - Age 18-25: Casual + emojis → "Hey Mike! Don't miss out on those sneakers 🔥"
   - Age 26-40: Friendly → "Sarah, your laptop is still available. Complete checkout now!"
   - Age 40-60: Professional → "Robert, your order is ready. Finish your purchase today."
   - Age 60+: Clear, formal → "Hello Margaret, your items await. Please complete your order."

4. MAX 160 characters
5. Do NOT mention discounts
6. Include call-to-action (checkout, complete order, etc.)

Write ONE SMS exactly as it would be sent (max 160 chars):"""
        else:
            # Extract name and age for explicit use
            name = user_features.get('name') or user_features.get('full_name', '')
            age = user_features.get('age', 30)
            orders_6m = user_features.get('orders_6m', 0)
            
            # Determine customer type
            if orders_6m == 0:
                cust_type = "first-time visitor"
            elif orders_6m < 3:
                cust_type = "occasional shopper"
            else:
                cust_type = "frequent customer"
            
            prompt = f"""Create a personalized brand engagement SMS for QuickMart. Use the customer's name.

CUSTOMER DATA:
Name: {name if name else 'NOT PROVIDED'}
Age: {age}
Customer Type: {cust_type}
{user_context}

STRICT RULES:
1. START WITH NAME: If name provided, begin with it. Examples:
   - "Hi Emily!" or "Emily,"
   - "Hey Tom!" or "Tom,"
   
2. AGE-APPROPRIATE TONE & LANGUAGE:
   - Age 18-25: Casual + emoji → "Hey Tom! Check out our new drops 🔥 Shop now!"
   - Age 26-40: Friendly → "Sarah, discover something special today at QuickMart!"
   - Age 40-60: Professional → "Robert, quality products waiting for you at QuickMart."
   - Age 60+: Clear, respectful → "Hello Margaret, shop our trusted collection today."

3. MESSAGE STYLE (vary based on customer):
   - First-time visitor: Welcoming, inviting tone
   - Occasional: Friendly reminder about value
   - Frequent: Appreciation + new arrivals
   - NO "miss you" or "come back" (they're active!)

4. MAX 160 characters
5. Do NOT mention discounts or promotions
6. Include call-to-action (shop, explore, discover, browse)

Write ONE SMS exactly as it would be sent (max 160 chars):"""


        print(prompt)
        
        return prompt
    
    def _fetch_user_profile_from_aerospike(self, user_id: str) -> Dict[str, Any]:
        """Fetch user profile data (name, age, etc.) directly from Aerospike users set"""
        try:
            if not self.aerospike_client:
                logger.warning("No Aerospike client available to fetch user profile")
                return {}
            
            # Get user record from users set
            namespace = settings.AEROSPIKE_NAMESPACE
            key = (namespace, "users", user_id)
            
            logger.info(f"Fetching user profile for {user_id} from Aerospike users set")
            (key, metadata, bins) = self.aerospike_client.get(key)
            
            if bins and 'data' in bins:
                user_data = bins['data']
                profile = user_data.get('profile', {})
                
                # Extract name and age from profile
                profile_data = {
                    'name': profile.get('name', ''),
                    'full_name': profile.get('name', ''),
                    'age': profile.get('age'),
                    'loyalty_tier': profile.get('loyalty_tier', ''),
                    'geo_location': profile.get('location', '')
                }
                
                # Remove empty values
                profile_data = {k: v for k, v in profile_data.items() if v not in [None, '', 0]}
                
                logger.info(f"Fetched profile for {user_id}: name={profile_data.get('name')}, age={profile_data.get('age')}")
                return profile_data
                
        except aerospike.exception.RecordNotFound:
            logger.warning(f"User record not found in Aerospike for {user_id}")
            return {}
        except Exception as e:
            logger.warning(f"Error fetching user profile from Aerospike for {user_id}: {e}")
            return {}
    
    def _fetch_cart_items_from_aerospike(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch cart items from user's realtime features in Aerospike"""
        try:
            if not self.aerospike_client:
                logger.warning("No Aerospike client available to fetch cart items")
                return []
            
            # Get realtime features which contain cart_items
            namespace = settings.AEROSPIKE_NAMESPACE
            key = (namespace, "user_features", f"{user_id}_realtime")
            
            logger.info(f"Fetching cart items for {user_id} from realtime features")
            (key, metadata, bins) = self.aerospike_client.get(key)
            
            if bins:
                # Cart items should be in the realtime features
                cart_items = bins.get('cart_items', [])
                
                if cart_items:
                    logger.info(f"Found {len(cart_items)} cart items for {user_id}: {[item.get('name', 'unknown') for item in cart_items]}")
                    return cart_items
                else:
                    logger.info(f"No cart items found in realtime features for {user_id}")
                    return []
                    
        except aerospike.exception.RecordNotFound:
            logger.info(f"No realtime features found for {user_id} (cart may be empty)")
            return []
        except Exception as e:
            logger.warning(f"Error fetching cart items from Aerospike for {user_id}: {e}")
            return []
    
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
            # Check if we have name in features, if not try to fetch from Aerospike
            if not user_features.get('name') and not user_features.get('full_name'):
                logger.warning(f"No name found in features for {user_id}, fetching from Aerospike users set")
                additional_profile = self._fetch_user_profile_from_aerospike(user_id)
                if additional_profile:
                    user_features.update(additional_profile)
                    logger.info(f"Successfully added profile data: name={additional_profile.get('name')}, age={additional_profile.get('age')}")
            
            # Check if we have cart items in features, if not try to fetch from realtime features
            if not user_features.get('cart_items'):
                logger.info(f"No cart items in features for {user_id}, fetching from realtime features")
                cart_items = self._fetch_cart_items_from_aerospike(user_id)
                if cart_items:
                    user_features['cart_items'] = cart_items
                    logger.info(f"Successfully added {len(cart_items)} cart items to user features")
            
            # Log what features we received for debugging
            logger.info(f"Features received for {user_id}: name={user_features.get('name')}, age={user_features.get('age')}, " +
                       f"cart_items={len(user_features.get('cart_items', []))}, loyalty={user_features.get('loyalty_tier')}")
            
            # Build user context
            user_context = self._build_user_context(user_features)
            
            # Log the context being sent to LLM
            logger.info(f"User context for {user_id}:\n{user_context}")
            
            # Build prompt (pass user_features for direct access to name, cart items, etc.)
            prompt = self._build_prompt(churn_probability, churn_reasons, user_context, user_features)
            
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


# Global message generator instance - will be initialized with Aerospike client later
message_generator = None

def initialize_message_generator(aerospike_client):
    """Initialize the message generator with Aerospike client"""
    global message_generator
    message_generator = MessageGenerator(aerospike_client)
    return message_generator  # Return the instance so main.py can use it

