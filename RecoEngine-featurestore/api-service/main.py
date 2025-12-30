from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import aerospike
import httpx
import os
import sys
import json
from datetime import datetime
import logging
from contextlib import asynccontextmanager
from model_predictor import churn_predictor, get_model_health
from nudge_engine import nudge_engine, get_nudge_health, NudgeResponse
from training_service import ModelTrainer, get_training_status
import message_generator as msg_gen_module
from message_generator import initialize_message_generator
from config import settings

# Agent flow toggle - set USE_AGENT_FLOW=true to use LangGraph agent
USE_AGENT_FLOW = os.getenv("USE_AGENT_FLOW", "false").lower() == "true"
# Store toggle - set USE_LANGGRAPH_STORE=true to use LangGraph Store for feature retrieval
USE_LANGGRAPH_STORE = os.getenv("USE_LANGGRAPH_STORE", "true").lower() == "true"
AGENT_IMPORT_ERROR = None

# Agent imports (only loaded when needed) - Requires Python 3.10+ and LangGraph 1.0+
if USE_AGENT_FLOW:
    try:
        from agent import run_agent_prediction, get_aerospike_saver, configure_tools as configure_agent_tools
        from agent.store_helper import (
            get_aerospike_store, 
            store_user_features as store_via_langgraph,
            retrieve_all_user_features as retrieve_via_langgraph
        )
        # Recommendations graph imports
        from agent import (
            run_recommendations_workflow,
            index_products_in_store,
            check_products_indexed,
        )
        print("Agent module loaded successfully (LangGraph 1.0+, Python 3.10+)")
        print(f"LangGraph Store: {'enabled' if USE_LANGGRAPH_STORE else 'disabled'}")
    except ImportError as e:
        AGENT_IMPORT_ERROR = str(e)
        print(f"Agent module import failed: {e}")
        print("   Falling back to manual flow.")
        USE_AGENT_FLOW = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    global client
    connect_aerospike()
    # Initialize message generator with Aerospike client
    if client:
        msg_gen_module.message_generator = initialize_message_generator(client)
        logger.info("Message generator initialized with Aerospike client")
    else:
        # Fallback - initialize without Aerospike client (name fetching won't work)
        msg_gen_module.message_generator = initialize_message_generator(None)
        logger.warning("Message generator initialized WITHOUT Aerospike client - name fetching will be limited")
    
    # Initialize agent tools if agent flow is enabled
    if USE_AGENT_FLOW:
        logger.info("🤖 Agent flow ENABLED - initializing LangGraph agent tools")
        configure_agent_tools(
            aerospike_client=client,
            churn_predictor=churn_predictor,
            nudge_engine=nudge_engine,
            message_generator=msg_gen_module.message_generator,
            namespace=AEROSPIKE_NAMESPACE
        )
        logger.info("✅ Agent tools configured successfully")
        
        # Initialize LangGraph Store if enabled
        if USE_LANGGRAPH_STORE and client:
            try:
                store = get_aerospike_store(client=client, namespace=AEROSPIKE_NAMESPACE)
                logger.info("📦 LangGraph Store initialized for feature retrieval")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize LangGraph Store: {e}")
        
        # Initialize recommendation store with embeddings for vector search
        global reco_store, products_indexed
        try:
            from sentence_transformers import SentenceTransformer
            from langgraph.store.aerospike import AerospikeStore
            
            # Load embedding model
            logger.info("🔄 Loading embedding model for product recommendations...")
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensions
            
            # Create embeddings wrapper for LangGraph Store
            # Must have embed_documents and embed_query methods
            class STEmbeddings:
                def __init__(self, model):
                    self.model = model
                
                def embed_documents(self, texts: list[str]) -> list[list[float]]:
                    """Embed a list of documents."""
                    return self.model.encode(texts).tolist()
                
                def embed_query(self, text: str) -> list[float]:
                    """Embed a single query text."""
                    return self.model.encode(text).tolist()
                
                # Make it callable for ensure_embeddings compatibility
                def __call__(self, text: str) -> list[float]:
                    """Allow calling as a function."""
                    return self.embed_query(text)
            
            embeddings = STEmbeddings(embedding_model)
            
            # Create store with vector search config
            reco_store = AerospikeStore(
                client=client,
                namespace=AEROSPIKE_NAMESPACE,
                set="products",  # Aerospike set name
                index_config={
                    "embed": embeddings,
                    "vector_dims": 384,  # all-MiniLM-L6-v2 dimensions
                    "fields": ["embedding_text"]
                }
            )
            
            logger.info("✅ Recommendation store initialized with vector search")
            
            # Check if products are already indexed
            products_indexed = await check_products_indexed(reco_store)
            if products_indexed:
                logger.info("✅ Products already indexed in store")
            else:
                logger.info("📦 Products not indexed yet. They will be indexed when QuickMart's /api/admin/load-products is called.")
                
        except ImportError as e:
            logger.warning(f"⚠️ Could not initialize embeddings (install sentence-transformers): {e}")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize recommendation store: {e}")
    else:
        logger.info("📋 Manual flow ENABLED - using step-by-step processing")
    
    yield
    # Shutdown (if needed)
    pass

app = FastAPI(title="Churn Prediction API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from settings
AEROSPIKE_HOST = settings.AEROSPIKE_HOST
AEROSPIKE_PORT = settings.AEROSPIKE_PORT
AEROSPIKE_NAMESPACE = settings.AEROSPIKE_NAMESPACE
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:8001")
# NUDGE_SERVICE_URL = os.getenv("NUDGE_SERVICE_URL", "http://localhost:8002")  # No longer needed - integrated

# Aerospike client (will be initialized on startup)
client = None

# Global store instance for vector search (with embeddings)
reco_store = None
products_indexed = False

def connect_aerospike():
    """Connect to Aerospike with retry logic"""
    global client
    config = {
        'hosts': [(AEROSPIKE_HOST, AEROSPIKE_PORT)],
        'policies': {
            'write': {'key': aerospike.POLICY_KEY_SEND}
        }
    }
    try:
        logger.info(f"Attempting to connect to Aerospike at {AEROSPIKE_HOST}:{AEROSPIKE_PORT}")
        client = aerospike.client(config).connect()
        logger.info("Connected to Aerospike successfully")
        # Test the connection
        info = client.info_all("build")
        logger.info(f"Aerospike info: {info}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Aerospike: {str(e)}")
        client = None
        return False

# Pydantic models
class UserProfileFeatures(BaseModel):
    user_id: str
    acc_age_days: Optional[int] = None
    member_dur: Optional[int] = None
    loyalty_tier: Optional[str] = None
    geo_location: Optional[str] = None
    device_type: Optional[str] = None
    pref_payment: Optional[str] = None
    lang_pref: Optional[str] = None

class UserBehaviorFeatures(BaseModel):
    user_id: str
    days_last_login: Optional[int] = None
    days_last_purch: Optional[int] = None
    sess_7d: Optional[int] = None
    sess_30d: Optional[int] = None
    avg_sess_dur: Optional[float] = None
    ctr_10_sess: Optional[float] = None
    cart_abandon: Optional[float] = None
    wishlist_ratio: Optional[float] = None
    content_engage: Optional[float] = None

class TransactionalFeatures(BaseModel):
    user_id: str
    avg_order_val: Optional[float] = None
    orders_6m: Optional[int] = None
    purch_freq_90d: Optional[float] = None
    last_hv_purch: Optional[int] = None
    refund_rate: Optional[float] = None
    sub_pay_status: Optional[str] = None
    discount_dep: Optional[float] = None
    cat_spend_dist: Optional[Dict[str, float]] = None

class EngagementFeatures(BaseModel):
    user_id: str
    push_open_rate: Optional[float] = None
    email_ctr: Optional[float] = None
    inapp_ctr: Optional[float] = None
    promo_resp_time: Optional[float] = None
    retention_resp: Optional[str] = None

class SupportFeatures(BaseModel):
    user_id: str
    tickets_90d: Optional[int] = None
    avg_ticket_res: Optional[float] = None
    csat_score: Optional[float] = None
    refund_req: Optional[int] = None

class RealTimeSessionFeatures(BaseModel):
    user_id: str
    curr_sess_clk: Optional[int] = None
    checkout_time: Optional[float] = None
    cart_no_buy: Optional[bool] = None
    bounce_flag: Optional[bool] = None
    cart_items: Optional[List[Dict[str, Any]]] = None  # Cart items for personalized messages
    abandon_count: Optional[int] = None  # Track how many times user abandoned cart
    last_abandon_at: Optional[str] = None  # Timestamp of last abandonment
    cart_items_count: Optional[int] = None  # Number of items in cart when abandoned

class ChurnPredictionResponse(BaseModel):
    user_id: str
    churn_probability: float
    risk_segment: str
    churn_reasons: List[str]
    confidence_score: float
    features_retrieved: Dict[str, Any]
    feature_freshness: str
    prediction_timestamp: str
    nudges_triggered: Optional[List[Dict[str, Any]]] = None
    nudge_rule_matched: Optional[str] = None

class MonitoringMetrics(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    api_performance: Dict[str, Any]
    feature_freshness: Dict[str, Any]
    model_accuracy: Dict[str, Any]
    nudge_responses: Dict[str, Any]

class CustomMessageRequest(BaseModel):
    user_id: str
    churn_probability: float
    churn_reasons: List[str]
    user_features: Optional[Dict[str, Any]] = None
    store_in_db: bool = True  # Optional flag to store in Aerospike (default: True for production use)

class CustomMessageResponse(BaseModel):
    user_id: str
    message: str
    churn_probability: float
    churn_reasons: List[str]
    user_context_used: str
    generated_at: str
    stored: bool
    message_id: Optional[str] = None

# Helper functions
def store_features_in_aerospike(user_id: str, features: Dict[str, Any], feature_type: str):
    """Store features in Aerospike using LangGraph Store API.
    
    Data format:
    - namespace: ("user_features", feature_type)
    - key: user_id
    - value: {features..., timestamp, feature_type}
    """
    global client
    
    # Use LangGraph Store API when enabled
    if USE_AGENT_FLOW and USE_LANGGRAPH_STORE:
        try:
            store = get_aerospike_store(client=client, namespace=AEROSPIKE_NAMESPACE)
            store_via_langgraph(store, user_id, features, feature_type)
            logger.info(f"Stored {feature_type} features for user {user_id} via LangGraph Store API")
            return
        except Exception as e:
            logger.error(f"Error storing features via Store API for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to store features: {str(e)}")
    
    # Fallback to direct Aerospike client (when Store API is disabled)
    if client is None:
        if not connect_aerospike():
            raise HTTPException(status_code=503, detail="Aerospike not available")
    
    try:
        namespace = AEROSPIKE_NAMESPACE
        set_name = "user_features"
        key_name = user_id + "_" + feature_type
        key = (namespace, set_name, key_name)
        
        existing_features = {}
        try:
            (key, metadata, bins) = client.get(key)
            if bins:
                existing_features = {k: v for k, v in bins.items() if k not in ["timestamp", "feature_type"]}
                logger.info(f"Found existing {feature_type} features for user {user_id}, merging with new features")
        except aerospike.exception.RecordNotFound:
            logger.info(f"No existing {feature_type} features for user {user_id}, creating new record")
        except Exception as e:
            logger.warning(f"Error retrieving existing features for user {user_id}: {e}")
        
        merged_features = {**existing_features, **features}
        
        features_with_timestamp = {
            **merged_features,
            "timestamp": datetime.utcnow().isoformat(),
            "feature_type": feature_type
        }
        
        client.put(key, features_with_timestamp)
        logger.info(f"Stored {feature_type} features for user {user_id} (direct client)")
    except Exception as e:
        logger.error(f"Error storing features for user {user_id}: {str(e)}")
        client = None
        raise HTTPException(status_code=500, detail=f"Failed to store features: {str(e)}")

def retrieve_all_features(user_id: str) -> Dict[str, Any]:
    """Retrieve all feature types for a user from Aerospike using LangGraph Store API.
    
    Data format expected:
    - namespace: ("user_features", feature_type)
    - key: user_id
    - value: {features..., timestamp, feature_type}
    """
    global client
    
    # Use LangGraph Store API when enabled
    if USE_AGENT_FLOW and USE_LANGGRAPH_STORE:
        try:
            store = get_aerospike_store(client=client, namespace=AEROSPIKE_NAMESPACE)
            all_features, feature_freshness = retrieve_via_langgraph(store, user_id)
            logger.info(f"Retrieved {len(all_features)} features for user {user_id} via LangGraph Store API")
            return all_features, feature_freshness
        except Exception as e:
            logger.error(f"Error retrieving features via Store API for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve features: {str(e)}")
    
    # Fallback to direct Aerospike client (when Store API is disabled)
    if client is None:
        if not connect_aerospike():
            raise HTTPException(status_code=503, detail="Aerospike not available")
    
    feature_types = ["profile", "behavior", "transactional", "engagement", "support", "realtime"]
    all_features = {}
    feature_freshness = None
    
    for feature_type in feature_types:
        try:
            namespace = AEROSPIKE_NAMESPACE
            set_name = "user_features"
            key_name = user_id + "_" + feature_type
            key = (namespace, set_name, key_name)
            (key, metadata, bins) = client.get(key)
            if bins:
                features = {k: v for k, v in bins.items() if k not in ["timestamp", "feature_type"]}
                all_features.update(features)
                if not feature_freshness or bins.get("timestamp", "") > feature_freshness:
                    feature_freshness = bins.get("timestamp")
        except aerospike.exception.RecordNotFound:
            logger.warning(f"No {feature_type} features found for user {user_id}")
        except Exception as e:
            logger.error(f"Error retrieving {feature_type} features for user {user_id}: {str(e)}")
            client = None
    
    return all_features, feature_freshness or datetime.utcnow().isoformat()

def store_custom_message_in_aerospike(user_id: str, message_id: str, message: str, 
                                     churn_probability: float, churn_reasons: List[str],
                                     user_features: Optional[Dict[str, Any]] = None):
    """Store custom user message in Aerospike"""
    global client
    
    # Try to reconnect if client is None
    if client is None:
        if not connect_aerospike():
            raise HTTPException(status_code=503, detail="Aerospike not available")
    
    try:
        namespace = AEROSPIKE_NAMESPACE
        set_name = "custom_user_messages"
        key_name = f"{user_id}_{message_id}"
        key = (namespace, set_name, key_name)
        
        message_record = {
            "user_id": user_id,
            "message_id": message_id,
            "message": message,
            "churn_prob": churn_probability,  # Shortened to stay under 15 char limit
            "churn_reasons": churn_reasons,
            "user_ftrs": user_features or {},  # Shortened to stay under 15 char limit
            "created_at": datetime.utcnow().isoformat(),
            "status": "generated"
        }
        
        # Wrap in 'data' bin to match QuickMart backend's expected format
        bins = {"data": message_record}
        client.put(key, bins)
        logger.info(f"Stored custom message {message_id} for user {user_id} in Aerospike")
        
        return True
    except Exception as e:
        logger.error(f"Error storing custom message for user {user_id}: {str(e)}")
        # Try to reconnect on error
        client = None
        raise HTTPException(status_code=500, detail=f"Failed to store custom message: {str(e)}")

# API Endpoints

@app.get("/")
async def root():
    return {"message": "Churn Prediction API", "version": "1.0.0"}

@app.post("/ingest/profile")
async def ingest_profile_features(features: UserProfileFeatures):
    """Feature Ingestion API - User Profile Features"""
    feature_dict = features.model_dump(exclude_unset=True)  # Pydantic v2
    user_id = feature_dict.pop("user_id")
    store_features_in_aerospike(user_id, feature_dict, "profile")
    return {"status": "success", "message": f"Profile features stored for user {user_id}"}

@app.post("/ingest/behavior")
async def ingest_behavior_features(features: UserBehaviorFeatures):
    """Feature Ingestion API - User Behavior Features"""
    feature_dict = features.model_dump(exclude_unset=True)  # Pydantic v2
    user_id = feature_dict.pop("user_id")
    store_features_in_aerospike(user_id, feature_dict, "behavior")
    return {"status": "success", "message": f"Behavior features stored for user {user_id}"}

@app.post("/ingest/transactional")
async def ingest_transactional_features(features: TransactionalFeatures):
    """Feature Ingestion API - Transactional Features"""
    feature_dict = features.model_dump(exclude_unset=True)  # Pydantic v2
    user_id = feature_dict.pop("user_id")
    store_features_in_aerospike(user_id, feature_dict, "transactional")
    return {"status": "success", "message": f"Transactional features stored for user {user_id}"}

@app.post("/ingest/engagement")
async def ingest_engagement_features(features: EngagementFeatures):
    """Feature Ingestion API - Engagement Features"""
    feature_dict = features.model_dump(exclude_unset=True)  # Pydantic v2
    user_id = feature_dict.pop("user_id")
    store_features_in_aerospike(user_id, feature_dict, "engagement")
    return {"status": "success", "message": f"Engagement features stored for user {user_id}"}

@app.post("/ingest/support")
async def ingest_support_features(features: SupportFeatures):
    """Feature Ingestion API - Support Features"""
    feature_dict = features.model_dump(exclude_unset=True)  # Pydantic v2
    user_id = feature_dict.pop("user_id")
    store_features_in_aerospike(user_id, feature_dict, "support")
    return {"status": "success", "message": f"Support features stored for user {user_id}"}

@app.post("/ingest/realtime")
async def ingest_realtime_features(features: RealTimeSessionFeatures):
    """Feature Ingestion API - Real-time Session Features"""
    feature_dict = features.model_dump(exclude_unset=True)  # Pydantic v2
    user_id = feature_dict.pop("user_id")
    store_features_in_aerospike(user_id, feature_dict, "realtime")
    return {"status": "success", "message": f"Real-time features stored for user {user_id}"}


# NOTE: /predict/test MUST be defined BEFORE /predict/{user_id} to avoid route conflict
@app.post("/predict/test")
async def test_predict_flow(
    user_id: str = Query("user_001", description="User ID to test prediction for"),
    force_agent: bool = Query(False, description="Force agent flow regardless of USE_AGENT_FLOW setting"),
    verbose: bool = Query(True, description="Include detailed debug information")
):
    """
    Test endpoint for debugging the prediction flow.
    
    This endpoint allows direct testing of both manual and agent flows
    with detailed debug output for troubleshooting.
    """
    import time
    start_time = time.time()
    
    debug_info = {
        "test_params": {"user_id": user_id, "force_agent": force_agent, "verbose": verbose},
        "environment": {
            "USE_AGENT_FLOW_env": os.getenv("USE_AGENT_FLOW", "false"),
            "USE_AGENT_FLOW_active": USE_AGENT_FLOW,
            "flow_used": "agent" if (USE_AGENT_FLOW or force_agent) else "manual"
        },
        "steps": [],
        "timing": {}
    }
    
    try:
        if USE_AGENT_FLOW or force_agent:
            debug_info["steps"].append({"step": "init", "message": "Using AGENT flow (LangGraph)"})
            
            # Import agent module (needed whether USE_AGENT_FLOW is true or force_agent)
            try:
                from agent import run_agent_prediction as agent_predict, configure_tools as configure_agent_tools
                if force_agent and not USE_AGENT_FLOW:
                    configure_agent_tools(
                        aerospike_client=client, churn_predictor=churn_predictor,
                        nudge_engine=nudge_engine, message_generator=msg_gen_module.message_generator,
                        namespace=AEROSPIKE_NAMESPACE
                    )
            except ImportError as e:
                raise HTTPException(status_code=500, detail=f"Agent module not available: {str(e)}")
            
            step_start = time.time()
            agent_result = await agent_predict(
                user_id=user_id, 
                aerospike_client=client, 
                use_checkpointer=True,
                use_store=USE_LANGGRAPH_STORE
            )
            debug_info["timing"]["agent_execution"] = f"{(time.time() - step_start)*1000:.2f}ms"
            
            if verbose and agent_result.get("agent_reasoning"):
                debug_info["agent_reasoning"] = agent_result.get("agent_reasoning", [])
            
            debug_info["steps"].append({
                "step": "agent_complete",
                "message": f"Agent workflow completed: {agent_result.get('current_step')}",
                "error": agent_result.get("error")
            })
            
            result = {
                "success": not agent_result.get("error"),
                "flow": "agent",
                "user_id": user_id,
                "prediction": agent_result.get("churn_prediction"),
                "nudge_decision": agent_result.get("nudge_decision"),
                "generated_nudge": agent_result.get("generated_nudge"),
                "feature_count": len(agent_result.get("user_features", {}) or {}),
            }
        else:
            debug_info["steps"].append({"step": "init", "message": "Using MANUAL flow"})
            
            step_start = time.time()
            features, feature_freshness = retrieve_all_features(user_id)
            debug_info["timing"]["feature_retrieval"] = f"{(time.time() - step_start)*1000:.2f}ms"
            debug_info["steps"].append({"step": "features", "message": f"Retrieved {len(features)} features", "feature_freshness": feature_freshness})
            
            if not features:
                raise HTTPException(status_code=404, detail=f"No features found for user {user_id}")
            
            step_start = time.time()
            prediction_data = churn_predictor.predict_churn(features)
            debug_info["timing"]["prediction"] = f"{(time.time() - step_start)*1000:.2f}ms"
            debug_info["steps"].append({
                "step": "prediction",
                "message": f"Churn: {prediction_data['churn_probability']:.1%}, Segment: {prediction_data['risk_segment']}",
                "reasons": prediction_data["churn_reasons"][:3]
            })
            
            step_start = time.time()
            nudge_response = None
            try:
                nudge_response = await nudge_engine.trigger_nudges(
                    user_id=user_id, churn_probability=prediction_data["churn_probability"],
                    risk_segment=prediction_data["risk_segment"], churn_reasons=prediction_data["churn_reasons"],
                    user_features=features
                )
            except Exception as e:
                debug_info["steps"].append({"step": "nudge_error", "message": str(e)})
            
            debug_info["timing"]["nudge_trigger"] = f"{(time.time() - step_start)*1000:.2f}ms"
            debug_info["steps"].append({
                "step": "nudge",
                "message": f"Nudges triggered: {len(nudge_response.nudges_triggered) if nudge_response else 0}",
                "rule_matched": nudge_response.rule_matched if nudge_response else None
            })
            
            result = {
                "success": True, "flow": "manual", "user_id": user_id,
                "prediction": {
                    "churn_probability": prediction_data["churn_probability"],
                    "risk_segment": prediction_data["risk_segment"],
                    "churn_reasons": prediction_data["churn_reasons"],
                    "confidence_score": prediction_data["confidence_score"]
                },
                "nudges_triggered": len(nudge_response.nudges_triggered) if nudge_response else 0,
                "feature_count": len(features),
            }
        
        debug_info["timing"]["total"] = f"{(time.time() - start_time)*1000:.2f}ms"
        if verbose:
            result["debug"] = debug_info
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test prediction failed: {str(e)}")
        debug_info["steps"].append({"step": "error", "message": str(e)})
        debug_info["timing"]["total"] = f"{(time.time() - start_time)*1000:.2f}ms"
        return {"success": False, "error": str(e), "debug": debug_info if verbose else None}


@app.post("/predict/{user_id}")
async def predict_churn(user_id: str) -> ChurnPredictionResponse:
    """
    Churn Prediction API - Fetch features and predict churn probability.
    
    This endpoint supports two execution modes controlled by USE_AGENT_FLOW env var:
    - Manual flow (default): Step-by-step processing with explicit function calls
    - Agent flow: LangGraph-based AI agent with Aerospike checkpointing
    """
    
    # =========================================================================
    # AGENT FLOW: Use LangGraph agent with checkpointing and store
    # =========================================================================
    if USE_AGENT_FLOW:
        logger.info(f"🤖 Using AGENT flow for user {user_id} (store: {USE_LANGGRAPH_STORE})")
        try:
            # Run the agent-based prediction workflow
            agent_result = await run_agent_prediction(
                user_id=user_id,
                aerospike_client=client,
                use_checkpointer=True,
                use_store=USE_LANGGRAPH_STORE
            )
            
            # Check for errors
            if agent_result.get("error"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Agent workflow error: {agent_result['error']}"
                )
            
            # Extract prediction from agent result
            prediction = agent_result.get("churn_prediction", {})
            nudge_decision = agent_result.get("nudge_decision", {})
            generated_nudge = agent_result.get("generated_nudge", {})
            
            if not prediction:
                raise HTTPException(
                    status_code=404,
                    detail=f"No features found for user {user_id}"
                )
            
            # Build nudges_triggered from agent result
            nudges_triggered = None
            if nudge_decision.get("should_nudge") and generated_nudge:
                from nudge_engine import NudgeAction
                nudges_triggered = [
                    NudgeAction(
                        action_type=nudge_decision.get("nudge_type", "general"),
                        content_template=generated_nudge.get("message", ""),
                        channel=generated_nudge.get("channel", "in_app"),
                        priority=1  # Default priority
                    ).model_dump()  # Pydantic v2
                ]
            
            # Build response
            response = ChurnPredictionResponse(
                user_id=user_id,
                churn_probability=prediction.get("churn_probability", 0.0),
                risk_segment=prediction.get("risk_segment", "unknown"),
                churn_reasons=prediction.get("churn_reasons", []),
                confidence_score=prediction.get("confidence_score", 0.0),
                features_retrieved=agent_result.get("user_features", {}),
                feature_freshness=agent_result.get("feature_freshness", datetime.utcnow().isoformat()),
                prediction_timestamp=datetime.utcnow().isoformat(),
                nudges_triggered=nudges_triggered,
                nudge_rule_matched=nudge_decision.get("rule_matched")
            )
            
            logger.info(f"🤖 Agent flow completed for user {user_id}")
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Agent flow error for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Agent prediction failed: {str(e)}")
    
    # =========================================================================
    # MANUAL FLOW: Original step-by-step processing
    # =========================================================================
    logger.info(f"📋 Using MANUAL flow for user {user_id}")
    try:
        # Retrieve all features from Aerospike
        features, feature_freshness = retrieve_all_features(user_id)
        
        if not features:
            raise HTTPException(status_code=404, detail=f"No features found for user {user_id}")
        
        # Log key features for debugging
        logger.info(f"Predicting churn for user {user_id}")
        logger.info(f"Key features - abandon_count: {features.get('abandon_count', 0)}, "
                   f"cart_abandon: {features.get('cart_abandon')}, "
                   f"sess_7d: {features.get('sess_7d')}, "
                   f"days_last_purch: {features.get('days_last_purch')}, "
                   f"days_last_login: {features.get('days_last_login')}, "
                   f"cart_no_buy: {features.get('cart_no_buy')}, "
                   f"orders_6m: {features.get('orders_6m')}, "
                   f"csat_score: {features.get('csat_score')}, "
                   f"push_open_rate: {features.get('push_open_rate')}, "
                   f"loyalty_enc: {features.get('loyalty_enc')}")
        
        # Call local model for prediction
        prediction_data = churn_predictor.predict_churn(features)
        
        logger.info(f"Prediction result - probability: {prediction_data['churn_probability']:.3f}, "
                   f"risk_segment: {prediction_data['risk_segment']}")
        logger.info(f"Top churn reasons: {prediction_data.get('churn_reasons', [])[:3]}")
        
        # Trigger nudges using integrated nudge engine
        # Now triggers for ALL users to send engagement messages
        nudge_response = None
        try:
            nudge_response = await nudge_engine.trigger_nudges(
                user_id=user_id,
                churn_probability=prediction_data["churn_probability"],
                risk_segment=prediction_data["risk_segment"],
                churn_reasons=prediction_data["churn_reasons"],
                user_features=features  # Pass user features for personalized message generation
            )
            if nudge_response:
                logger.info(f"Nudges triggered for user {user_id}: {len(nudge_response.nudges_triggered)} actions")
        except Exception as e:
            logger.error(f"Failed to trigger nudge for user {user_id}: {str(e)}")
        
        # Prepare response
        response = ChurnPredictionResponse(
            user_id=user_id,
            churn_probability=prediction_data["churn_probability"],
            risk_segment=prediction_data["risk_segment"],
            churn_reasons=prediction_data["churn_reasons"],
            confidence_score=prediction_data["confidence_score"],
            features_retrieved=features,
            feature_freshness=feature_freshness,
            prediction_timestamp=datetime.utcnow().isoformat(),
            nudges_triggered=[nudge.model_dump() for nudge in nudge_response.nudges_triggered] if nudge_response else None,  # Pydantic v2
            nudge_rule_matched=nudge_response.rule_matched if nudge_response else None
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error predicting churn for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


# ==================== Recommendations Endpoints ====================

class RecommendationRequest(BaseModel):
    """Request model for triggering recommendations."""
    cart_items: Optional[List[Dict[str, Any]]] = None


class RecommendedProductResponse(BaseModel):
    """Response model for a recommended product."""
    product_id: str
    name: str
    description: str
    category: str
    brand: str
    price: float
    original_price: Optional[float] = None
    discounted_price: float
    discount_percentage: int
    rating: float
    review_count: int
    image: Optional[str] = None
    similarity_score: float
    recommendation_reason: str


class RecommendationsResponse(BaseModel):
    """Response model for recommendations."""
    user_id: str
    recommendations: List[RecommendedProductResponse]
    churn_risk: str
    churn_probability: float
    generated_at: str
    source: str  # "cached" or "generated"


# NOTE: Static routes MUST come before dynamic {user_id} routes in FastAPI

class ProductIndexRequest(BaseModel):
    """Request model for indexing products."""
    products: Optional[List[Dict[str, Any]]] = None


@app.post("/recommendations/index")
async def index_products(request: Optional[ProductIndexRequest] = None):
    """
    Index products for vector search.
    
    Products can be:
    1. Passed directly in the request body (preferred)
    2. Fetched from QuickMart backend (fallback, requires public endpoint)
    
    This endpoint is automatically called by QuickMart's /api/admin/load-products.
    """
    global reco_store, products_indexed
    
    if not USE_AGENT_FLOW or reco_store is None:
        raise HTTPException(
            status_code=503,
            detail="Recommendation store not available"
        )
    
    try:
        logger.info("📦 Starting product indexing...")
        
        # Use provided products or fetch from backend
        products = request.products if request and request.products else None
        
        indexed_count = await index_products_in_store(reco_store, products)
        
        if indexed_count > 0:
            products_indexed = True
            logger.info(f"✅ Successfully indexed {indexed_count} products")
            return {
                "status": "success",
                "products_indexed": indexed_count,
                "message": f"Indexed {indexed_count} products for vector search"
            }
        else:
            return {
                "status": "warning",
                "products_indexed": 0,
                "message": "No products found to index."
            }
            
    except Exception as e:
        logger.error(f"Error indexing products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Product indexing failed: {str(e)}")


@app.get("/recommendations/status")
async def get_recommendations_status():
    """Get recommendations system status."""
    return {
        "enabled": USE_AGENT_FLOW and reco_store is not None,
        "store_initialized": reco_store is not None,
        "products_indexed": products_indexed,
        "embedding_model": "all-MiniLM-L6-v2" if reco_store else None,
        "embedding_dimensions": 384 if reco_store else None
    }


@app.post("/recommendations/{user_id}")
async def trigger_recommendations(
    user_id: str,
    request: Optional[RecommendationRequest] = None
):
    """
    Trigger product recommendations for a user (called on login).
    
    This runs the recommendations LangGraph workflow which:
    1. Gets user's cart items
    2. Retrieves user features
    3. Estimates churn risk
    4. Uses vector search to find similar products
    5. Applies discounts based on churn risk
    6. Caches recommendations for later retrieval
    """
    global reco_store, churn_predictor
    
    if not USE_AGENT_FLOW:
        raise HTTPException(
            status_code=503, 
            detail="Agent flow not enabled. Set USE_AGENT_FLOW=true"
        )
    
    if reco_store is None:
        raise HTTPException(
            status_code=503,
            detail="Recommendation store not initialized. Check embeddings setup."
        )
    
    if not products_indexed:
        raise HTTPException(
            status_code=503,
            detail="Products not indexed. Call POST /recommendations/index first."
        )
    
    cart_items = request.cart_items if request else None
    
    try:
        logger.info(f"🎯 Running recommendations workflow for user {user_id}")
        
        # Get the user features store (same one used by /ingest endpoints)
        features_store = get_aerospike_store(client=client, namespace=AEROSPIKE_NAMESPACE)
        
        result = await run_recommendations_workflow(
            user_id=user_id,
            product_store=reco_store,       # For vector search (set="products")
            features_store=features_store,   # For user features (set="user_features")
            churn_predictor=churn_predictor,
            cart_items=cart_items
        )
        
        if result.get("error"):
            logger.error(f"Recommendations workflow error: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])
        
        recommendations = [
            RecommendedProductResponse(**r) for r in result.get("recommendations", [])
        ]
        
        return RecommendationsResponse(
            user_id=user_id,
            recommendations=recommendations,
            churn_risk=result.get("churn_risk", "low_risk"),
            churn_probability=result.get("churn_probability", 0),
            generated_at=datetime.utcnow().isoformat(),
            source="generated"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendations for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Recommendations failed: {str(e)}")


@app.get("/recommendations/{user_id}")
async def get_recommendations(user_id: str):
    """
    Get cached recommendations for a user.
    
    Returns previously generated recommendations from the store.
    """
    global reco_store
    
    if not USE_AGENT_FLOW or reco_store is None:
        raise HTTPException(
            status_code=503, 
            detail="Recommendation store not available"
        )
    
    try:
        # Retrieve cached recommendations
        item = await reco_store.aget(
            namespace=("user_recommendations",),
            key=user_id
        )
        
        if item is None or not item.value:
            raise HTTPException(
                status_code=404,
                detail=f"No recommendations found for user {user_id}. Call POST /recommendations/{user_id} first."
            )
        
        data = item.value
        recommendations = [
            RecommendedProductResponse(**r) for r in data.get("recommendations", [])
        ]
        
        return RecommendationsResponse(
            user_id=user_id,
            recommendations=recommendations,
            churn_risk=data.get("churn_risk", "low_risk"),
            churn_probability=data.get("churn_probability", 0),
            generated_at=data.get("created_at", ""),
            source="cached"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving recommendations for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


@app.get("/monitoring")
async def get_monitoring_metrics() -> MonitoringMetrics:
    """Monitoring API - Track API performance, feature freshness, and model accuracy"""
    # This is a placeholder implementation for POC
    # In production, this would collect real metrics from various sources
    return MonitoringMetrics(
        api_performance={
            "total_requests": 1000,
            "avg_response_time_ms": 150,
            "error_rate": 0.01
        },
        feature_freshness={
            "avg_feature_age_hours": 2.5,
            "stale_features_count": 5
        },
        model_accuracy={
            "precision": 0.85,
            "recall": 0.78,
            "f1_score": 0.81
        },
        nudge_responses={
            "nudges_sent": 250,
            "response_rate": 0.15,
            "conversion_rate": 0.08
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global client
    
    try:
        aerospike_status = "disconnected"
        if client is not None:
            try:
                # Test basic connection
                info = client.info_all("build")
                aerospike_status = "connected"
            except Exception as e:
                aerospike_status = f"error: {str(e)}"
                client = None
        
        # Get model health
        model_health = get_model_health()
        
        # Get nudge engine health
        nudge_health = get_nudge_health()
        
        # Agent flow status
        agent_status = {
            "enabled": USE_AGENT_FLOW,
            "flow_mode": "agent" if USE_AGENT_FLOW else "manual",
            "checkpointer": "aerospike" if USE_AGENT_FLOW else "none",
            "store": "aerospike" if (USE_AGENT_FLOW and USE_LANGGRAPH_STORE) else "none"
        }
        
        return {
            "status": "healthy" if aerospike_status == "connected" and model_health["model_loaded"] else "degraded",
            "aerospike": aerospike_status,
            "model": model_health,
            "nudge_engine": nudge_health,
            "agent": agent_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/agent/status")
async def get_agent_status():
    """Get detailed agent status and configuration"""
    return {
        "agent_flow_enabled": USE_AGENT_FLOW,
        "flow_mode": "agent" if USE_AGENT_FLOW else "manual",
        "checkpointer": {
            "type": "AerospikeSaver" if USE_AGENT_FLOW else "none",
            "namespace": AEROSPIKE_NAMESPACE if USE_AGENT_FLOW else None
        },
        "store": {
            "enabled": USE_LANGGRAPH_STORE if USE_AGENT_FLOW else False,
            "type": "AerospikeStore" if (USE_AGENT_FLOW and USE_LANGGRAPH_STORE) else "none",
            "namespace": AEROSPIKE_NAMESPACE if (USE_AGENT_FLOW and USE_LANGGRAPH_STORE) else None,
            "set": "user_features" if (USE_AGENT_FLOW and USE_LANGGRAPH_STORE) else None
        }
    }


# Nudge Engine Endpoints
@app.get("/nudge/rules")
async def get_nudge_rules():
    """Get all nudge rules"""
    return nudge_engine.get_rules()

@app.get("/nudge/rules/{rule_id}")
async def get_nudge_rule(rule_id: str):
    """Get specific nudge rule by ID"""
    rule = nudge_engine.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return rule

@app.get("/nudge/test/{user_id}")
async def test_nudge_rules(
    user_id: str, 
    churn_probability: float = Query(..., description="Churn probability (0.0-1.0)"),
    churn_reasons: List[str] = Query(..., description="List of churn reasons")
):
    """Test which rule would match for given parameters"""
    return nudge_engine.test_rules(user_id, churn_probability, churn_reasons)

# Training endpoints
@app.post("/train/generate-data")
async def generate_training_data(
    samples: int = Query(1000, ge=100, le=10000, description="Number of training samples to generate"),
    clear_existing: bool = Query(False, description="Clear existing training data before generating new"),
    random_seed: int = Query(42, description="Random seed for reproducibility")
):
    """Generate synthetic training data using the training data generation script"""
    try:
        logger.info(f"Generating {samples} training samples...")
        
        # Import the training data generator from local module
        try:
            from training_data_generator import TrainingDataGenerator
        except ImportError as e:
            logger.error(f"Failed to import TrainingDataGenerator: {e}")
            raise HTTPException(
                status_code=500,
                detail="Training data generator module not available"
            )
        
        # Initialize generator
        generator = TrainingDataGenerator(
            aerospike_host=os.getenv("AEROSPIKE_HOST", "localhost"),
            aerospike_port=int(os.getenv("AEROSPIKE_PORT", "3000"))
        )
        
        # Connect to Aerospike
        if not generator.connect_aerospike():
            raise HTTPException(
                status_code=503,
                detail="Failed to connect to Aerospike for training data generation"
            )
        
        try:
            # Generate synthetic training data
            logger.info(f"Generating {samples} synthetic training samples...")
            training_data = generator.generate_synthetic_features(
                n_samples=samples,
                random_seed=random_seed
            )
            
            # Store in Aerospike (this will handle clear_existing internally)
            stored_count = generator.store_training_data(training_data, clear_existing)
            
            if stored_count == 0:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to store training data into Aerospike"
                )
            
            # Get final count
            total_count = generator.get_training_data_count()
            
            return {
                "message": "Training data generated successfully",
                "samples_generated": len(training_data),
                "samples_stored": stored_count,
                "total_training_samples": total_count,
                "samples_requested": samples,
                "random_seed": random_seed,
                "cleared_existing": clear_existing,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        finally:
            generator.disconnect_aerospike()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Training data generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Training data generation failed: {str(e)}"
        )

@app.post("/train/start")
async def start_training(
    test_size: float = Query(0.2, ge=0.1, le=0.5, description="Test set size (0.1-0.5)"),
    random_state: int = Query(42, description="Random seed for reproducibility")
):
    """Start model training job using data from Aerospike"""
    try:
        logger.info("Starting model training job...")
        
        # Initialize trainer
        trainer = ModelTrainer(client)
        
        # Load training data
        df, X, y = trainer.load_training_data()
        
        # Validate data quality
        quality_report = trainer.validate_data_quality(df)
        
        if quality_report['quality_score'] < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Data quality too low for training: {quality_report['quality_score']:.1f}/100. Issues: {quality_report['issues']}"
            )
        
        # Train the model
        training_metrics = trainer.train_model(X, y, test_size=test_size, random_state=random_state)
        
        # Save the model
        model_saved = trainer.save_model()
        
        if not model_saved:
            raise HTTPException(
                status_code=500,
                detail="Model training completed but failed to save model"
            )
        
        # Reload the predictor with new model
        try:
            churn_predictor.load_or_create_model()
            logger.info("Churn predictor reloaded with new model")
        except Exception as e:
            logger.warning(f"Failed to reload predictor: {e}")
        
        return {
            "message": "Model training completed successfully",
            "training_metrics": training_metrics,
            "data_quality": quality_report,
            "model_saved": model_saved
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Training job failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Training job failed: {str(e)}"
        )

@app.get("/train/status")
async def get_training_status_endpoint():
    """Get current training status and model information"""
    try:
        status = get_training_status()
        
        # Add model health information
        model_health = get_model_health()
        status.update(model_health)
        
        # Add metrics if available
        if status['metrics_available']:
            try:
                with open("churn_model_metrics.json", 'r') as f:
                    metrics = json.load(f)
                    status['last_training_metrics'] = {
                        'trained_at': metrics.get('trained_at'),
                        'test_accuracy': metrics.get('test_accuracy'),
                        'test_f1': metrics.get('test_f1'),
                        'test_roc_auc': metrics.get('test_roc_auc'),
                        'training_samples': metrics.get('training_samples'),
                        'feature_count': metrics.get('feature_count')
                    }
            except Exception as e:
                logger.warning(f"Failed to load training metrics: {e}")
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get training status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get training status: {str(e)}"
        )

@app.get("/train/metrics")
async def get_training_metrics():
    """Get detailed training metrics from the last training job"""
    try:
        if not os.path.exists("churn_model_metrics.json"):
            raise HTTPException(
                status_code=404,
                detail="No training metrics available. Train a model first."
            )
        
        with open("churn_model_metrics.json", 'r') as f:
            metrics = json.load(f)
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get training metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get training metrics: {str(e)}"
        )

@app.get("/train/data-quality")
async def check_data_quality():
    """Check the quality of training data in Aerospike"""
    try:
        trainer = ModelTrainer(client)
        df, _, _ = trainer.load_training_data()
        quality_report = trainer.validate_data_quality(df)
        
        return quality_report
        
    except Exception as e:
        logger.error(f"Failed to check data quality: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check data quality: {str(e)}"
        )

# Custom Message API Endpoint
@app.post("/messages/custom", response_model=CustomMessageResponse)
async def send_custom_message(request: CustomMessageRequest) -> CustomMessageResponse:
    """
    Generate a custom personalized marketing message for a user
    
    This unified endpoint handles both production and testing use cases:
    1. Uses LangChain and Gemini to generate a personalized message based on:
       - Churn probability and reasons from ML model
       - User demographic and behavioral features
    2. Optionally stores the message in Aerospike in the 'custom_user_messages' set
    
    Args:
        user_id: User identifier
        churn_probability: Churn probability (0.0-1.0)
        churn_reasons: List of churn reasons (e.g., ["INACTIVITY", "CART_ABANDONMENT"])
        user_features: Optional user demographic and behavioral features. 
                      If not provided and store_in_db=True, will attempt to retrieve from Aerospike.
        store_in_db: If True, stores the message in Aerospike (default: True for production use)
    
    Returns:
        Generated message with context information and storage status
    """
    # Ensure message generator is initialized
    if msg_gen_module.message_generator is None:
        logger.warning("Message generator not initialized, initializing now")
        msg_gen_module.message_generator = initialize_message_generator(client)
        if msg_gen_module.message_generator is None:
            raise HTTPException(
                status_code=500,
                detail="Message generator initialization failed. Check Gemini API configuration."
            )
    try:
        import uuid
        
        # Get user features if not provided (only if we're storing in DB, indicating production use)
        user_features = request.user_features
        if not user_features and request.store_in_db:
            logger.info(f"Retrieving user features for {request.user_id}")
            try:
                user_features, _ = retrieve_all_features(request.user_id)
            except Exception as e:
                logger.warning(f"Could not retrieve user features for {request.user_id}: {e}")
                user_features = {}
        elif not user_features:
            user_features = {}
        
        # Generate personalized message using LLM
        logger.info(f"Generating custom message for user {request.user_id} (store_in_db={request.store_in_db})")
        generated_message = await msg_gen_module.message_generator.generate_message(
            user_id=request.user_id,
            churn_probability=request.churn_probability,
            churn_reasons=request.churn_reasons,
            user_features=user_features
        )
        
        if not generated_message:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate custom message. Check LLM configuration and GEMINI_API_KEY."
            )
        
        # Build user context string for response (for debugging/visibility)
        context_parts = []
        if user_features.get("loyalty_tier"):
            context_parts.append(f"Loyalty Tier: {user_features.get('loyalty_tier')}")
        if user_features.get("geo_location"):
            context_parts.append(f"Location: {user_features.get('geo_location')}")
        if user_features.get("age"):
            context_parts.append(f"Age: {user_features.get('age')}")
        if user_features.get("days_last_login") is not None:
            context_parts.append(f"Days since last login: {user_features.get('days_last_login')}")
        if user_features.get("days_last_purch") is not None:
            context_parts.append(f"Days since last purchase: {user_features.get('days_last_purch')}")
        if user_features.get("avg_order_val") is not None:
            context_parts.append(f"Average order value: ${user_features.get('avg_order_val'):.2f}")
        if user_features.get("orders_6m") is not None:
            context_parts.append(f"Orders in last 6 months: {user_features.get('orders_6m')}")
        if user_features.get("cart_abandon") is not None:
            abandon_rate = user_features.get('cart_abandon', 0) * 100
            context_parts.append(f"Cart abandonment rate: {abandon_rate:.1f}%")
        if user_features.get("sess_7d") is not None:
            context_parts.append(f"Sessions in last 7 days: {user_features.get('sess_7d')}")
        
        user_context = ", ".join(context_parts) if context_parts else "Limited user information available"
        
        # Optionally store in Aerospike
        message_id = None
        stored = False
        if request.store_in_db:
            try:
                message_id = f"msg_{uuid.uuid4().hex[:12]}"
                store_custom_message_in_aerospike(
                    user_id=request.user_id,
                    message_id=message_id,
                    message=generated_message,
                    churn_probability=request.churn_probability,
                    churn_reasons=request.churn_reasons,
                    user_features=user_features
                )
                stored = True
                logger.info(f"Message stored in Aerospike with ID: {message_id}")
            except Exception as e:
                logger.warning(f"Failed to store message in Aerospike: {e}")
                # Don't fail the request if storage fails
        
        logger.info(f"Successfully generated custom message for user {request.user_id}")
        
        return CustomMessageResponse(
            user_id=request.user_id,
            message=generated_message,
            churn_probability=request.churn_probability,
            churn_reasons=request.churn_reasons,
            user_context_used=user_context,
            generated_at=datetime.utcnow().isoformat(),
            stored=stored,
            message_id=message_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating custom message for user {request.user_id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate custom message: {str(e)}"
        )

@app.get("/messages/debug/{user_id}")
async def debug_user_messages(user_id: str):
    """Debug endpoint to check messages in Aerospike"""
    global client
    
    if client is None:
        if not connect_aerospike():
            raise HTTPException(status_code=503, detail="Aerospike not available")
    
    try:
        # Scan custom_user_messages set
        namespace = AEROSPIKE_NAMESPACE
        set_name = "custom_user_messages"
        scan = client.scan(namespace, set_name)
        
        messages = []
        def callback(input_tuple):
            key, metadata, bins = input_tuple
            if bins:
                # Check if data is in 'data' bin or directly in bins
                if 'data' in bins:
                    msg_data = bins['data']
                else:
                    msg_data = bins
                
                if isinstance(msg_data, dict) and msg_data.get("user_id") == user_id:
                    msg_data['_key'] = key[2] if len(key) > 2 else None
                    msg_data['_storage_format'] = 'data_bin' if 'data' in bins else 'direct'
                    messages.append(msg_data)
        
        scan.foreach(callback)
        
        return {
            "user_id": user_id,
            "total_messages": len(messages),
            "messages": messages
        }
        
    except Exception as e:
        logger.error(f"Error debugging messages for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to debug messages: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    import sys
    
    # Default values
    host = "0.0.0.0"
    port = 8000
    
    # Parse command line arguments
    if "--host" in sys.argv:
        host_index = sys.argv.index("--host") + 1
        if host_index < len(sys.argv):
            host = sys.argv[host_index]
    
    if "--port" in sys.argv:
        port_index = sys.argv.index("--port") + 1
        if port_index < len(sys.argv):
            port = int(sys.argv[port_index])
    
    uvicorn.run(app, host=host, port=port)
