from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import aerospike
import httpx
import os
import json
from datetime import datetime
import logging
from contextlib import asynccontextmanager
from model_predictor import churn_predictor, get_model_health
from nudge_engine import nudge_engine, get_nudge_health, NudgeResponse
from training_service import ModelTrainer, get_training_status
from message_generator import message_generator
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    connect_aerospike()
    yield
    # Shutdown (if needed)
    pass

app = FastAPI(title="Churn Prediction API", version="1.0.0", lifespan=lifespan)

# Configuration from settings
AEROSPIKE_HOST = settings.AEROSPIKE_HOST
AEROSPIKE_PORT = settings.AEROSPIKE_PORT
AEROSPIKE_NAMESPACE = settings.AEROSPIKE_NAMESPACE
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:8001")
# NUDGE_SERVICE_URL = os.getenv("NUDGE_SERVICE_URL", "http://localhost:8002")  # No longer needed - integrated

# Aerospike client (will be initialized on startup)
client = None

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
    """Store features in Aerospike with proper key structure - merges with existing features"""
    global client
    
    # Try to reconnect if client is None
    if client is None:
        if not connect_aerospike():
            raise HTTPException(status_code=503, detail="Aerospike not available")
    
    try:
        namespace = AEROSPIKE_NAMESPACE
        set_name = "user_features"
        key_name = user_id + "_" + feature_type
        key = (namespace, set_name, key_name)
        
        # Retrieve existing features to merge with new ones
        existing_features = {}
        try:
            (key, metadata, bins) = client.get(key)
            if bins:
                # Extract existing features (excluding metadata)
                existing_features = {k: v for k, v in bins.items() if k not in ["timestamp", "feature_type"]}
                logger.info(f"Found existing {feature_type} features for user {user_id}, merging with new features")
        except aerospike.exception.RecordNotFound:
            logger.info(f"No existing {feature_type} features for user {user_id}, creating new record")
        except Exception as e:
            logger.warning(f"Error retrieving existing features for user {user_id}: {e}")
        
        # Merge existing features with new features (new features override existing ones)
        merged_features = {**existing_features, **features}
        
        features_with_timestamp = {
            **merged_features,
            "timestamp": datetime.utcnow().isoformat(),
            "feature_type": feature_type
        }
        
        client.put(key, features_with_timestamp)
        logger.info(f"Stored {feature_type} features for user {user_id} (merged {len(existing_features)} existing + {len(features)} new = {len(merged_features)} total)")
    except Exception as e:
        logger.error(f"Error storing features for user {user_id}: {str(e)}")
        # Try to reconnect on error
        client = None
        raise HTTPException(status_code=500, detail=f"Failed to store features: {str(e)}")

def retrieve_all_features(user_id: str) -> Dict[str, Any]:
    """Retrieve all feature types for a user from Aerospike"""
    global client
    
    # Try to reconnect if client is None
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
                # Remove metadata fields and merge features
                features = {k: v for k, v in bins.items() if k not in ["timestamp", "feature_type"]}
                all_features.update(features)
                if not feature_freshness or bins.get("timestamp", "") > feature_freshness:
                    feature_freshness = bins.get("timestamp")
        except aerospike.exception.RecordNotFound:
            logger.warning(f"No {feature_type} features found for user {user_id}")
        except Exception as e:
            logger.error(f"Error retrieving {feature_type} features for user {user_id}: {str(e)}")
            # Try to reconnect on error
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
    feature_dict = features.dict(exclude_unset=True)
    user_id = feature_dict.pop("user_id")
    store_features_in_aerospike(user_id, feature_dict, "profile")
    return {"status": "success", "message": f"Profile features stored for user {user_id}"}

@app.post("/ingest/behavior")
async def ingest_behavior_features(features: UserBehaviorFeatures):
    """Feature Ingestion API - User Behavior Features"""
    feature_dict = features.dict(exclude_unset=True)
    user_id = feature_dict.pop("user_id")
    store_features_in_aerospike(user_id, feature_dict, "behavior")
    return {"status": "success", "message": f"Behavior features stored for user {user_id}"}

@app.post("/ingest/transactional")
async def ingest_transactional_features(features: TransactionalFeatures):
    """Feature Ingestion API - Transactional Features"""
    feature_dict = features.dict(exclude_unset=True)
    user_id = feature_dict.pop("user_id")
    store_features_in_aerospike(user_id, feature_dict, "transactional")
    return {"status": "success", "message": f"Transactional features stored for user {user_id}"}

@app.post("/ingest/engagement")
async def ingest_engagement_features(features: EngagementFeatures):
    """Feature Ingestion API - Engagement Features"""
    feature_dict = features.dict(exclude_unset=True)
    user_id = feature_dict.pop("user_id")
    store_features_in_aerospike(user_id, feature_dict, "engagement")
    return {"status": "success", "message": f"Engagement features stored for user {user_id}"}

@app.post("/ingest/support")
async def ingest_support_features(features: SupportFeatures):
    """Feature Ingestion API - Support Features"""
    feature_dict = features.dict(exclude_unset=True)
    user_id = feature_dict.pop("user_id")
    store_features_in_aerospike(user_id, feature_dict, "support")
    return {"status": "success", "message": f"Support features stored for user {user_id}"}

@app.post("/ingest/realtime")
async def ingest_realtime_features(features: RealTimeSessionFeatures):
    """Feature Ingestion API - Real-time Session Features"""
    feature_dict = features.dict(exclude_unset=True)
    user_id = feature_dict.pop("user_id")
    store_features_in_aerospike(user_id, feature_dict, "realtime")
    return {"status": "success", "message": f"Real-time features stored for user {user_id}"}

@app.post("/predict/{user_id}")
async def predict_churn(user_id: str) -> ChurnPredictionResponse:
    """Churn Prediction API - Fetch features and predict churn probability"""
    try:
        # Retrieve all features from Aerospike
        features, feature_freshness = retrieve_all_features(user_id)
        
        if not features:
            raise HTTPException(status_code=404, detail=f"No features found for user {user_id}")
        
        # Log key features for debugging
        logger.info(f"Predicting churn for user {user_id}")
        logger.info(f"Key features - cart_abandon: {features.get('cart_abandon')}, "
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
        nudge_response = None
        if prediction_data["risk_segment"] in ["high", "critical"]:
            try:
                nudge_response = await nudge_engine.trigger_nudges(
                    user_id=user_id,
                    churn_probability=prediction_data["churn_probability"],
                    risk_segment=prediction_data["risk_segment"],
                    churn_reasons=prediction_data["churn_reasons"],
                    user_features=features  # Pass user features for personalized message generation
                )
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
            nudges_triggered=[nudge.dict() for nudge in nudge_response.nudges_triggered] if nudge_response else None,
            nudge_rule_matched=nudge_response.rule_matched if nudge_response else None
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error predicting churn for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

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
        
        return {
            "status": "healthy" if aerospike_status == "connected" and model_health["model_loaded"] else "degraded",
            "aerospike": aerospike_status,
            "model": model_health,
            "nudge_engine": nudge_health,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
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
        generated_message = await message_generator.generate_message(
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
