#!/usr/bin/env python3
"""
Synthetic Training Data Generator for Churn Prediction

This script generates synthetic training data and inserts it into Aerospike
in the 'churn_features' namespace under the 'training_data' set.
"""

import aerospike
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import uuid
import logging
import argparse
import sys
import os

# Add the api-service directory to path to import feature_config
sys.path.append(os.path.join(os.path.dirname(__file__), 'api-service'))

from feature_config import (
    FEATURE_COLUMNS, CATEGORICAL_MAPPINGS, CATEGORICAL_INDICES, SYNTHETIC_DATA_PARAMS
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TrainingDataGenerator:
    def __init__(self, aerospike_host="localhost", aerospike_port=3000):
        self.aerospike_host = aerospike_host
        self.aerospike_port = aerospike_port
        self.client = None
        self.namespace = "churn_features"
        self.set_name = "training_data"
        
    def connect_aerospike(self):
        """Connect to Aerospike"""
        config = {
            'hosts': [(self.aerospike_host, self.aerospike_port)]
        }
        try:
            logger.info(f"Connecting to Aerospike at {self.aerospike_host}:{self.aerospike_port}")
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
            churn_label = np.random.binomial(1, churn_probability)
            
            # Create training record
            training_record = {
                'user_id': user_id,
                'features': features,
                'churn_label': int(churn_label),
                'churn_probability': float(churn_probability),
                'generated_at': datetime.utcnow().isoformat(),
                'data_type': 'synthetic_training'
            }
            
            training_data.append(training_record)
            
            if (i + 1) % 100 == 0:
                logger.info(f"Generated {i + 1}/{n_samples} samples")
        
        logger.info(f"Generated {len(training_data)} synthetic training samples")
        return training_data
    
    def _calculate_churn_probability(self, features):
        """Calculate realistic churn probability based on feature values"""
        # Start with base probability
        churn_prob = 0.2
        
        # High-risk factors (increase churn probability)
        if features['days_last_login'] > 14:
            churn_prob += 0.3
        elif features['days_last_login'] > 7:
            churn_prob += 0.15
            
        if features['days_last_purch'] > 60:
            churn_prob += 0.25
        elif features['days_last_purch'] > 30:
            churn_prob += 0.1
            
        if features['cart_abandon'] > 0.7:
            churn_prob += 0.2
            
        if features['sess_7d'] < 1:
            churn_prob += 0.2
            
        if features['csat_score'] < 3:
            churn_prob += 0.3
            
        if features['refund_rate'] > 0.3:
            churn_prob += 0.15
            
        if features['tickets_90d'] > 3:
            churn_prob += 0.1
        
        # Protective factors (decrease churn probability)
        if features['loyalty_enc'] >= 3:  # Gold/Platinum
            churn_prob -= 0.1
            
        if features['orders_6m'] > 5:
            churn_prob -= 0.15
            
        if features['avg_order_val'] > 100:
            churn_prob -= 0.1
            
        if features['push_open_rate'] > 0.5:
            churn_prob -= 0.05
        
        # Ensure probability is between 0 and 1
        return max(0.01, min(0.99, churn_prob))
    
    def insert_training_data(self, training_data):
        """Insert training data into Aerospike"""
        if not self.client:
            logger.error("Not connected to Aerospike")
            return False
        
        logger.info(f"Inserting {len(training_data)} training records into Aerospike")
        
        success_count = 0
        error_count = 0
        
        for i, record in enumerate(training_data):
            try:
                # Create Aerospike key
                key = (self.namespace, self.set_name, record['user_id'])
                
                # Prepare bins (Aerospike record fields)
                bins = {
                    'user_id': record['user_id'],
                    'churn_label': record['churn_label'],
                    'churn_prob': record['churn_probability'],  # Shortened to fit 15 char limit
                    'generated_at': record['generated_at'],
                    'data_type': record['data_type']
                }
                
                # Add all features as separate bins
                for feature_name, feature_value in record['features'].items():
                    bins[feature_name] = float(feature_value)
                
                # Insert record
                self.client.put(key, bins)
                success_count += 1
                
                if (i + 1) % 100 == 0:
                    logger.info(f"Inserted {i + 1}/{len(training_data)} records")
                    
            except Exception as e:
                logger.error(f"Failed to insert record {record['user_id']}: {e}")
                error_count += 1
                continue
        
        logger.info(f"Training data insertion completed. Success: {success_count}, Errors: {error_count}")
        return success_count > 0
    
    def get_data_stats(self):
        """Get statistics about the training data in Aerospike"""
        if not self.client:
            logger.error("Not connected to Aerospike")
            return None
        
        try:
            # Scan the training data set
            scan = self.client.scan(self.namespace, self.set_name)
            
            total_records = 0
            churn_count = 0
            non_churn_count = 0
            
            for record in scan.results():
                total_records += 1
                if record[2].get('churn_label', 0) == 1:
                    churn_count += 1
                else:
                    non_churn_count += 1
            
            stats = {
                'total_records': total_records,
                'churn_records': churn_count,
                'non_churn_records': non_churn_count,
                'churn_rate': churn_count / total_records if total_records > 0 else 0
            }
            
            logger.info(f"Training data stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get data stats: {e}")
            return None
    
    def clear_training_data(self):
        """Clear all training data from Aerospike"""
        if not self.client:
            logger.error("Not connected to Aerospike")
            return False
        
        try:
            logger.info("Clearing existing training data...")
            scan = self.client.scan(self.namespace, self.set_name)
            
            deleted_count = 0
            for record in scan.results():
                key = record[0]
                self.client.remove(key)
                deleted_count += 1
            
            logger.info(f"Cleared {deleted_count} training records")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear training data: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Generate synthetic training data for churn prediction')
    parser.add_argument('--host', default='localhost', help='Aerospike host (default: localhost)')
    parser.add_argument('--port', type=int, default=3000, help='Aerospike port (default: 3000)')
    parser.add_argument('--samples', type=int, default=1000, help='Number of samples to generate (default: 1000)')
    parser.add_argument('--clear', action='store_true', help='Clear existing training data before generating new')
    parser.add_argument('--stats-only', action='store_true', help='Only show statistics, don\'t generate data')
    parser.add_argument('--seed', type=int, default=42, help='Random seed (default: 42)')
    
    args = parser.parse_args()
    
    # Create data generator
    generator = TrainingDataGenerator(args.host, args.port)
    
    # Connect to Aerospike
    if not generator.connect_aerospike():
        sys.exit(1)
    
    try:
        if args.stats_only:
            # Just show stats
            generator.get_data_stats()
        else:
            # Clear existing data if requested
            if args.clear:
                generator.clear_training_data()
            
            # Generate synthetic data
            training_data = generator.generate_synthetic_features(
                n_samples=args.samples,
                random_seed=args.seed
            )
            
            # Insert into Aerospike
            if generator.insert_training_data(training_data):
                logger.info("Training data generation completed successfully")
                
                # Show final stats
                generator.get_data_stats()
            else:
                logger.error("Failed to insert training data")
                sys.exit(1)
                
    finally:
        generator.disconnect_aerospike()

if __name__ == "__main__":
    main()
