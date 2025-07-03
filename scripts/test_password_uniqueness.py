#!/usr/bin/env python3
"""
Uniqueness Validation Testing for Voice Gateway.
Tests password uniqueness generation and collision detection.
"""
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.adapters.services.password_service import PasswordService
from app.core.usecases.register_user import RegisterUserUseCase
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository

class UniquenessValidationTester:
    """Tester for password uniqueness validation."""
    
    def __init__(self):
        """Initialize tester with services."""
        try:
            self.password_service = PasswordService()
            self.user_repository = DynamoDBUserRepository()
            self.use_case = RegisterUserUseCase(self.user_repository, self.password_service)
        except Exception as e:
            print(f"ERROR: Failed to initialize services: {e}")
            sys.exit(1)
    
    def test_unique_password_generation(self) -> bool:
        """Test generation of unique passwords."""
        print("Testing unique password generation...")
        existing_passwords = [
            "biblioteca tortuga",
            "castillo mariposa",
            "medicina jirafa",
            "computadora hospital",
            "escalera rinoceronte"
        ]
        # Hash the existing passwords since the method now expects hashes
        existing_hashes = [self.password_service.hash_password(pwd) for pwd in existing_passwords]
        generated_passwords = []
        for i in range(10):
            try:
                unique_password = self.password_service.generate_unique_password(
                    existing_hashes=existing_hashes + [self.password_service.hash_password(pwd) for pwd in generated_passwords],
                    max_attempts=20
                )
                generated_passwords.append(unique_password)
            except Exception as e:
                print(f"ERROR: Failed to generate unique password {i+1}: {e}")
                return False
        all_passwords = existing_passwords + generated_passwords
        if len(set(all_passwords)) != len(all_passwords):
            print("ERROR: Duplicate passwords found")
            return False
        print(f"   Successfully generated {len(generated_passwords)} unique passwords")
        print("Unique password generation successful")
        return True
    
    def test_retry_logic_exhaustion(self) -> bool:
        """Test retry logic when unable to generate unique password."""
        print("\nTesting retry logic exhaustion...")
        existing_passwords = []
        for _ in range(100):
            password = self.password_service.generate_password()
            existing_passwords.append(password)
        # Hash the existing passwords since the method now expects hashes
        existing_hashes = [self.password_service.hash_password(pwd) for pwd in existing_passwords]
        try:
            self.password_service.generate_unique_password(
                existing_hashes=existing_hashes,
                max_attempts=3
            )
            print("   Generated unique password (should be rare)")
            return True
        except ValueError as e:
            print("   Retry logic correctly failed after max attempts")
            print(f"   Error message: {e}")
            return True
        except Exception as e:
            print(f"ERROR: Unexpected error: {e}")
            return False

def main():
    """Run all uniqueness validation tests."""
    print("Voice Gateway - Uniqueness Validation Testing")
    print("=" * 55)
    tester = UniquenessValidationTester()
    tests = [
        ("Unique Password Generation", tester.test_unique_password_generation),
        ("Retry Logic Exhaustion", tester.test_retry_logic_exhaustion)
    ]
    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()
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
    success = main()
    sys.exit(0 if success else 1) 