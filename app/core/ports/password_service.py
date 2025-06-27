"""
Password service port for Voice Gateway.
Defines interface for secure password generation for voice authentication.
"""
from abc import ABC, abstractmethod
from typing import Tuple, List


class PasswordServicePort(ABC):
    """
    Abstract interface for password generation services.
    
    Supports voice authentication requirements:
    - Exactly 2 words for memorability
    - Phonetically clear words for speech recognition
    - Cryptographically secure generation
    - Uniqueness validation against existing passwords
    """
    
    @abstractmethod
    def generate_password(self) -> Tuple[str, List[str]]:
        """
        Generate a secure 2-word password for voice authentication.
        
        Returns:
            Tuple[str, List[str]]: (complete_password, list_of_words_used)
            
        Example:
            ("casa verde", ["casa", "verde"])
            
        Raises:
            ValueError: If unable to generate unique password after retries
            RuntimeError: If dictionary is unavailable or corrupted
        """
        pass
    
    @abstractmethod
    def validate_password_format(self, password: str) -> bool:
        """
        Validate if password matches expected format.
        
        Args:
            password: Password string to validate
            
        Returns:
            bool: True if password format is valid
            
        Example:
            validate_password_format("casa verde") → True
            validate_password_format("word") → False (only 1 word)
            validate_password_format("casa verde azul") → False (3 words)
        """
        pass
    
    @abstractmethod
    def get_dictionary_info(self) -> dict:
        """
        Get information about the dictionary being used.
        
        Returns:
            dict: Dictionary metadata (size, language, entropy, etc.)
        """
        pass 