#!/usr/bin/env python3
"""
Integration testing for Voice Gateway password generation.
Tests complete flow from use case through endpoints with automatic password generation.
"""
import sys
import asyncio
import requests
import json
import uuid
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.usecases.register_user import RegisterUserUseCase
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository
from app.core.services.password_service import PasswordService
from app.core.models.user import User
from app.infrastructure.config.infrastructure_settings import infra_settings


class IntegrationTester:
    """Integration tester for password generation flow."""
    
    def __init__(self):
        """Initialize integration tester."""
        self.base_url = infra_settings.audio_base_url
        self.user_repository = DynamoDBUserRepository()
        self.password_service = PasswordService()
        self.use_case = RegisterUserUseCase(self.user_repository, self.password_service)
        self.test_users = []  # Track created users for cleanup
    
    async def test_use_case_integration(self) -> bool:
        """Test use case with password generation integration."""
        print("Testing use case integration...")
        
        try:
            # Test user registration with automatic password generation
            unique_id = str(uuid.uuid4())[:8]
            user, voice_password = await self.use_case.execute(
                email=f"usecase{unique_id}@test.com",
                name="Use Case Test User"
            )
            
            # Validate user was created
            if not user:
                print("ERROR: User not created")
                return False
            
            # Validate generated password
            if not voice_password:
                print("ERROR: Voice password not generated")
                return False
            
            # Validate password format
            if not self.password_service.validate_password_format(voice_password):
                print("ERROR: Generated password format is invalid")
                return False
            
            # Validate user doesn't have password in plain text
            if hasattr(user, 'voice_password'):
                print("ERROR: User entity should not contain password in plain text")
                return False
            
            # Track user for cleanup
            self.test_users.append(user)
            
            print(f"   User created: {user.name} ({user.email})")
            print(f"   Generated password: '{voice_password}'")
            print("Use case integration successful")
            return True
            
        except Exception as e:
            print(f"ERROR: Use case integration failed: {e}")
            return False
    
    async def test_http_endpoint_integration(self) -> bool:
        """Test HTTP endpoint with password generation."""
        print("\nTesting HTTP endpoint integration...")
        
        try:
            # Prepare registration request (no password field)
            unique_id = str(uuid.uuid4())[:8]
            test_email = f"http{unique_id}@test.com"
            registration_data = {
                "name": "HTTP Test User",
                "email": test_email
            }
            
            # Make registration request
            response = requests.post(
                f"{self.base_url}/api/auth/register",
                json=registration_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            # Check response status
            if response.status_code != 200:
                print(f"ERROR: HTTP request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
            # Parse response
            try:
                user_data = response.json()
            except json.JSONDecodeError:
                print("ERROR: Invalid JSON response")
                return False
            
            # Validate response structure
            required_fields = ['id', 'name', 'email', 'created_at', 'voice_password']
            for field in required_fields:
                if field not in user_data:
                    print(f"ERROR: Missing field in response: {field}")
                    return False
            
            # Validate generated password
            voice_password = user_data['voice_password']
            
            if not voice_password:
                print("ERROR: Password not generated in HTTP response")
                return False
            
            # Validate password format
            if not self.password_service.validate_password_format(voice_password):
                print("ERROR: Generated password format is invalid")
                return False
            
            # Track user for cleanup (if we can retrieve it)
            try:
                user = await self.user_repository.get_by_email(test_email)
                if user:
                    self.test_users.append(user)
            except Exception:
                pass
            
            print(f"   User registered: {user_data['name']} ({user_data['email']})")
            print(f"   Generated password: '{voice_password}'")
            print("HTTP endpoint integration successful")
            return True
            
        except requests.RequestException as e:
            print(f"ERROR: HTTP request failed: {e}")
            return False
        except Exception as e:
            print(f"ERROR: HTTP endpoint test failed: {e}")
            return False
    
    async def test_duplicate_registration(self) -> bool:
        """Test duplicate email registration handling."""
        print("\nTesting duplicate registration handling...")
        
        try:
            # First, register a user
            unique_id = str(uuid.uuid4())[:8]
            test_email = f"duplicate{unique_id}@test.com"
            
            # Register first user
            registration_data = {
                "name": "First Test User",
                "email": test_email
            }
            
            response = requests.post(
                f"{self.base_url}/api/auth/register",
                json=registration_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"ERROR: First registration failed with status {response.status_code}")
                return False
            
            # Track user for cleanup
            try:
                user = await self.user_repository.get_by_email(test_email)
                if user:
                    self.test_users.append(user)
            except Exception:
                pass
            
            # Now try to register the same email again
            duplicate_data = {
                "name": "Duplicate Test User",
                "email": test_email  # Same email
            }
            
            response = requests.post(
                f"{self.base_url}/api/auth/register",
                json=duplicate_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            # Should get 400 error for duplicate
            if response.status_code != 400:
                print(f"ERROR: Expected 400, got {response.status_code}")
                return False
            
            try:
                error_data = response.json()
                if "already exists" not in error_data.get("detail", "").lower():
                    print("ERROR: Wrong error message for duplicate")
                    return False
            except json.JSONDecodeError:
                print("ERROR: Invalid error response format")
                return False
            
            print("   Duplicate registration properly rejected")
            print("Duplicate registration handling successful")
            return True
            
        except requests.RequestException as e:
            print(f"ERROR: HTTP request failed: {e}")
            return False
        except Exception as e:
            print(f"ERROR: Duplicate registration test failed: {e}")
            return False
    
    async def test_password_service_info(self) -> bool:
        """Test password service information access."""
        print("\nTesting password service information...")
        
        try:
            # Get password service info directly from the service
            info = self.password_service.get_dictionary_info()
            
            if not info:
                print("ERROR: Password service info is empty")
                return False
            
            expected_fields = ['language', 'version', 'total_words', 'total_combinations', 'entropy_bits']
            for field in expected_fields:
                if field not in info:
                    print(f"ERROR: Missing field in password info: {field}")
                    return False
            
            print(f"   Dictionary language: {info['language']}")
            print(f"   Total words: {info['total_words']}")
            print(f"   Total combinations: {info['total_combinations']:,}")
            print(f"   Entropy: {info['entropy_bits']} bits")
            print("Password service information access successful")
            return True
            
        except Exception as e:
            print(f"ERROR: Password service info test failed: {e}")
            return False
    
    async def cleanup_test_users(self):
        """Clean up all test users from database."""
        if not self.test_users:
            return
            
        print(f"\nCleaning up {len(self.test_users)} test users...")
        for user in self.test_users:
            try:
                await self.user_repository.delete(str(user.id))
            except Exception as e:
                print(f"   Warning: Could not cleanup user {user.id}: {e}")


async def main():
    """Run integration tests."""
    print("Voice Gateway - Integration Testing")
    print("=" * 50)
    print(f"Testing against: {infra_settings.audio_base_url}")
    print(f"Environment: {infra_settings.aws_region}")
    print()
    
    # Initialize tester
    tester = IntegrationTester()
    
    # Run test suite
    tests = [
        ("Use Case Integration", tester.test_use_case_integration),
        ("HTTP Endpoint Integration", tester.test_http_endpoint_integration),
        ("Duplicate Registration", tester.test_duplicate_registration),
        ("Password Service Info", tester.test_password_service_info)
    ]
    
    results = {}
    for test_name, test_func in tests:
        results[test_name] = await test_func()
    
    # Cleanup test users
    await tester.cleanup_test_users()
    
    # Summary
    print("\n" + "=" * 50)
    print("Integration Test Results:")
    print("-" * 30)
    
    passed_tests = 0
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {test_name}: {status}")
        if passed:
            passed_tests += 1
    
    print(f"\nTests passed: {passed_tests}/{len(tests)}")
    
    if passed_tests == len(tests):
        print("\nAll integration tests passed!")
        print("Password generation integration is working correctly.")
        return True
    else:
        print(f"\n{len(tests) - passed_tests} test(s) failed.")
        print("Please review implementation before proceeding.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 