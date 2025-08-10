"""
Voice authentication port (interface) for authentication operations.

This module defines the contract for voice authentication implementations,
following Clean Architecture principles by defining the interface
without implementation details.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class VoiceAuthenticationPort(ABC):
    """
    Port (interface) for voice authentication operations.
    
    Defines the contract for authenticating users through voice embedding
    comparison and similarity analysis. Implementations can vary in their
    similarity algorithms and confidence calculations.
    """
    
    @abstractmethod
    def calculate_cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two voice embeddings.
        
        Args:
            embedding1: First voice embedding vector
            embedding2: Second voice embedding vector
            
        Returns:
            Cosine similarity score between 0.0 and 1.0
            
        Raises:
            ValueError: If embeddings are invalid or incompatible
        """
        pass
    
    @abstractmethod
    def compare_against_stored_embeddings(
        self, 
        input_embedding: List[float], 
        stored_embeddings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare input embedding against multiple stored embeddings.
        
        Args:
            input_embedding: The input voice embedding to authenticate
            stored_embeddings: List of stored embeddings with metadata
            
        Returns:
            Dictionary with similarity analysis results including:
            - similarities: List of individual similarity scores
            - average_similarity: Average similarity across all comparisons
            - max_similarity: Maximum similarity found
            - total_comparisons: Number of embeddings compared
            
        Raises:
            ValueError: If insufficient data or invalid inputs
        """
        pass
    
    @abstractmethod
    def calculate_authentication_confidence(self, comparison_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate authentication confidence based on similarity comparison results.
        
        Args:
            comparison_result: Result from compare_against_stored_embeddings
            
        Returns:
            Dictionary with confidence analysis including:
            - confidence_score: Final confidence score [0.0, 1.0]
            - authentication_result: Authentication result status
            - meets_threshold: Boolean if authentication threshold is met
            
        """
        pass
    
    @abstractmethod
    def authenticate_voice(
        self, 
        input_embedding: List[float], 
        stored_embeddings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Complete voice authentication workflow.
        
        Combines embedding comparison and confidence calculation into a single
        authentication decision with detailed analysis.
        
        Args:
            input_embedding: Voice embedding to authenticate
            stored_embeddings: User's stored voice embeddings
            
        Returns:
            Complete authentication result with similarity analysis and confidence
            
        Raises:
            ValueError: If inputs are invalid or insufficient
        """
        pass
    
    @abstractmethod
    def get_authentication_config(self) -> Dict[str, Any]:
        """
        Get authentication configuration and settings.
        
        Returns:
            Dictionary with current authentication configuration
        """
        pass
