#!/usr/bin/env python3
"""
Spanish Dictionary Validation for Voice Gateway.
Tests dictionary structure, word criteria, and entropy calculations.
"""
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))


class DictionaryValidator:
    """Validator for Spanish dictionary used in password generation."""
    
    def __init__(self, dictionary_path: str):
        """
        Initialize validator with dictionary file.
        
        Args:
            dictionary_path: Path to dictionary JSON file
        """
        self.dictionary_path = Path(dictionary_path)
        self.dictionary_data = None
        
    def load_dictionary(self) -> bool:
        """Load and parse dictionary file."""
        try:
            if not self.dictionary_path.exists():
                print(f"ERROR: Dictionary file not found: {self.dictionary_path}")
                return False
                
            with open(self.dictionary_path, 'r', encoding='utf-8') as f:
                self.dictionary_data = json.load(f)
                
            print(f"Dictionary loaded successfully")
            print(f"   File: {self.dictionary_path}")
            return True
            
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON format: {e}")
            return False
        except Exception as e:
            print(f"ERROR: Error loading dictionary: {e}")
            return False
    
    def validate_structure(self) -> bool:
        """Validate required dictionary structure."""
        print("\nValidating dictionary structure...")
        
        required_keys = ['metadata', 'words']
        metadata_keys = ['version', 'language', 'total_words', 'validation_criteria', 'entropy']
        
        try:
            # Check top-level structure
            for key in required_keys:
                if key not in self.dictionary_data:
                    print(f"ERROR: Missing required key: {key}")
                    return False
            
            # Check metadata structure
            metadata = self.dictionary_data['metadata']
            for key in metadata_keys:
                if key not in metadata:
                    print(f"ERROR: Missing metadata key: {key}")
                    return False
            
            # Check words is a list
            if not isinstance(self.dictionary_data['words'], list):
                print(f"ERROR: 'words' must be a list")
                return False
                
            print("Dictionary structure is valid")
            return True
            
        except Exception as e:
            print(f"ERROR: Structure validation error: {e}")
            return False
    
    def validate_words(self) -> bool:
        """Validate individual words against criteria."""
        print("\nValidating word criteria...")
        
        words = self.dictionary_data['words']
        criteria = self.dictionary_data['metadata']['validation_criteria']
        
        min_length = criteria['min_length']
        max_length = criteria['max_length']
        no_accents = criteria['no_accents']
        no_special_chars = criteria['no_special_chars']
        
        valid_words = 0
        issues = []
        
        # Valid character pattern (Spanish letters without accents)
        valid_pattern = re.compile(r'^[a-z]+$')
        
        for i, word in enumerate(words):
            word_issues = []
            
            # Check length
            if len(word) < min_length or len(word) > max_length:
                word_issues.append(f"length {len(word)} not in range {min_length}-{max_length}")
            
            # Check for accents and special characters
            if no_accents and no_special_chars:
                if not valid_pattern.match(word):
                    word_issues.append("contains accents or special characters")
            
            # Check for uppercase
            if word != word.lower():
                word_issues.append("contains uppercase letters")
            
            if word_issues:
                issues.append(f"Word '{word}' (#{i+1}): {', '.join(word_issues)}")
            else:
                valid_words += 1
        
        # Print results
        total_words = len(words)
        print(f"   Total words: {total_words}")
        print(f"   Valid words: {valid_words}")
        print(f"   Invalid words: {len(issues)}")
        
        if issues:
            print("\nWARNING: Word validation issues:")
            for issue in issues[:10]:  # Show first 10 issues
                print(f"   - {issue}")
            if len(issues) > 10:
                print(f"   ... and {len(issues) - 10} more issues")
            return False
        
        print("All words meet validation criteria")
        return True
    
    def validate_metadata_consistency(self) -> bool:
        """Validate metadata matches actual word count and properties."""
        print("\nValidating metadata consistency...")
        
        words = self.dictionary_data['words']
        metadata = self.dictionary_data['metadata']
        
        # Check word count
        actual_count = len(words)
        declared_count = metadata['total_words']
        
        if actual_count != declared_count:
            print(f"ERROR: Word count mismatch: declared {declared_count}, actual {actual_count}")
            return False
        
        # Check for duplicates
        unique_words = set(words)
        if len(unique_words) != actual_count:
            duplicates = actual_count - len(unique_words)
            print(f"ERROR: Found {duplicates} duplicate words")
            return False
        
        # Validate entropy calculation
        entropy_data = metadata['entropy']
        expected_combinations = actual_count * (actual_count - 1)  # 2 words without replacement
        declared_combinations = entropy_data['total_combinations']
        
        if expected_combinations != declared_combinations:
            print(f"ERROR: Entropy calculation error: expected {expected_combinations}, declared {declared_combinations}")
            return False
        
        print(f"Metadata consistency validated")
        print(f"   Words: {actual_count} (no duplicates)")
        print(f"   Combinations: {declared_combinations:,}")
        print(f"   Entropy: {entropy_data['entropy_bits']:.2f} bits")
        
        return True
    
    def calculate_security_metrics(self) -> Dict[str, Any]:
        """Calculate security and usability metrics."""
        print("\nCalculating security metrics...")
        
        words = self.dictionary_data['words']
        word_count = len(words)
        
        # Security metrics
        combinations_with_replacement = word_count ** 2
        combinations_without_replacement = word_count * (word_count - 1)
        entropy_bits = combinations_without_replacement.bit_length() - 1
        
        # Word length distribution
        lengths = [len(word) for word in words]
        length_distribution = {}
        for length in range(min(lengths), max(lengths) + 1):
            count = lengths.count(length)
            if count > 0:
                length_distribution[length] = count
        
        metrics = {
            "word_count": word_count,
            "combinations_without_replacement": combinations_without_replacement,
            "combinations_with_replacement": combinations_with_replacement,
            "entropy_bits": entropy_bits,
            "length_distribution": length_distribution,
            "avg_word_length": sum(lengths) / len(lengths),
            "min_word_length": min(lengths),
            "max_word_length": max(lengths)
        }
        
        print(f"   Word count: {metrics['word_count']}")
        print(f"   Total combinations: {metrics['combinations_without_replacement']:,}")
        print(f"   Entropy: ~{metrics['entropy_bits']} bits")
        print(f"   Average word length: {metrics['avg_word_length']:.1f} characters")
        print(f"   Length range: {metrics['min_word_length']}-{metrics['max_word_length']} characters")
        
        return metrics
    
    def test_word_sampling(self, sample_size: int = 10) -> bool:
        """Test random word selection to verify accessibility."""
        print(f"\nTesting word sampling ({sample_size} samples)...")
        
        import random
        
        words = self.dictionary_data['words']
        
        try:
            # Test random selection
            sample_words = random.choices(words, k=sample_size)
            sample_pairs = []
            
            for i in range(0, sample_size, 2):
                if i + 1 < sample_size:
                    pair = f"{sample_words[i]} {sample_words[i+1]}"
                    sample_pairs.append(pair)
            
            print("   Sample password pairs:")
            for pair in sample_pairs:
                print(f"   - {pair}")
            
            print("Word sampling works correctly")
            return True
            
        except Exception as e:
            print(f"ERROR: Word sampling failed: {e}")
            return False


def main():
    """Run complete dictionary validation."""
    print("Voice Gateway - Spanish Dictionary Validation")
    print("=" * 55)
    
    # Dictionary file path
    dictionary_path = Path(__file__).parent.parent / "app" / "config" / "spanish_dictionary.json"
    
    # Initialize validator
    validator = DictionaryValidator(dictionary_path)
    
    # Run validation tests
    tests = [
        ("Load Dictionary", validator.load_dictionary),
        ("Validate Structure", validator.validate_structure),
        ("Validate Words", validator.validate_words),
        ("Validate Metadata", validator.validate_metadata_consistency),
        ("Test Sampling", lambda: validator.test_word_sampling(10))
    ]
    
    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()
        if not results[test_name]:
            print(f"\nERROR: {test_name} failed. Stopping validation.")
            break
    
    # Calculate metrics if basic validation passed
    if results.get("Validate Structure") and results.get("Load Dictionary"):
        validator.calculate_security_metrics()
    
    # Summary
    print("\n" + "=" * 55)
    print("Dictionary Validation Results:")
    print("-" * 35)
    
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {test_name}: {status}")
    
    if all(results.values()):
        print("\nDictionary validation completed successfully!")
        print("Dictionary is ready for password generation service.")
        return True
    else:
        print(f"\nDictionary validation failed.")
        print("Please fix issues before proceeding.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 