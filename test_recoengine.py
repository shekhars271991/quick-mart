#!/usr/bin/env python3
"""
RecoEngine Test Script
Comprehensive testing for the churn prediction and nudge generation system.
"""

import requests
import json
import time
import sys
from typing import Dict, Any, List
from datetime import datetime, timedelta
import random

class RecoEngineTestSuite:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_users = []
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def assert_response(self, response: requests.Response, expected_status: int = 200, test_name: str = ""):
        """Assert response status and log results"""
        try:
            if response.status_code == expected_status:
                self.results["passed"] += 1
                self.log(f"✅ {test_name} - Status: {response.status_code}", "PASS")
                return True
            else:
                self.results["failed"] += 1
                self.results["errors"].append(f"{test_name} - Expected {expected_status}, got {response.status_code}")
                self.log(f"❌ {test_name} - Expected {expected_status}, got {response.status_code}", "FAIL")
                return False
        except Exception as e:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name} - Exception: {str(e)}")
            self.log(f"❌ {test_name} - Exception: {str(e)}", "ERROR")
            return False
    
    def test_health_check(self):
        """Test the health endpoint"""
        self.log("Testing health check endpoint...")
        try:
            response = requests.get(f"{self.base_url}/health")
            if self.assert_response(response, 200, "Health Check"):
                data = response.json()
                self.log(f"Health Status: {data.get('status')}")
                self.log(f"Aerospike: {data.get('aerospike')}")
                self.log(f"Model Loaded: {data.get('model', {}).get('model_loaded')}")
                self.log(f"Nudge Rules: {data.get('nudge_engine', {}).get('rules_loaded')}")
        except Exception as e:
            self.assert_response(None, 200, f"Health Check - {str(e)}")
    
    def test_profile_ingestion(self, user_id: str):
        """Test profile feature ingestion"""
        self.log(f"Testing profile ingestion for user {user_id}...")
        
        profile_data = {
            "user_id": user_id,
            "acc_age_days": random.randint(30, 1000),
            "loyalty_tier": random.choice(["bronze", "silver", "gold", "platinum"]),
            "geo_location": random.choice(["US", "CA", "UK", "DE", "FR"]),
            "device_type": random.choice(["mobile", "desktop", "tablet"])
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/ingest/profile",
                json=profile_data,
                headers={"Content-Type": "application/json"}
            )
            self.assert_response(response, 200, f"Profile Ingestion - {user_id}")
            return profile_data
        except Exception as e:
            self.assert_response(None, 200, f"Profile Ingestion - {user_id} - {str(e)}")
            return None
    
    def test_behavior_ingestion(self, user_id: str):
        """Test behavior feature ingestion"""
        self.log(f"Testing behavior ingestion for user {user_id}...")
        
        behavior_data = {
            "user_id": user_id,
            "login_frequency": random.randint(1, 30),
            "session_duration_avg": random.randint(5, 120),
            "page_views_per_session": random.randint(1, 50),
            "cart_abandonment_rate": round(random.uniform(0.0, 1.0), 2),
            "search_frequency": random.randint(0, 20)
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/ingest/behavior",
                json=behavior_data,
                headers={"Content-Type": "application/json"}
            )
            self.assert_response(response, 200, f"Behavior Ingestion - {user_id}")
            return behavior_data
        except Exception as e:
            self.assert_response(None, 200, f"Behavior Ingestion - {user_id} - {str(e)}")
            return None
    
    def test_transactional_ingestion(self, user_id: str):
        """Test transactional feature ingestion"""
        self.log(f"Testing transactional ingestion for user {user_id}...")
        
        transactional_data = {
            "user_id": user_id,
            "total_orders": random.randint(0, 50),
            "avg_order_value": round(random.uniform(10.0, 500.0), 2),
            "total_spent": round(random.uniform(50.0, 5000.0), 2),
            "refund_rate": round(random.uniform(0.0, 0.3), 2),
            "days_since_last_order": random.randint(0, 365)
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/ingest/transactional",
                json=transactional_data,
                headers={"Content-Type": "application/json"}
            )
            self.assert_response(response, 200, f"Transactional Ingestion - {user_id}")
            return transactional_data
        except Exception as e:
            self.assert_response(None, 200, f"Transactional Ingestion - {user_id} - {str(e)}")
            return None
    
    def test_engagement_ingestion(self, user_id: str):
        """Test engagement feature ingestion"""
        self.log(f"Testing engagement ingestion for user {user_id}...")
        
        engagement_data = {
            "user_id": user_id,
            "email_open_rate": round(random.uniform(0.0, 1.0), 2),
            "push_notification_rate": round(random.uniform(0.0, 1.0), 2),
            "promo_response_rate": round(random.uniform(0.0, 0.5), 2),
            "social_shares": random.randint(0, 20),
            "review_count": random.randint(0, 10)
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/ingest/engagement",
                json=engagement_data,
                headers={"Content-Type": "application/json"}
            )
            self.assert_response(response, 200, f"Engagement Ingestion - {user_id}")
            return engagement_data
        except Exception as e:
            self.assert_response(None, 200, f"Engagement Ingestion - {user_id} - {str(e)}")
            return None
    
    def test_support_ingestion(self, user_id: str):
        """Test support feature ingestion"""
        self.log(f"Testing support ingestion for user {user_id}...")
        
        support_data = {
            "user_id": user_id,
            "support_tickets": random.randint(0, 10),
            "avg_resolution_time": random.randint(1, 72),
            "csat_score": round(random.uniform(1.0, 5.0), 1),
            "escalation_rate": round(random.uniform(0.0, 0.3), 2)
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/ingest/support",
                json=support_data,
                headers={"Content-Type": "application/json"}
            )
            self.assert_response(response, 200, f"Support Ingestion - {user_id}")
            return support_data
        except Exception as e:
            self.assert_response(None, 200, f"Support Ingestion - {user_id} - {str(e)}")
            return None
    
    def test_realtime_ingestion(self, user_id: str):
        """Test realtime feature ingestion"""
        self.log(f"Testing realtime ingestion for user {user_id}...")
        
        realtime_data = {
            "user_id": user_id,
            "session_clicks": random.randint(1, 100),
            "time_on_checkout": random.randint(30, 600),
            "bounce_flag": random.choice([True, False]),
            "current_cart_value": round(random.uniform(0.0, 300.0), 2)
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/ingest/realtime",
                json=realtime_data,
                headers={"Content-Type": "application/json"}
            )
            self.assert_response(response, 200, f"Realtime Ingestion - {user_id}")
            return realtime_data
        except Exception as e:
            self.assert_response(None, 200, f"Realtime Ingestion - {user_id} - {str(e)}")
            return None
    
    def test_churn_prediction(self, user_id: str):
        """Test churn prediction endpoint"""
        self.log(f"Testing churn prediction for user {user_id}...")
        
        try:
            response = requests.post(f"{self.base_url}/predict/{user_id}")
            if self.assert_response(response, 200, f"Churn Prediction - {user_id}"):
                data = response.json()
                self.log(f"Churn Probability: {data.get('churn_probability')}")
                self.log(f"Risk Segment: {data.get('risk_segment')}")
                self.log(f"Confidence Score: {data.get('confidence_score')}")
                self.log(f"Churn Reasons: {data.get('churn_reasons')}")
                
                # Check if nudges were triggered
                nudges = data.get('nudges_triggered', [])
                if nudges:
                    self.log(f"Nudges Triggered: {len(nudges)}")
                    for nudge in nudges:
                        self.log(f"  - {nudge.get('type')}: {nudge.get('channel')}")
                
                return data
        except Exception as e:
            self.assert_response(None, 200, f"Churn Prediction - {user_id} - {str(e)}")
            return None
    
    def test_nudge_rules(self):
        """Test nudge rules endpoint"""
        self.log("Testing nudge rules endpoint...")
        
        try:
            response = requests.get(f"{self.base_url}/nudge/rules")
            if self.assert_response(response, 200, "Nudge Rules"):
                data = response.json()
                self.log(f"Total Nudge Rules: {len(data.get('rules', []))}")
                for rule in data.get('rules', [])[:3]:  # Show first 3 rules
                    self.log(f"  Rule {rule.get('rule_id')}: {rule.get('name')}")
        except Exception as e:
            self.assert_response(None, 200, f"Nudge Rules - {str(e)}")
    
    def test_nudge_rule_detail(self, rule_id: str = "rule_1"):
        """Test specific nudge rule endpoint"""
        self.log(f"Testing nudge rule detail for {rule_id}...")
        
        try:
            response = requests.get(f"{self.base_url}/nudge/rules/{rule_id}")
            if self.assert_response(response, 200, f"Nudge Rule Detail - {rule_id}"):
                data = response.json()
                self.log(f"Rule Name: {data.get('name')}")
                self.log(f"Trigger Condition: {data.get('trigger_condition')}")
                self.log(f"Action: {data.get('action')}")
        except Exception as e:
            self.assert_response(None, 200, f"Nudge Rule Detail - {rule_id} - {str(e)}")
    
    def test_nudge_matching(self, user_id: str):
        """Test nudge rule matching for a user"""
        self.log(f"Testing nudge matching for user {user_id}...")
        
        try:
            response = requests.get(f"{self.base_url}/nudge/test/{user_id}")
            if self.assert_response(response, 200, f"Nudge Matching - {user_id}"):
                data = response.json()
                matched_rules = data.get('matched_rules', [])
                self.log(f"Matched Rules: {len(matched_rules)}")
                for rule in matched_rules:
                    self.log(f"  - Rule {rule.get('rule_id')}: {rule.get('reason')}")
        except Exception as e:
            self.assert_response(None, 200, f"Nudge Matching - {user_id} - {str(e)}")
    
    def create_test_user(self, user_id: str):
        """Create a complete test user with all feature types"""
        self.log(f"Creating test user: {user_id}")
        
        user_data = {
            "user_id": user_id,
            "profile": self.test_profile_ingestion(user_id),
            "behavior": self.test_behavior_ingestion(user_id),
            "transactional": self.test_transactional_ingestion(user_id),
            "engagement": self.test_engagement_ingestion(user_id),
            "support": self.test_support_ingestion(user_id),
            "realtime": self.test_realtime_ingestion(user_id)
        }
        
        # Wait a moment for data to be processed
        time.sleep(1)
        
        # Test prediction for this user
        prediction = self.test_churn_prediction(user_id)
        user_data["prediction"] = prediction
        
        # Test nudge matching
        self.test_nudge_matching(user_id)
        
        self.test_users.append(user_data)
        return user_data
    
    def test_error_scenarios(self):
        """Test error handling scenarios"""
        self.log("Testing error scenarios...")
        
        # Test prediction for non-existent user
        try:
            response = requests.post(f"{self.base_url}/predict/nonexistent_user")
            # This might return 200 with default values or 404, both are acceptable
            if response.status_code in [200, 404]:
                self.results["passed"] += 1
                self.log("✅ Non-existent user prediction handled correctly", "PASS")
            else:
                self.results["failed"] += 1
                self.log(f"❌ Unexpected status for non-existent user: {response.status_code}", "FAIL")
        except Exception as e:
            self.log(f"Error testing non-existent user: {str(e)}", "ERROR")
        
        # Test invalid JSON
        try:
            response = requests.post(
                f"{self.base_url}/ingest/profile",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            )
            if response.status_code in [400, 422]:
                self.results["passed"] += 1
                self.log("✅ Invalid JSON handled correctly", "PASS")
            else:
                self.results["failed"] += 1
                self.log(f"❌ Invalid JSON not handled properly: {response.status_code}", "FAIL")
        except Exception as e:
            self.log(f"Error testing invalid JSON: {str(e)}", "ERROR")
    
    def run_comprehensive_test(self):
        """Run the complete test suite"""
        self.log("🚀 Starting RecoEngine Comprehensive Test Suite")
        self.log("=" * 60)
        
        # Test basic connectivity
        self.test_health_check()
        
        # Test nudge system
        self.test_nudge_rules()
        self.test_nudge_rule_detail()
        
        # Create test users with different profiles
        test_user_scenarios = [
            "high_risk_user",      # User likely to churn
            "loyal_customer",      # Long-term loyal customer
            "new_user",           # Recently joined user
            "inactive_user",      # User with low engagement
            "premium_user"        # High-value customer
        ]
        
        for user_id in test_user_scenarios:
            self.log(f"\n--- Testing Scenario: {user_id} ---")
            self.create_test_user(user_id)
        
        # Test error scenarios
        self.log("\n--- Testing Error Scenarios ---")
        self.test_error_scenarios()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        self.log("\n" + "=" * 60)
        self.log("🏁 TEST SUMMARY")
        self.log("=" * 60)
        
        total_tests = self.results["passed"] + self.results["failed"]
        pass_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        self.log(f"Total Tests: {total_tests}")
        self.log(f"Passed: {self.results['passed']} ✅")
        self.log(f"Failed: {self.results['failed']} ❌")
        self.log(f"Pass Rate: {pass_rate:.1f}%")
        
        if self.results["errors"]:
            self.log("\n❌ ERRORS:")
            for error in self.results["errors"]:
                self.log(f"  - {error}")
        
        if self.results["failed"] == 0:
            self.log("\n🎉 ALL TESTS PASSED! RecoEngine is working correctly.")
        else:
            self.log(f"\n⚠️  {self.results['failed']} tests failed. Please check the errors above.")
        
        # Print user predictions summary
        if self.test_users:
            self.log("\n📊 USER PREDICTIONS SUMMARY:")
            for user in self.test_users:
                if user.get("prediction"):
                    pred = user["prediction"]
                    self.log(f"  {user['user_id']}: {pred.get('churn_probability', 'N/A'):.3f} "
                           f"({pred.get('risk_segment', 'N/A')})")

def main():
    """Main function to run the test suite"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RecoEngine Test Suite")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="RecoEngine API base URL (default: http://localhost:8000)")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick test (health check only)")
    
    args = parser.parse_args()
    
    # Initialize test suite
    test_suite = RecoEngineTestSuite(args.url)
    
    try:
        if args.quick:
            test_suite.log("🏃 Running Quick Test (Health Check Only)")
            test_suite.test_health_check()
            test_suite.print_summary()
        else:
            test_suite.run_comprehensive_test()
        
        # Exit with appropriate code
        sys.exit(0 if test_suite.results["failed"] == 0 else 1)
        
    except KeyboardInterrupt:
        test_suite.log("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        test_suite.log(f"\n💥 Unexpected error: {str(e)}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
