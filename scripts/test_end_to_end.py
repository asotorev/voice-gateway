#!/usr/bin/env python3
"""
End-to-end integration tests for Voice Gateway.
Tests complete flow from HTTP requests to DynamoDB persistence.
"""
import sys
import asyncio
import requests
import json
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app.config.settings import settings


class EndToEndTester:
    """Complete end-to-end testing suite."""
    
    def __init__(self):
        self.base_url = settings.app_url
        self.test_results = []
    
    def test_health_endpoints(self):
        """Test health check endpoints."""
        print("Testing health endpoints...")
        
        try:
            # Test basic ping
            response = requests.get(f"{self.base_url}/api/ping")
            if response.status_code == 200 and response.json().get("message") == "pong":
                print("✓ Basic ping endpoint working")
                self.test_results.append("PING: SUCCESS")
            else:
                print("✗ Basic ping endpoint failed")
                self.test_results.append("PING: FAILED")
            
            # Test comprehensive health check
            response = requests.get(f"{self.base_url}/api/health")
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("status") == "healthy":
                    print("✓ Health check endpoint working")
                    print(f"  Environment: {health_data.get('environment')}")
                    print(f"  DynamoDB status: {health_data['services']['dynamodb']['status']}")
                    self.test_results.append("HEALTH: SUCCESS")
                else:
                    print("✗ Health check shows unhealthy status")
                    self.test_results.append("HEALTH: UNHEALTHY")
            else:
                print("✗ Health check endpoint failed")
                self.test_results.append("HEALTH: FAILED")
                
        except requests.exceptions.ConnectionError:
            print("✗ Cannot connect to application - ensure uvicorn is running")
            self.test_results.append("CONNECTION: FAILED")
            return False
        except Exception as e:
            print(f"✗ Health check failed: {e}")
            self.test_results.append("HEALTH: ERROR")
            return False
            
        return True
    
    def test_user_registration_flow(self):
        """Test complete user registration flow."""
        print("\nTesting user registration flow...")
        
        test_users = [
            {
                "name": "End-to-End Test User",
                "email": "e2e@test.com",
                "password": "testpassword123"
            },
            {
                "name": "Second Test User", 
                "email": "e2e2@test.com",
                "password": "anotherpassword456"
            }
        ]
        
        for i, user_data in enumerate(test_users, 1):
            try:
                print(f"\n  Testing user {i}: {user_data['email']}")
                
                # Register user
                response = requests.post(
                    f"{self.base_url}/api/auth/register",
                    json=user_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    user_response = response.json()
                    print(f"  ✓ User registered successfully")
                    print(f"    User ID: {user_response.get('id')}")
                    print(f"    Name: {user_response.get('name')}")
                    print(f"    Email: {user_response.get('email')}")
                    
                    # Verify response structure
                    required_fields = ['id', 'name', 'email', 'created_at']
                    if all(field in user_response for field in required_fields):
                        print(f"  ✓ Response structure is correct")
                        self.test_results.append(f"REGISTER_USER_{i}: SUCCESS")
                    else:
                        print(f"  ✗ Response missing required fields")
                        self.test_results.append(f"REGISTER_USER_{i}: INCOMPLETE")
                
                else:
                    print(f"  ✗ Registration failed with status {response.status_code}")
                    print(f"    Error: {response.text}")
                    self.test_results.append(f"REGISTER_USER_{i}: FAILED")
                    
            except Exception as e:
                print(f"  ✗ Registration test failed: {e}")
                self.test_results.append(f"REGISTER_USER_{i}: ERROR")
    
    def test_duplicate_email_validation(self):
        """Test duplicate email validation."""
        print("\nTesting duplicate email validation...")
        
        duplicate_user = {
            "name": "Duplicate User",
            "email": "e2e@test.com",  # Same as first test user
            "password": "differentpassword"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/register",
                json=duplicate_user,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 400:
                error_detail = response.json().get("detail", "")
                if "already exists" in error_detail.lower():
                    print("✓ Duplicate email properly rejected")
                    print(f"  Error message: {error_detail}")
                    self.test_results.append("DUPLICATE_VALIDATION: SUCCESS")
                else:
                    print("✗ Wrong error message for duplicate email")
                    self.test_results.append("DUPLICATE_VALIDATION: WRONG_MESSAGE")
            else:
                print("✗ Duplicate email was allowed (should have been rejected)")
                self.test_results.append("DUPLICATE_VALIDATION: FAILED")
                
        except Exception as e:
            print(f"✗ Duplicate validation test failed: {e}")
            self.test_results.append("DUPLICATE_VALIDATION: ERROR")
    
    def test_swagger_documentation(self):
        """Test that API documentation is accessible."""
        print("\nTesting API documentation...")
        
        try:
            # Test OpenAPI spec
            response = requests.get(f"{self.base_url}/openapi.json")
            if response.status_code == 200:
                openapi_spec = response.json()
                if "paths" in openapi_spec and "/api/auth/register" in openapi_spec["paths"]:
                    print("✓ OpenAPI specification is accessible")
                    self.test_results.append("OPENAPI: SUCCESS")
                else:
                    print("✗ OpenAPI spec missing expected endpoints")
                    self.test_results.append("OPENAPI: INCOMPLETE")
            else:
                print("✗ OpenAPI specification not accessible")
                self.test_results.append("OPENAPI: FAILED")
            
            # Test Swagger UI
            response = requests.get(f"{self.base_url}/docs")
            if response.status_code == 200:
                print("✓ Swagger UI is accessible")
                self.test_results.append("SWAGGER_UI: SUCCESS")
            else:
                print("✗ Swagger UI not accessible")
                self.test_results.append("SWAGGER_UI: FAILED")
                
        except Exception as e:
            print(f"✗ Documentation test failed: {e}")
            self.test_results.append("DOCUMENTATION: ERROR")
    
    def run_all_tests(self):
        """Run complete end-to-end test suite."""
        print("Voice Gateway - End-to-End Integration Test")
        print("=" * 55)
        print(f"Environment: {settings.environment}")
        print(f"Application URL: {self.base_url}")
        print(f"DynamoDB Endpoint: {settings.dynamodb_endpoint_url}")
        print()
        
        # Run test suites
        connection_ok = self.test_health_endpoints()
        if connection_ok:
            self.test_user_registration_flow()
            self.test_duplicate_email_validation()
            self.test_swagger_documentation()
        
        # Summary
        print("\n" + "=" * 55)
        print("End-to-End Test Results Summary:")
        print("-" * 35)
        for result in self.test_results:
            print(f"  {result}")
        
        success_count = len([r for r in self.test_results if "SUCCESS" in r])
        total_count = len([r for r in self.test_results if r != "CONNECTION: FAILED"])
        
        print(f"\nTests passed: {success_count}/{total_count}")
        
        if success_count == total_count and connection_ok:
            print("\nAll end-to-end tests passed!")
            print("Complete integration is working correctly.")
            print("\n(DynamoDB Persistence) completed successfully!")
        else:
            print(f"\n{total_count - success_count} tests failed.")
            print("Check application logs and DynamoDB setup.")
        
        return success_count == total_count and connection_ok


def main():
    """Main test runner."""
    print("Starting end-to-end integration tests...")
    print("Make sure the following are running:")
    print("1. docker-compose up -d (DynamoDB Local)")
    print("2. python scripts/setup_database.py (Tables created)")  
    print("3. uvicorn app.main:app --reload (Application running)")
    print()
    
    tester = EndToEndTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 