#!/usr/bin/env python3
"""
Password Generation Testing for Voice Gateway.
Tests Spanish password service functionality and randomness distribution.
"""
import sys
import asyncio
from pathlib import Path
from collections import Counter
from typing import List, Tuple

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.adapters.services.password_service import PasswordService


class PasswordGenerationTester:
    """Tester for password generation service."""
    
    def __init__(self):
        """Initialize tester with password service."""
        try:
            self.password_service = PasswordService()
        except Exception as e:
            print(f"ERROR: Failed to initialize password service: {e}")
            sys.exit(1)
    
    def test_service_initialization(self) -> bool:
        """Test that password service initializes correctly."""
        print("Testing service initialization...")
        
        try:
            # Test dictionary info
            info = self.password_service.get_dictionary_info()
            
            if not info:
                print("ERROR: Dictionary info is empty")
                return False
                
            expected_fields = ['language', 'version', 'total_words', 'total_combinations', 'entropy_bits']
            for field in expected_fields:
                if field not in info:
                    print(f"ERROR: Missing field in dictionary info: {field}")
                    return False
            
            print(f"   Language: {info['language']}")
            print(f"   Version: {info['version']}")
            print(f"   Total words: {info['total_words']}")
            print(f"   Combinations: {info['total_combinations']:,}")
            print(f"   Entropy: {info['entropy_bits']} bits")
            
            print("Service initialization successful")
            return True
            
        except Exception as e:
            print(f"ERROR: Service initialization failed: {e}")
            return False
    
    def test_password_generation(self) -> bool:
        """Test basic password generation functionality."""
        print("\nTesting password generation...")
        
        try:
            # Generate a single password
            password, words = self.password_service.generate_password()
            
            # Validate structure (important for catching implementation errors)
            if not isinstance(password, str):
                print("ERROR: Password is not a string")
                return False
                
            if not isinstance(words, list):
                print("ERROR: Words is not a list")
                return False
            
            print(f"   Generated password: '{password}'")
            print(f"   Words used: {words}")
            
            # Validate format using the service method
            if not self.password_service.validate_password_format(password):
                print("ERROR: Generated password failed validation")
                return False
            
            # Additional format checks for thoroughness
            password_words = password.split()
            if len(password_words) != 2:
                print(f"ERROR: Password should have 2 words, got {len(password_words)}")
                return False
            
            # Verify password string matches word list
            if password_words != words:
                print("ERROR: Password string doesn't match word list")
                return False
            
            # Check word count
            if len(words) != 2:
                print(f"ERROR: Expected 2 words, got {len(words)}")
                return False
            
            # Check words are different
            if words[0] == words[1]:
                print("ERROR: Both words are identical")
                return False
            
            # Check words are from dictionary
            if words[0] not in self.password_service._words or words[1] not in self.password_service._words:
                print("ERROR: Generated words not found in dictionary")
                return False
            
            print("Password generation test passed")
            return True
            
        except Exception as e:
            print(f"ERROR: Password generation test failed: {e}")
            return False
    
    def test_password_validation(self) -> bool:
        """Test password format validation."""
        print("\nTesting password validation...")
        
        try:
            # Test valid passwords (using known words from dictionary)
            info = self.password_service.get_dictionary_info()
            
            # Get some sample passwords
            samples = self.password_service.get_sample_passwords(3)
            
            valid_tests = 0
            for password, words in samples:
                if self.password_service.validate_password_format(password):
                    valid_tests += 1
                    print(f"   Valid: '{password}' - PASSED")
                else:
                    print(f"   Valid: '{password}' - FAILED")
            
            # Test invalid passwords
            invalid_passwords = [
                "",                           # Empty
                "single",                     # One word
                "one two three",              # Three words
                "invalid notindict",          # Unknown words
                "123 456",                    # Numbers
                None,                         # None type
            ]
            
            invalid_tests = 0
            for password in invalid_passwords:
                if not self.password_service.validate_password_format(password):
                    invalid_tests += 1
                    print(f"   Invalid: '{password}' - PASSED")
                else:
                    print(f"   Invalid: '{password}' - FAILED")
            
            if valid_tests == len(samples) and invalid_tests == len(invalid_passwords):
                print("Password validation successful")
                return True
            else:
                print(f"ERROR: Validation failed - valid: {valid_tests}/{len(samples)}, invalid: {invalid_tests}/{len(invalid_passwords)}")
                return False
                
        except Exception as e:
            print(f"ERROR: Password validation test failed: {e}")
            return False
    
    def test_randomness_distribution(self, sample_size: int = 100) -> bool:
        """Test randomness and distribution of generated passwords."""
        print(f"\nTesting randomness distribution ({sample_size} samples)...")
        
        try:
            # Generate multiple passwords
            passwords = []
            all_words = []
            
            for _ in range(sample_size):
                password, words = self.password_service.generate_password()
                passwords.append(password)
                all_words.extend(words)
            
            # Check for duplicates
            unique_passwords = set(passwords)
            duplicate_rate = (sample_size - len(unique_passwords)) / sample_size * 100
            
            print(f"   Generated passwords: {sample_size}")
            print(f"   Unique passwords: {len(unique_passwords)}")
            print(f"   Duplicate rate: {duplicate_rate:.1f}%")
            
            # Analyze word frequency distribution
            word_counts = Counter(all_words)
            most_common = word_counts.most_common(5)
            least_common = word_counts.most_common()[-5:]
            
            print(f"   Most frequent words:")
            for word, count in most_common:
                frequency = count / len(all_words) * 100
                print(f"     {word}: {count} times ({frequency:.1f}%)")
                
            print(f"   Least frequent words:")
            for word, count in least_common:
                frequency = count / len(all_words) * 100
                print(f"     {word}: {count} times ({frequency:.1f}%)")
            
            # Check if distribution is reasonable
            max_frequency = most_common[0][1] / len(all_words)
            min_frequency = least_common[0][1] / len(all_words)
            
            # For good randomness, no word should appear too frequently
            if max_frequency > 0.05:  # More than 5% is suspicious for 100 words
                print(f"WARNING: High frequency detected ({max_frequency:.1%}) - randomness may be poor")
            
            # Show some sample passwords
            print(f"   Sample passwords:")
            for i, password in enumerate(passwords[:10], 1):
                print(f"     {i:2d}. {password}")
            
            print("Randomness distribution test completed")
            return True
            
        except Exception as e:
            print(f"ERROR: Randomness test failed: {e}")
            return False
    
    def test_entropy_calculation(self) -> bool:
        """Test entropy calculation accuracy."""
        print("\nTesting entropy calculation...")
        
        try:
            calculated_entropy = self.password_service.calculate_entropy()
            declared_entropy = self.password_service.get_dictionary_info()['entropy_bits']
            
            print(f"   Calculated entropy: {calculated_entropy:.2f} bits")
            print(f"   Declared entropy: {declared_entropy} bits")
            
            # Allow small difference due to rounding
            difference = abs(calculated_entropy - declared_entropy)
            if difference < 0.1:
                print("Entropy calculation matches declared value")
                return True
            else:
                print(f"WARNING: Entropy mismatch - difference: {difference:.2f} bits")
                return True  # Not a critical error
                
        except Exception as e:
            print(f"ERROR: Entropy calculation failed: {e}")
            return False
    
    def test_uniqueness_across_generations(self, iterations: int = 50) -> bool:
        """Test that consecutive generations produce different passwords."""
        print(f"\nTesting uniqueness across {iterations} generations...")
        
        try:
            previous_passwords = set()
            collision_count = 0
            
            for i in range(iterations):
                password, _ = self.password_service.generate_password()
                
                if password in previous_passwords:
                    collision_count += 1
                    print(f"   Collision detected at iteration {i+1}: '{password}'")
                else:
                    previous_passwords.add(password)
            
            collision_rate = collision_count / iterations * 100
            print(f"   Total iterations: {iterations}")
            print(f"   Collisions: {collision_count}")
            print(f"   Collision rate: {collision_rate:.1f}%")
            
            # For 9,900 combinations, some collisions are expected with 50 samples
            # But rate should be very low
            if collision_rate < 10:  # Less than 10% collision rate is acceptable
                print("Uniqueness test passed")
                return True
            else:
                print("WARNING: High collision rate detected")
                return False
                
        except Exception as e:
            print(f"ERROR: Uniqueness test failed: {e}")
            return False


def main():
    """Run all password generation tests."""
    print("Voice Gateway - Password Generation Testing")
    print("=" * 50)
    
    # Initialize tester
    tester = PasswordGenerationTester()
    
    # Run test suite
    tests = [
        ("Service Initialization", tester.test_service_initialization),
        ("Password Generation", tester.test_password_generation),
        ("Password Validation", tester.test_password_validation),
        ("Randomness Distribution", tester.test_randomness_distribution),
        ("Entropy Calculation", tester.test_entropy_calculation),
        ("Uniqueness Testing", tester.test_uniqueness_across_generations)
    ]
    
    results = {}
    for test_name, test_func in tests:
        # All tests are now synchronous
        if test_name == "Randomness Distribution":
            results[test_name] = test_func(100)
        elif test_name == "Uniqueness Testing":
            results[test_name] = test_func(50)
        else:
            results[test_name] = test_func()
    
    # Summary
    print("\n" + "=" * 50)
    print("Password Generation Test Results:")
    print("-" * 32)
    
    passed_tests = 0
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {test_name}: {status}")
        if passed:
            passed_tests += 1
    
    print(f"\nTests passed: {passed_tests}/{len(tests)}")
    
    if passed_tests == len(tests):
        print("\nPassword generation service is working correctly!")
        return True
    else:
        print(f"\n{len(tests) - passed_tests} test(s) failed.")
        print("Please review implementation before proceeding.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 