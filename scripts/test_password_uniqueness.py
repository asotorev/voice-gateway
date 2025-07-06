#!/usr/bin/env python3
"""
Uniqueness Validation Testing for Voice Gateway.
Tests password uniqueness generation and collision detection.
"""
import sys
import asyncio
import uuid
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.adapters.services.password_service import PasswordService
from app.core.services.unique_password_service import UniquePasswordService
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository
from app.core.models.user import User
from app.config.settings import UNIQUE_PASSWORD_MAX_ATTEMPTS

class UniquenessValidationTester:
    """Tester for password uniqueness validation."""
    
    def __init__(self):
        """Initialize tester with services."""
        try:
            self.user_repository = DynamoDBUserRepository()
            self.password_service = PasswordService()
            self.unique_password_service = UniquePasswordService(self.password_service, self.user_repository)
            self.test_users = []  # Track created users for cleanup
        except Exception as e:
            print(f"ERROR: Failed to initialize services: {e}")
            sys.exit(1)
    
    async def test_unique_password_generation(self) -> bool:
        """Test generation of unique passwords with real database validation."""
        print("Testing unique password generation with database validation...")
        
        generated_passwords = []
        created_users = []
        
        try:
            # Generate and save multiple users with unique passwords
            for i in range(5):  # Reduced to 5 for faster testing
                try:
                    # Generate unique password
                    unique_password = await self.unique_password_service.generate_unique_password(max_attempts=UNIQUE_PASSWORD_MAX_ATTEMPTS)
                    generated_passwords.append(unique_password)
                    
                    # Create and save user with this password
                    password_hash = self.password_service.hash_password(unique_password)
                    test_user = User.create(
                        email=f"uniqueness_test_{uuid.uuid4().hex[:8]}@test.com",
                        name=f"Test User {i+1}",
                        password_hash=password_hash
                    )
                    
                    saved_user = await self.user_repository.save(test_user)
                    created_users.append(saved_user)
                    
                    print(f"   Generated and saved user {i+1}: '{unique_password}'")
                    
                except Exception as e:
                    print(f"ERROR: Failed to generate/save user {i+1}: {e}")
                    return False
            
            # Verify no duplicates in generated passwords (local check)
            if len(set(generated_passwords)) != len(generated_passwords):
                print("ERROR: Duplicate passwords found in local array")
                return False
            
            # Verify passwords are actually unique between each other
            print("\n   Verifying uniqueness between generated passwords...")
            for i, password1 in enumerate(generated_passwords):
                for j, password2 in enumerate(generated_passwords):
                    if i != j and password1 == password2:
                        print(f"   ERROR: Duplicate found: '{password1}' at positions {i} and {j}")
                        return False
            print("   ✓ All generated passwords are unique between each other")
            
            # Verify passwords are actually unique in database
            print("\n   Verifying database uniqueness...")
            for i, password in enumerate(generated_passwords):
                password_hash = self.password_service.hash_password(password)
                exists = await self.user_repository.check_password_hash_exists(password_hash)
                if not exists:
                    print(f"   ERROR: Password {i+1} not found in database after saving")
                    return False
                print(f"   ✓ Password {i+1} confirmed in database")
            
            print(f"\n   Successfully generated and validated {len(generated_passwords)} unique passwords")
            print("   All passwords are unique both locally and in database")
            
            print("Unique password generation with database validation successful")
            return True
            
        except Exception as e:
            print(f"ERROR: Test failed: {e}")
            return False
        finally:
            # Always cleanup test users, regardless of success or failure
            if created_users:
                await self._cleanup_test_users(created_users)
    
    async def test_collision_detection(self) -> bool:
        """Test that the system detects when a password already exists (deterministic)."""
        print("\nTesting collision detection (deterministic)...")
        
        try:
            # Force generate_password to always return the same password
            test_password = "biblioteca tortuga"
            password_hash = self.password_service.hash_password(test_password)
            
            exists = await self.user_repository.check_password_hash_exists(password_hash)
            if not exists:
                print(f"   Password '{test_password}' not found in database, creating it...")
                test_user = User.create(
                    email=f"collision_test_{uuid.uuid4().hex[:8]}@test.com",
                    name="Collision Test User",
                    password_hash=password_hash
                )
                saved_user = await self.user_repository.save(test_user)
                self.test_users.append(saved_user)
                print(f"   Created user with password: '{test_password}'")
            else:
                print(f"   Password '{test_password}' already exists in database")
            
            # Monkeypatch generate_password to always return the collision
            original_generate_password = self.password_service.generate_password
            self.password_service.generate_password = lambda: test_password
            try:
                await self.unique_password_service.generate_unique_password(max_attempts=5)
                print("   ERROR: Should have failed due to existing password")
                # Restore original method
                self.password_service.generate_password = original_generate_password
                return False
            except ValueError as e:
                self.password_service.generate_password = original_generate_password
                if "Unable to generate unique password" in str(e):
                    print("   ✓ Correctly detected existing password and failed deterministically")
                    return True
                else:
                    print(f"   ERROR: Unexpected error message: {e}")
                    return False
        except Exception as e:
            print(f"ERROR: Collision detection test failed: {e}")
            return False
    
    async def _cleanup_test_users(self, users):
        """Clean up test users from database."""
        if not users:
            return
        print(f"   Cleaning up {len(users)} test users...")
        for user in users:
            try:
                await self.user_repository.delete(str(user.id))
            except Exception as e:
                print(f"   Warning: Could not cleanup user {user.id}: {e}")

async def main():
    """Run all uniqueness validation tests."""
    print("Voice Gateway - Uniqueness Validation Testing")
    print("=" * 55)
    tester = UniquenessValidationTester()
    tests = [
        ("Unique Password Generation", tester.test_unique_password_generation),
        ("Collision Detection", tester.test_collision_detection)
    ]
    results = {}
    for test_name, test_func in tests:
        results[test_name] = await test_func()
    print("\n" + "=" * 55)
    print("Uniqueness Validation Test Results:")
    print("-" * 40)
    passed_tests = 0
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {test_name}: {status}")
        if passed:
            passed_tests += 1
    print(f"\nTests passed: {passed_tests}/{len(tests)}")
    if passed_tests == len(tests):
        print("\nUniqueness validation is working correctly!")
        print("Password collision detection and retry logic implemented successfully.")
        return True
    else:
        print(f"\n{len(tests) - passed_tests} test(s) failed.")
        print("Please review implementation before proceeding.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 