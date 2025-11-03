#!/usr/bin/env python3
"""
Synthetic Training Data Generator for Churn Prediction

This module generates synthetic training data and inserts it into Aerospike
in the 'churnprediction' namespace under the 'training_data' set.
"""

import aerospike
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import uuid
import logging
from feature_config import (
    FEATURE_COLUMNS, CATEGORICAL_MAPPINGS, CATEGORICAL_INDICES, SYNTHETIC_DATA_PARAMS
)
from config import settings

# Configure logging
logger = logging.getLogger(__name__)

class TrainingDataGenerator:
    def __init__(self, aerospike_host="localhost", aerospike_port=3000):
        self.aerospike_host = aerospike_host
        self.aerospike_port = aerospike_port
        self.client = None
        self.namespace = settings.AEROSPIKE_NAMESPACE
        self.set_name = "training_data"
        
    def connect_aerospike(self):
        """Connect to Aerospike"""
        config = {
            'hosts': [(self.aerospike_host, self.aerospike_port)],
            'policies': {
                        'write': {'key': aerospike.POLICY_KEY_SEND}
                    }
         }
        
        # Add TLS configuration if enabled (only CA file required for Aerospike Cloud)
        if settings.AEROSPIKE_USE_TLS:
            tls_config = {}
            if settings.AEROSPIKE_TLS_CAFILE:
                tls_config['cafile'] = settings.AEROSPIKE_TLS_CAFILE
            if settings.AEROSPIKE_TLS_NAME:
                tls_config['name'] = settings.AEROSPIKE_TLS_NAME
            if tls_config:
                config['tls'] = tls_config
            else:
                logger.warning("TLS enabled but AEROSPIKE_TLS_CAFILE not provided")
        
        # Add authentication if credentials provided
        if settings.AEROSPIKE_USERNAME and settings.AEROSPIKE_PASSWORD:
            config['auth'] = {
                'username': settings.AEROSPIKE_USERNAME,
                'password': settings.AEROSPIKE_PASSWORD
            }
        
        try:
            logger.info(f"Connecting to Aerospike at {self.aerospike_host}:{self.aerospike_port}")
            if settings.AEROSPIKE_USE_TLS:
                logger.info("Using TLS connection")
            self.client = aerospike.client(config).connect()
            logger.info("Connected to Aerospike successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Aerospike: {e}")
            return False
    
    def disconnect_aerospike(self):
        """Disconnect from Aerospike"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from Aerospike")
    
    def generate_synthetic_features(self, n_samples=1000, random_seed=42):
        """Generate synthetic training features"""
        logger.info(f"Generating {n_samples} synthetic training samples")
        
        np.random.seed(random_seed)
        
        training_data = []
        
        for i in range(n_samples):
            # Generate base user ID
            user_id = f"synthetic_user_{uuid.uuid4().hex[:8]}"
            
            # Generate realistic feature values
            features = {}
            
            # Account and membership features
            features['acc_age_days'] = np.random.exponential(365) + 30  # 30+ days, exponential distribution
            features['member_dur'] = features['acc_age_days'] * np.random.uniform(0.5, 1.0)  # Member duration <= account age
            
            # Categorical features (encoded)
            features['loyalty_enc'] = np.random.choice([1, 2, 3, 4], p=[0.4, 0.3, 0.2, 0.1])  # Bronze most common
            features['geo_loc_enc'] = np.random.choice([1, 2, 3, 4, 5], p=[0.3, 0.25, 0.2, 0.15, 0.1])
            features['device_type_enc'] = np.random.choice([1, 2, 3], p=[0.6, 0.3, 0.1])  # Mobile most common
            features['pref_pay_enc'] = np.random.choice([1, 2, 3, 4], p=[0.5, 0.3, 0.15, 0.05])
            features['lang_pref_enc'] = np.random.choice([1, 2, 3, 4], p=[0.7, 0.15, 0.1, 0.05])
            features['sub_pay_enc'] = np.random.choice([1, 2, 3], p=[0.7, 0.2, 0.1])
            features['retention_enc'] = np.random.choice([1, 2, 3], p=[0.4, 0.3, 0.3])
            
            # Activity features
            features['days_last_login'] = np.random.exponential(5)  # Most users login frequently
            features['days_last_purch'] = np.random.exponential(15) + features['days_last_login']  # Purchase after login
            features['sess_7d'] = max(0, np.random.poisson(5))  # Sessions in last 7 days
            features['sess_30d'] = features['sess_7d'] + max(0, np.random.poisson(15))  # Sessions in last 30 days
            features['avg_sess_dur'] = np.random.lognormal(3, 0.5)  # Average session duration in minutes
            
            # Engagement features
            features['ctr_10_sess'] = np.random.beta(2, 8)  # Click-through rate (0-1)
            features['cart_abandon'] = np.random.beta(3, 7)  # Cart abandonment rate (0-1)
            features['wishlist_ratio'] = np.random.beta(2, 8)  # Wishlist to purchase ratio
            features['content_engage'] = np.random.beta(3, 7)  # Content engagement score
            
            # Purchase behavior features
            features['avg_order_val'] = np.random.lognormal(4, 0.8) + 10  # Average order value
            features['orders_6m'] = max(0, np.random.poisson(3))  # Orders in last 6 months
            features['purch_freq_90d'] = max(0, np.random.poisson(2))  # Purchase frequency in 90 days
            features['last_hv_purch'] = features['days_last_purch'] + np.random.exponential(30)  # Days since last high-value purchase
            features['refund_rate'] = np.random.beta(1, 9)  # Refund rate (0-1)
            
            # Marketing features
            features['discount_dep'] = np.random.beta(2, 5)  # Discount dependency
            features['push_open_rate'] = np.random.beta(3, 7)  # Push notification open rate
            features['email_ctr'] = np.random.beta(2, 8)  # Email click-through rate
            features['inapp_ctr'] = np.random.beta(3, 7)  # In-app click-through rate
            features['promo_resp_time'] = np.random.exponential(24)  # Promo response time in hours
            
            # Support features
            features['tickets_90d'] = max(0, np.random.poisson(1))  # Support tickets in 90 days
            features['avg_ticket_res'] = np.random.exponential(48) + 2  # Average ticket resolution time in hours
            features['csat_score'] = np.random.choice([1, 2, 3, 4, 5], p=[0.05, 0.1, 0.2, 0.4, 0.25])  # Customer satisfaction
            features['refund_req'] = max(0, np.random.poisson(0.5))  # Number of refund requests
            
            # Session behavior features
            features['curr_sess_clk'] = max(0, np.random.poisson(10))  # Clicks in current session
            features['checkout_time'] = np.random.exponential(300) + 60  # Checkout time in seconds
            features['cart_no_buy'] = max(0, np.random.poisson(2))  # Cart additions without purchase
            features['bounce_flag'] = np.random.choice([0, 1], p=[0.7, 0.3])  # Bounce flag
            
            # Generate churn label based on realistic patterns
            churn_probability = self._calculate_churn_probability(features)
            churn_label = 1 if np.random.random() < churn_probability else 0
            
            # Add metadata
            sample = {
                'user_id': user_id,
                'churn_label': churn_label,  # Changed from 'churn' to 'churn_label' to match training service
                'generated_at': datetime.utcnow().isoformat(),
                'data_source': 'synthetic',
                **features
            }
            
            training_data.append(sample)
            
            # Log progress
            if (i + 1) % 1000 == 0:
                logger.info(f"Generated {i + 1}/{n_samples} samples")
        
        logger.info(f"Generated {len(training_data)} training samples")
        return training_data
    
    def _calculate_churn_probability(self, features):
        """Calculate churn probability based on feature values using realistic correlations"""
        churn_score = 0.0
        
        # High-risk factors (increase churn probability)
        if features.get('days_last_login', 0) > 14:
            churn_score += 0.3
        elif features.get('days_last_login', 0) > 7:
            churn_score += 0.15
            
        if features.get('days_last_purch', 0) > 60:
            churn_score += 0.25
        elif features.get('days_last_purch', 0) > 30:
            churn_score += 0.1
            
        if features.get('cart_abandon', 0) > 0.7:
            churn_score += 0.2
        elif features.get('cart_abandon', 0) > 0.5:
            churn_score += 0.1
            
        if features.get('sess_7d', 0) < 2:
            churn_score += 0.2
        elif features.get('sess_7d', 0) < 5:
            churn_score += 0.1
            
        if features.get('csat_score', 5) < 3:
            churn_score += 0.15
        elif features.get('csat_score', 5) < 4:
            churn_score += 0.05
            
        if features.get('refund_rate', 0) > 0.3:
            churn_score += 0.15
        elif features.get('refund_rate', 0) > 0.1:
            churn_score += 0.05
            
        if features.get('tickets_90d', 0) > 3:
            churn_score += 0.1
        elif features.get('tickets_90d', 0) > 1:
            churn_score += 0.05
            
        if features.get('orders_6m', 0) == 0:
            churn_score += 0.3
        elif features.get('orders_6m', 0) < 2:
            churn_score += 0.15
            
        # Protective factors (decrease churn probability)
        if features.get('loyalty_enc', 1) >= 3:  # Gold/Platinum
            churn_score -= 0.2
        elif features.get('loyalty_enc', 1) >= 2:  # Silver
            churn_score -= 0.1
            
        if features.get('orders_6m', 0) > 10:
            churn_score -= 0.15
        elif features.get('orders_6m', 0) > 5:
            churn_score -= 0.1
            
        if features.get('avg_order_val', 0) > 100:
            churn_score -= 0.1
        elif features.get('avg_order_val', 0) > 50:
            churn_score -= 0.05
            
        if features.get('push_open_rate', 0) > 0.5:
            churn_score -= 0.1
        elif features.get('push_open_rate', 0) > 0.3:
            churn_score -= 0.05
            
        if features.get('email_ctr', 0) > 0.3:
            churn_score -= 0.05
            
        if features.get('avg_sess_dur', 0) > 20:
            churn_score -= 0.05
        
        # Convert to probability and ensure realistic range
        churn_probability = max(0.05, min(0.95, 0.25 + churn_score))  # Base rate of 25% ± adjustments
        return churn_probability
    
    def store_training_data(self, training_data, clear_existing=False):
        """Store training data in Aerospike"""
        if not self.client:
            if not self.connect_aerospike():
                raise Exception("Failed to connect to Aerospike")
        
        try:
            if clear_existing:
                logger.info("Clearing existing training data...")
                self._clear_training_data()
            
            logger.info(f"Storing {len(training_data)} training samples in Aerospike")
            
            stored_count = 0
            for sample in training_data:
                try:
                    key = (self.namespace, self.set_name, sample['user_id'])
                    
                    # Convert numpy types to native Python types for Aerospike serialization
                    bins = {}
                    for field_name, field_value in sample.items():
                        if isinstance(field_value, (np.integer, np.floating)):
                            bins[field_name] = float(field_value)
                        elif isinstance(field_value, np.ndarray):
                            bins[field_name] = field_value.tolist()
                        elif isinstance(field_value, (int, float, str, bool)):
                            bins[field_name] = field_value
                        else:
                            # Convert other types to string as fallback
                            bins[field_name] = str(field_value)
                    
                    self.client.put(key, bins)
                    stored_count += 1
                    
                    if stored_count % 1000 == 0:
                        logger.info(f"Stored {stored_count}/{len(training_data)} samples")
                        
                except Exception as e:
                    logger.error(f"Failed to store sample {sample['user_id']}: {e}")
            
            logger.info(f"Successfully stored {stored_count} training samples")
            return stored_count
            
        except Exception as e:
            logger.error(f"Error storing training data: {e}")
            raise
    
    def _clear_training_data(self):
        """Clear existing training data from Aerospike"""
        try:
            # Scan and delete all records in the training_data set
            scan = self.client.scan(self.namespace, self.set_name)
            deleted_count = 0
            
            def delete_record(input_tuple):
                nonlocal deleted_count
                key, metadata, record = input_tuple
                try:
                    self.client.remove(key)
                    deleted_count += 1
                    if deleted_count % 1000 == 0:
                        logger.info(f"Deleted {deleted_count} existing records")
                except Exception as e:
                    logger.error(f"Failed to delete record: {e}")
            
            scan.foreach(delete_record)
            logger.info(f"Cleared {deleted_count} existing training records")
            
        except Exception as e:
            logger.error(f"Error clearing training data: {e}")
            # Don't raise exception here, as this is optional cleanup
    
    def get_training_data_count(self):
        """Get count of training data records"""
        if not self.client:
            if not self.connect_aerospike():
                return 0
        
        try:
            scan = self.client.scan(self.namespace, self.set_name)
            count = 0
            
            def count_record(input_tuple):
                nonlocal count
                count += 1
            
            scan.foreach(count_record)
            return count
            
        except Exception as e:
            logger.error(f"Error counting training data: {e}")
            return 0
    
    def generate_and_store(self, n_samples=1000, clear_existing=False, random_seed=42):
        """Generate and store training data in one operation"""
        logger.info(f"Starting training data generation and storage process")
        
        # Generate synthetic data
        training_data = self.generate_synthetic_features(n_samples, random_seed)
        
        # Store in Aerospike
        stored_count = self.store_training_data(training_data, clear_existing)
        
        # Get final count
        total_count = self.get_training_data_count()
        
        result = {
            'generated_samples': len(training_data),
            'stored_samples': stored_count,
            'total_training_samples': total_count,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Training data generation complete: {result}")
        return result


if __name__ == "__main__":
    # Command line interface for standalone usage
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate synthetic training data for churn prediction')
    parser.add_argument('--samples', type=int, default=1000, help='Number of samples to generate')
    parser.add_argument('--host', type=str, default='localhost', help='Aerospike host')
    parser.add_argument('--port', type=int, default=3000, help='Aerospike port')
    parser.add_argument('--clear', action='store_true', help='Clear existing training data')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
    
    args = parser.parse_args()
    
    # Create generator and run
    generator = TrainingDataGenerator(args.host, args.port)
    try:
        result = generator.generate_and_store(
            n_samples=args.samples,
            clear_existing=args.clear,
            random_seed=args.seed
        )
        print(f"Success: {result}")
    finally:
        generator.disconnect_aerospike()
