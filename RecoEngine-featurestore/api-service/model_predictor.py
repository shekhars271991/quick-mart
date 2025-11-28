"""
Churn Prediction Model Module
"""
import xgboost as xgb
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
import logging
from datetime import datetime
import joblib
import os
import shap
from feature_config import (
    FEATURE_COLUMNS, FEATURE_MAPPING, CATEGORICAL_MAPPINGS, 
    CATEGORICAL_INDICES, MODEL_PARAMS, SYNTHETIC_DATA_PARAMS
)

# Configure logging
logger = logging.getLogger(__name__)

class ChurnPredictor:
    def __init__(self):
        self.model = None
        self.feature_columns = None
        self.explainer = None
        self.load_or_create_model()
    
    def load_or_create_model(self):
        """Load existing model or create a synthetic one for POC"""
        # Try multiple model paths and formats
        model_paths = [
            "churn_model.joblib",  # Current directory .joblib
            "churn_model.pkl",     # Current directory .pkl
            "../models/churn_model.joblib",  # Models directory .joblib
            "../models/churn_model.pkl",     # Models directory .pkl
            "/app/models/churn_model.joblib", # Absolute path .joblib
            "/app/models/churn_model.pkl"     # Absolute path .pkl
        ]
        
        for model_path in model_paths:
            if os.path.exists(model_path):
                try:
                    self.model = joblib.load(model_path)
                    # Set feature columns for loaded model
                    self._set_feature_columns()
                    # Initialize SHAP explainer
                    self._initialize_shap_explainer()
                    logger.info(f"Loaded existing churn model from: {model_path}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load model from {model_path}: {e}")
                    continue
        
        logger.error("No existing model found. Please train a model first using the training service.")
        self.model = None
        self.feature_columns = FEATURE_COLUMNS
    
    def _set_feature_columns(self):
        """Set feature columns for the model"""
        self.feature_columns = FEATURE_COLUMNS
    
    def _initialize_shap_explainer(self):
        """Initialize SHAP explainer for model interpretability"""
        try:
            if self.model is None:
                logger.warning("Cannot initialize SHAP explainer: model is None")
                return
            
            # For XGBoost models, use TreeExplainer for better performance
            if hasattr(self.model, 'get_booster'):
                self.explainer = shap.TreeExplainer(self.model)
                logger.info("Initialized SHAP TreeExplainer for XGBoost model")
            else:
                # For other models, use Explainer (more general but slower)
                self.explainer = shap.Explainer(self.model)
                logger.info("Initialized SHAP Explainer for model")
                
        except Exception as e:
            logger.error(f"Failed to initialize SHAP explainer: {e}")
            self.explainer = None
    
    
    def prepare_features(self, features: Dict[str, Any]) -> np.ndarray:
        """Prepare features for prediction"""
        # Create feature vector with defaults
        feature_vector = np.zeros(len(self.feature_columns))
        
        # Fill in available features
        for feature_name, value in features.items():
            if feature_name in FEATURE_MAPPING and value is not None:
                idx = FEATURE_MAPPING[feature_name]
                if isinstance(value, (int, float)):
                    feature_vector[idx] = float(value)
                elif isinstance(value, bool):
                    feature_vector[idx] = float(value)
        
        # Handle categorical features with simple encoding
        for cat_feature, mapping in CATEGORICAL_MAPPINGS.items():
            if cat_feature in features and features[cat_feature] is not None:
                encoded_value = mapping.get(features[cat_feature], 0)
                idx = CATEGORICAL_INDICES[cat_feature]
                feature_vector[idx] = float(encoded_value)
        
        return feature_vector.reshape(1, -1)
    
    def predict_churn(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Predict churn probability and generate SHAP-based insights"""
        if self.model is None:
            raise ValueError("Model not loaded. Please train a model first using the training service.")
        
        # Prepare features
        feature_vector = self.prepare_features(features)
        
        # Get prediction probability
        churn_probability = float(self.model.predict_proba(feature_vector)[0][1])
        
        # Apply dynamic boost based on cart abandonment count
        abandon_count = features.get('abandon_count', 0)
        if abandon_count > 0:
            # Boost churn probability based on consecutive abandonments
            # First abandonment: +10%, second: +15%, third+: +20%
            if abandon_count == 1:
                boost = 0.10
            elif abandon_count == 2:
                boost = 0.15
            else:  # 3 or more
                boost = 0.20
            
            original_prob = churn_probability
            churn_probability = min(0.95, churn_probability + boost)
            logger.info(f"🎯 Applied cart abandonment boost: count={abandon_count}, "
                       f"boost=+{boost:.0%}, {original_prob:.2%} → {churn_probability:.2%}")
        
        # Determine risk segment
        if churn_probability >= 0.8:
            risk_segment = "critical"
        elif churn_probability >= 0.6:
            risk_segment = "high"
        elif churn_probability >= 0.4:
            risk_segment = "medium"
        else:
            risk_segment = "low"
        
        # Generate SHAP-based explanations
        shap_explanations = self._generate_shap_explanations(feature_vector)
        
        # Calculate confidence score
        confidence_score = min(0.95, max(0.6, abs(churn_probability - 0.5) * 2))
        
        return {
            "churn_probability": churn_probability,
            "risk_segment": risk_segment,
            "churn_reasons": shap_explanations.get("reasons", []),
            "feature_importance": shap_explanations.get("feature_importance", {}),
            "shap_values": shap_explanations.get("shap_values", {}),
            "confidence_score": confidence_score
        }
    
    def _generate_shap_explanations(self, feature_vector: np.ndarray) -> Dict[str, Any]:
        """Generate SHAP-based explanations for churn prediction"""
        try:
            if self.explainer is None:
                # Fallback to rule-based explanations if SHAP is not available
                logger.warning("SHAP explainer not available, using fallback explanations")
                return self._fallback_explanations(feature_vector)
            
            # Calculate SHAP values
            shap_values = self.explainer.shap_values(feature_vector)
            
            # For binary classification, we want the positive class (churn) SHAP values
            if isinstance(shap_values, list) and len(shap_values) == 2:
                shap_values = shap_values[1]  # Positive class (churn)
            
            # Get SHAP values for this single prediction
            single_shap_values = shap_values[0] if len(shap_values.shape) > 1 else shap_values
            
            # Create feature importance dictionary
            feature_importance = {}
            shap_dict = {}
            
            for i, feature_name in enumerate(self.feature_columns):
                shap_value = float(single_shap_values[i])
                feature_value = float(feature_vector[0][i])
                
                feature_importance[feature_name] = abs(shap_value)
                shap_dict[feature_name] = {
                    "shap_value": shap_value,
                    "feature_value": feature_value,
                    "contribution": "increases_churn" if shap_value > 0 else "decreases_churn"
                }
            
            # Sort features by absolute SHAP value (importance)
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            
            # Generate human-readable reasons from top SHAP features
            reasons = []
            for feature_name, importance in sorted_features[:5]:  # Top 5 features
                if importance > 0.01:  # Only include features with meaningful contribution
                    reason = self._shap_to_reason(feature_name, shap_dict[feature_name])
                    if reason:
                        reasons.append(reason)
            
            return {
                "reasons": reasons,
                "feature_importance": dict(sorted_features[:10]),  # Top 10 features
                "shap_values": shap_dict
            }
            
        except Exception as e:
            logger.error(f"Error generating SHAP explanations: {e}")
            return self._fallback_explanations(feature_vector)
    
    def _shap_to_reason(self, feature_name: str, shap_info: Dict[str, Any]) -> str:
        """Convert SHAP feature contribution to human-readable reason"""
        shap_value = shap_info["shap_value"]
        feature_value = shap_info["feature_value"]
        
        # Only return reasons for features that increase churn risk
        if shap_value <= 0:
            return None
            
        # Map feature names to human-readable reasons
        reason_mapping = {
            "days_last_login": f"Inactive for {feature_value:.0f} days",
            "cart_abandon": f"High cart abandonment rate ({feature_value:.1%})",
            "sess_7d": f"Low engagement - only {feature_value:.0f} sessions in 7 days",
            "csat_score": f"Poor satisfaction score ({feature_value:.1f}/5)",
            "refund_rate": f"High refund rate ({feature_value:.1%})",
            "order_freq": f"Low purchase frequency ({feature_value:.1f} orders/month)",
            "total_spent": f"Low total spending (${feature_value:.0f})",
            "acc_age_days": f"Account age: {feature_value:.0f} days",
            "avg_ord_val": f"Low average order value (${feature_value:.0f})",
            "loyalty_enc": "Loyalty tier indicates risk",
            "geo_loc_enc": "Geographic location factor",
            "device_type_enc": "Device usage pattern",
            "pref_pay_enc": "Payment preference factor",
            "lang_pref_enc": "Language preference factor",
            "sub_pay_enc": "Subscription payment status",
            "retention_enc": "Poor retention campaign response",
            "days_last_purch": f"No purchase for {feature_value:.0f} days",
            "tickets_90d": f"High support tickets ({feature_value:.0f} in 90 days)"
        }
        
        return reason_mapping.get(feature_name, f"High risk factor: {feature_name}")
    
    def _fallback_explanations(self, feature_vector: np.ndarray) -> Dict[str, Any]:
        """Fallback explanations when SHAP is not available"""
        # Convert feature vector back to feature dict for rule-based analysis
        features = {}
        for i, feature_name in enumerate(self.feature_columns):
            features[feature_name] = float(feature_vector[0][i])
        
        reasons = []
        feature_importance = {}
        
        # Rule-based analysis
        # Check for recent cart abandonment count (dynamic signal)
        abandon_count = features.get('abandon_count', 0)
        if abandon_count > 0:
            if abandon_count >= 3:
                reasons.append(f"Abandoned cart {abandon_count} times recently (high risk)")
                feature_importance['abandon_count'] = 0.9
            elif abandon_count == 2:
                reasons.append(f"Abandoned cart {abandon_count} times recently")
                feature_importance['abandon_count'] = 0.8
            else:
                reasons.append(f"Abandoned cart {abandon_count} time recently")
                feature_importance['abandon_count'] = 0.7
        
        if features.get('days_last_login', 0) > 7:
            reasons.append("Inactive for extended period")
            feature_importance['days_last_login'] = 0.8
        
        if features.get('cart_abandon', 0) > 0.5:
            reasons.append("High cart abandonment rate (historical)")
            feature_importance['cart_abandon'] = 0.7
        
        if features.get('sess_7d', 0) < 2:
            reasons.append("Low engagement in recent week")
            feature_importance['sess_7d'] = 0.6
        
        if features.get('csat_score', 5) < 3:
            reasons.append("Poor customer satisfaction")
            feature_importance['csat_score'] = 0.7
        
        if features.get('refund_rate', 0) > 0.3:
            reasons.append("High refund rate indicates dissatisfaction")
            feature_importance['refund_rate'] = 0.6
        
        if features.get('days_last_purch', 0) > 30:
            reasons.append("No recent purchases")
            feature_importance['days_last_purch'] = 0.6
        
        if features.get('tickets_90d', 0) > 3:
            reasons.append("Frequent support issues")
            feature_importance['tickets_90d'] = 0.5
        
        return {
            "reasons": reasons[:5],
            "feature_importance": feature_importance,
            "shap_values": {}
        }

# Global predictor instance
churn_predictor = ChurnPredictor()

def get_model_health() -> Dict[str, Any]:
    """Get model health status"""
    return {
        "model_loaded": churn_predictor.model is not None,
        "feature_count": len(churn_predictor.feature_columns) if churn_predictor.feature_columns else 0,
        "timestamp": datetime.utcnow().isoformat()
    }
