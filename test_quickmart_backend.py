#!/usr/bin/env python3
"""
QuickMart Backend Test Script
Test the QuickMart backend API endpoints
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional
from datetime import datetime

class QuickMartTestSuite:
    def __init__(self, base_url: str = "http://localhost:3010"):
        self.base_url = base_url
        self.access_token = None
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
                self.log(f"Status: {data.get('status')}")
                self.log(f"Database: {data.get('database')}")
                self.log(f"Version: {data.get('version')}")
        except Exception as e:
            self.assert_response(None, 200, f"Health Check - {str(e)}")
    
    def test_root_endpoint(self):
        """Test the root endpoint"""
        self.log("Testing root endpoint...")
        try:
            response = requests.get(f"{self.base_url}/")
            if self.assert_response(response, 200, "Root Endpoint"):
                data = response.json()
                self.log(f"Message: {data.get('message')}")
        except Exception as e:
            self.assert_response(None, 200, f"Root Endpoint - {str(e)}")
    
    def test_user_registration(self):
        """Test user registration"""
        self.log("Testing user registration...")
        
        user_data = {
            "email": "test@quickmart.com",
            "password": "testpassword123",
            "profile": {
                "name": "Test User",
                "age": 25,
                "location": "Test City",
                "loyalty_tier": "bronze"
            },
            "preferences": {
                "categories": ["electronics", "clothing"],
                "brands": ["Apple", "Nike"],
                "price_range": {"min": 0, "max": 500}
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/register",
                json=user_data,
                headers={"Content-Type": "application/json"}
            )
            if self.assert_response(response, 200, "User Registration"):
                data = response.json()
                self.log(f"Registered user: {data.get('email')}")
                return data
        except Exception as e:
            self.assert_response(None, 200, f"User Registration - {str(e)}")
            return None
    
    def test_user_login(self):
        """Test user login"""
        self.log("Testing user login...")
        
        login_data = {
            "email": "demo@quickmart.com",  # Use pre-loaded demo user
            "password": "demo"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            if self.assert_response(response, 200, "User Login"):
                data = response.json()
                self.access_token = data.get("access_token")
                self.log(f"Logged in user: {data.get('user', {}).get('email')}")
                return data
        except Exception as e:
            self.assert_response(None, 200, f"User Login - {str(e)}")
            return None
    
    def test_get_products(self):
        """Test getting products"""
        self.log("Testing get products...")
        try:
            response = requests.get(f"{self.base_url}/api/products/")
            if self.assert_response(response, 200, "Get Products"):
                data = response.json()
                self.log(f"Total products: {data.get('total')}")
                self.log(f"Products on page: {len(data.get('products', []))}")
                return data
        except Exception as e:
            self.assert_response(None, 200, f"Get Products - {str(e)}")
            return None
    
    def test_get_categories(self):
        """Test getting categories"""
        self.log("Testing get categories...")
        try:
            response = requests.get(f"{self.base_url}/api/products/categories/")
            if self.assert_response(response, 200, "Get Categories"):
                data = response.json()
                self.log(f"Categories found: {len(data)}")
                for category in data[:3]:  # Show first 3
                    self.log(f"  - {category.get('name')}")
                return data
        except Exception as e:
            self.assert_response(None, 200, f"Get Categories - {str(e)}")
            return None
    
    def test_get_available_coupons(self):
        """Test getting available coupons"""
        self.log("Testing get available coupons...")
        try:
            response = requests.get(f"{self.base_url}/api/coupons/available")
            if self.assert_response(response, 200, "Get Available Coupons"):
                data = response.json()
                self.log(f"Available coupons: {len(data)}")
                for coupon in data[:3]:  # Show first 3
                    self.log(f"  - {coupon.get('code')}: {coupon.get('description')}")
                return data
        except Exception as e:
            self.assert_response(None, 200, f"Get Available Coupons - {str(e)}")
            return None
    
    def test_authenticated_endpoints(self):
        """Test authenticated endpoints"""
        if not self.access_token:
            self.log("No access token available, skipping authenticated tests")
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Test get profile
        self.log("Testing get user profile...")
        try:
            response = requests.get(f"{self.base_url}/api/auth/profile", headers=headers)
            if self.assert_response(response, 200, "Get User Profile"):
                data = response.json()
                self.log(f"Profile: {data.get('profile', {}).get('name')}")
        except Exception as e:
            self.assert_response(None, 200, f"Get User Profile - {str(e)}")
        
        # Test get user coupons
        self.log("Testing get user coupons...")
        try:
            response = requests.get(f"{self.base_url}/api/coupons/user", headers=headers)
            if self.assert_response(response, 200, "Get User Coupons"):
                data = response.json()
                self.log(f"User coupons: {len(data)}")
        except Exception as e:
            self.assert_response(None, 200, f"Get User Coupons - {str(e)}")
    
    def test_admin_endpoints(self):
        """Test admin endpoints"""
        self.log("Testing admin data status...")
        try:
            response = requests.get(f"{self.base_url}/api/admin/data-status")
            if self.assert_response(response, 200, "Admin Data Status"):
                data = response.json()
                self.log(f"Products: {data.get('products')}")
                self.log(f"Users: {data.get('users')}")
                self.log(f"Coupons: {data.get('coupons')}")
                self.log(f"Categories: {data.get('categories')}")
                self.log(f"Is Initialized: {data.get('is_initialized')}")
        except Exception as e:
            self.assert_response(None, 200, f"Admin Data Status - {str(e)}")
    
    def run_comprehensive_test(self):
        """Run the complete test suite"""
        self.log("🚀 Starting QuickMart Backend Test Suite")
        self.log("=" * 60)
        
        # Test basic connectivity
        self.test_health_check()
        self.test_root_endpoint()
        
        # Test admin endpoints
        self.test_admin_endpoints()
        
        # Test public endpoints
        self.test_get_products()
        self.test_get_categories()
        self.test_get_available_coupons()
        
        # Test authentication
        self.test_user_login()
        
        # Test authenticated endpoints
        self.test_authenticated_endpoints()
        
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
            self.log("\n🎉 ALL TESTS PASSED! QuickMart Backend is working correctly.")
        else:
            self.log(f"\n⚠️  {self.results['failed']} tests failed. Please check the errors above.")

def main():
    """Main function to run the test suite"""
    import argparse
    
    parser = argparse.ArgumentParser(description="QuickMart Backend Test Suite")
    parser.add_argument("--url", default="http://localhost:3010", 
                       help="QuickMart Backend API base URL (default: http://localhost:3010)")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick test (health check only)")
    
    args = parser.parse_args()
    
    # Initialize test suite
    test_suite = QuickMartTestSuite(args.url)
    
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
