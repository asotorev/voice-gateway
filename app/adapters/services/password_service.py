"""
Password service for Voice Gateway.
Generates cryptographically secure 2-word passwords using curated Spanish dictionary.
"""
import json
import secrets
from pathlib import Path
from typing import Tuple, List, Dict, Any
from app.core.ports.password_service import PasswordServicePort


class PasswordService(PasswordServicePort):
    """
    Password generation service using curated dictionary.
    
    Generates cryptographically secure 2-word passwords optimized for
    voice authentication with Whisper ASR compatibility.
    """
    
    def __init__(self, dictionary_path: str = None):
        """
        Initialize password service.
        
        Args:
            dictionary_path: Path to dictionary JSON file
        """
        if dictionary_path is None:
            # Default to Spanish dictionary
            self.dictionary_path = Path(__file__).parent.parent.parent / "config" / "spanish_dictionary.json"
        else:
            self.dictionary_path = Path(dictionary_path)
            
        self._dictionary_data = None
        self._words = None
        self._load_dictionary()
        
    def _load_dictionary(self) -> None:
        """Load and validate dictionary."""
        try:
            with open(self.dictionary_path, 'r', encoding='utf-8') as f:
                self._dictionary_data = json.load(f)
                
            # Validate required fields
            if 'words' not in self._dictionary_data:
                raise RuntimeError("Dictionary missing 'words' field")
                
            if 'metadata' not in self._dictionary_data:
                raise RuntimeError("Dictionary missing 'metadata' field")
                
            self._words = self._dictionary_data['words']
            declared_count = self._dictionary_data['metadata']['total_words']
            
            # Verify word count matches metadata
            actual_count = len(self._words)
            
            if actual_count != declared_count:
                raise RuntimeError(f"Word count mismatch: declared {declared_count}, actual {actual_count}")
                
            if actual_count == 0:
                raise RuntimeError("Dictionary contains no words")
                
        except FileNotFoundError:
            raise RuntimeError(f"Dictionary file not found: {self.dictionary_path}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in dictionary file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading dictionary: {e}")
    
    def generate_password(self) -> str:
        """
        Generate a cryptographically secure 2-word password.
        
        Returns:
            str: Complete password string (e.g., "biblioteca tortuga")
            
        Raises:
            RuntimeError: If dictionary is not available
        """
        if not self._words:
            raise RuntimeError("Dictionary not loaded")
            
        # Use cryptographically secure random generator
        secure_random = secrets.SystemRandom()
        
        # Select 2 different words without replacement
        # This ensures no "hospital hospital" passwords
        selected_words = secure_random.sample(self._words, 2)
        
        # Create password string
        password = " ".join(selected_words)
        
        return password
    
    def validate_password_format(self, password: str) -> bool:
        """
        Validate if password matches expected 2-word format.
        
        Args:
            password: Password string to validate
            
        Returns:
            bool: True if password format is valid
        """
        if not password or not isinstance(password, str):
            return False
            
        # Split by whitespace and check word count
        words = password.strip().split()
        
        # Must be exactly 2 words
        if len(words) != 2:
            return False
            
        # Each word must be from our dictionary
        for word in words:
            if word not in self._words:
                return False
                
        return True
    
    def get_dictionary_info(self) -> Dict[str, Any]:
        """
        Get information about the dictionary being used.
        
        Returns:
            dict: Dictionary metadata
        """
        if not self._dictionary_data:
            return {}
        metadata = self._dictionary_data['metadata']
        return {
            "language": metadata.get("language", "unknown"),
            "version": metadata.get("version", "unknown"),
            "total_words": metadata.get("total_words", 0),
            "total_combinations": metadata.get("total_combinations", 0),
            "entropy_bits": metadata.get("entropy_bits", 0),
            "validation_criteria": metadata.get("validation_criteria", {}),
            "last_updated": metadata.get("last_updated", "unknown")
        }
    
    def calculate_entropy(self) -> float:
        """
        Calculate entropy in bits for current dictionary.
        
        Returns:
            float: Entropy in bits
        """
        if not self._words:
            return 0.0
            
        word_count = len(self._words)
        # Calculate combinations without replacement (word1 != word2)
        combinations = word_count * (word_count - 1)
        
        # Calculate entropy: log2(combinations)
        import math
        entropy = math.log2(combinations) if combinations > 0 else 0.0
        
        return entropy
    
    def get_sample_passwords(self, count: int = 5) -> List[Tuple[str, List[str]]]:
        """
        Generate sample passwords for testing/demonstration.
        
        Args:
            count: Number of sample passwords to generate
            
        Returns:
            List[Tuple[str, List[str]]]: List of (password, words) tuples
        """
        samples = []
        
        for _ in range(count):
            try:
                password, words = self.generate_password()
                samples.append((password, words))
            except Exception:
                # Skip failed generation
                continue
                
        return samples
    
    def hash_password(self, password: str) -> str:
        """
        Hash password using SHA-256.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hexadecimal hash of password
        """
        import hashlib
        return hashlib.sha256(password.encode('utf-8')).hexdigest()