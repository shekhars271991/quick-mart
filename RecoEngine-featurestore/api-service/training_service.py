"""
Training Service for Churn Prediction Model
Handles model training using data from Aerospike
"""

import xgboost as xgb
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import logging
from datetime import datetime
import joblib
import os
import uuid
import aerospike
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, classification_report, confusion_matrix
import json
from feature_config import FEATURE_COLUMNS, MODEL_PARAMS
from config import settings

# Configure logging
logger = logging.getLogger(__name__)

class ModelTrainer:
    def __init__(self, aerospike_client):
        self.client = aerospike_client
        self.namespace = settings.AEROSPIKE_NAMESPACE
        self.set_name = "training_data"
        self.feature_columns = FEATURE_COLUMNS
        self.model = None
        self.training_metrics = {}
        
    def load_training_data(self) -> Tuple[pd.DataFrame, np.ndarray]:
        """Load training data from Aerospike"""
        logger.info("Loading training data from Aerospike...")
        
        try:
            # Scan the training data set
            scan = self.client.scan(self.namespace, self.set_name)
            
            training_records = []
            total_records = 0
            
            for record in scan.results():
                total_records += 1
                record_data = record[2]  # The actual data is in index 2
                
                # Extract features and label
                features = {}
                for feature_name in self.feature_columns:
                    features[feature_name] = record_data.get(feature_name, 0.0)
                
                churn_label = record_data.get('churn_label', 0)
                user_id = record_data.get('user_id', f'unknown_{total_records}')
                
                training_record = {
                    'user_id': user_id,
                    'churn_label': churn_label,
                    **features
                }
                training_records.append(training_record)
            
            logger.info(f"Loaded {len(training_records)} training records from Aerospike")
            
            if len(training_records) == 0:
                raise ValueError("No training data found in Aerospike")
            
            # Convert to DataFrame
            df = pd.DataFrame(training_records)
            
            # Separate features and labels
            X = df[self.feature_columns].values
            y = df['churn_label'].values
            
            logger.info(f"Training data shape: X={X.shape}, y={y.shape}")
            logger.info(f"Churn distribution: {np.bincount(y)} (0=no churn, 1=churn)")
            
            return df, X, y
            
        except Exception as e:
            logger.error(f"Failed to load training data: {e}")
            raise
    
    def train_model(self, X: np.ndarray, y: np.ndarray, test_size: float = 0.2, random_state: int = 42) -> Dict[str, Any]:
        """Train the XGBoost model"""
        logger.info("Starting model training...")
        
        try:
            # Split the data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state, stratify=y
            )
            
            logger.info(f"Training set: {X_train.shape}, Test set: {X_test.shape}")
            
            # Initialize and train the model
            self.model = xgb.XGBClassifier(**MODEL_PARAMS)
            
            # Train the model
            training_start = datetime.utcnow()
            self.model.fit(X_train, y_train)
            training_end = datetime.utcnow()
            training_duration = (training_end - training_start).total_seconds()
            
            logger.info(f"Model training completed in {training_duration:.2f} seconds")
            
            # Make predictions
            y_train_pred = self.model.predict(X_train)
            y_test_pred = self.model.predict(X_test)
            y_test_proba = self.model.predict_proba(X_test)[:, 1]
            
            # Calculate metrics
            metrics = {
                'training_duration_seconds': training_duration,
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'feature_count': len(self.feature_columns),
                'train_accuracy': float(accuracy_score(y_train, y_train_pred)),
                'test_accuracy': float(accuracy_score(y_test, y_test_pred)),
                'test_precision': float(precision_score(y_test, y_test_pred, zero_division=0)),
                'test_recall': float(recall_score(y_test, y_test_pred, zero_division=0)),
                'test_f1': float(f1_score(y_test, y_test_pred, zero_division=0)),
                'test_roc_auc': float(roc_auc_score(y_test, y_test_proba)),
                'confusion_matrix': confusion_matrix(y_test, y_test_pred).tolist(),
                'classification_report': classification_report(y_test, y_test_pred, output_dict=True),
                'trained_at': training_end.isoformat(),
                'model_params': MODEL_PARAMS,
                'feature_columns': self.feature_columns
            }
            
            # Feature importance
            if hasattr(self.model, 'feature_importances_'):
                feature_importance = {}
                for i, importance in enumerate(self.model.feature_importances_):
                    feature_importance[self.feature_columns[i]] = float(importance)
                metrics['feature_importance'] = feature_importance
            
            self.training_metrics = metrics
            
            logger.info(f"Model training metrics:")
            logger.info(f"  Test Accuracy: {metrics['test_accuracy']:.4f}")
            logger.info(f"  Test F1 Score: {metrics['test_f1']:.4f}")
            logger.info(f"  Test ROC AUC: {metrics['test_roc_auc']:.4f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            raise
    
    def save_model(self, model_path: str = "churn_model.joblib", metrics_path: str = "churn_model_metrics.json") -> bool:
        """Save the trained model and metrics"""
        try:
            if self.model is None:
                raise ValueError("No trained model to save")
            
            # Save the model
            joblib.dump(self.model, model_path)
            logger.info(f"Model saved to: {model_path}")
            
            # Save the metrics
            with open(metrics_path, 'w') as f:
                json.dump(self.training_metrics, f, indent=2)
            logger.info(f"Metrics saved to: {metrics_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    def validate_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate the quality of training data"""
        logger.info("Validating data quality...")
        
        quality_report = {
            'total_records': len(df),
            'feature_count': len(self.feature_columns),
            'missing_values': {},
            'data_types': {},
            'value_ranges': {},
            'class_distribution': {},
            'quality_score': 0.0,
            'issues': []
        }
        
        # Check missing values
        for column in self.feature_columns:
            if column in df.columns:
                missing_count = df[column].isnull().sum()
                quality_report['missing_values'][column] = int(missing_count)
                quality_report['data_types'][column] = str(df[column].dtype)
                
                if df[column].dtype in ['int64', 'float64']:
                    quality_report['value_ranges'][column] = {
                        'min': float(df[column].min()),
                        'max': float(df[column].max()),
                        'mean': float(df[column].mean()),
                        'std': float(df[column].std())
                    }
            else:
                quality_report['issues'].append(f"Missing feature column: {column}")
        
        # Check class distribution
        if 'churn_label' in df.columns:
            class_counts = df['churn_label'].value_counts().to_dict()
            quality_report['class_distribution'] = {int(k): int(v) for k, v in class_counts.items()}
            
            # Check for class imbalance
            total = sum(class_counts.values())
            minority_class_ratio = min(class_counts.values()) / total
            if minority_class_ratio < 0.1:
                quality_report['issues'].append(f"Severe class imbalance detected: {minority_class_ratio:.2%}")
            elif minority_class_ratio < 0.2:
                quality_report['issues'].append(f"Class imbalance detected: {minority_class_ratio:.2%}")
        else:
            quality_report['issues'].append("Missing target column: churn_label")
        
        # Calculate quality score
        base_score = 100.0
        
        # Deduct for missing values
        total_missing = sum(quality_report['missing_values'].values())
        missing_penalty = (total_missing / (len(df) * len(self.feature_columns))) * 30
        
        # Deduct for issues
        issue_penalty = len(quality_report['issues']) * 10
        
        # Deduct for insufficient data
        if len(df) < 100:
            size_penalty = 20
        elif len(df) < 500:
            size_penalty = 10
        else:
            size_penalty = 0
        
        quality_report['quality_score'] = max(0.0, base_score - missing_penalty - issue_penalty - size_penalty)
        
        logger.info(f"Data quality score: {quality_report['quality_score']:.1f}/100")
        if quality_report['issues']:
            logger.warning(f"Data quality issues: {quality_report['issues']}")
        
        return quality_report

def get_training_status() -> Dict[str, Any]:
    """Get current training status"""
    return {
        "training_active": False,  # This would be managed by a job queue in production
        "last_training": None,
        "model_available": os.path.exists("churn_model.joblib"),
        "metrics_available": os.path.exists("churn_model_metrics.json")
    }
