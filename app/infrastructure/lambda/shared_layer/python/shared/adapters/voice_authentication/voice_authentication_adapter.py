"""
Voice Authentication Adapter.

Adapter implementation that connects the VoiceAuthenticationPort interface
with the VoiceAuthenticationService implementation, following Clean Architecture
principles and adapter pattern.
"""
import logging
from typing import List, Dict, Any

from ...core.ports.voice_authentication import VoiceAuthenticationPort
from ...core.services.voice_authentication_service import VoiceAuthenticationService

logger = logging.getLogger(__name__)


class VoiceAuthenticationAdapter(VoiceAuthenticationPort):
    """
    Adapter that implements VoiceAuthenticationPort using VoiceAuthenticationService.
    
    This adapter connects the Clean Architecture port interface with the
    concrete implementation, allowing for dependency inversion and testability.
    """
    
    def __init__(self, voice_auth_service: VoiceAuthenticationService):
        """
        Initialize the voice authentication adapter.
        
        Args:
            voice_auth_service: VoiceAuthenticationService implementation
        """
        self.voice_auth_service = voice_auth_service
        logger.debug("Voice authentication adapter initialized")
    
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
        return self.voice_auth_service.calculate_cosine_similarity(embedding1, embedding2)
    
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
            Dictionary with similarity analysis results
            
        Raises:
            ValueError: If insufficient data or invalid inputs
        """
        return self.voice_auth_service.compare_against_stored_embeddings(
            input_embedding, stored_embeddings
        )
    
    def calculate_authentication_confidence(self, comparison_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate authentication confidence based on similarity comparison results.
        
        Args:
            comparison_result: Result from compare_against_stored_embeddings
            
        Returns:
            Dictionary with confidence analysis
        """
        return self.voice_auth_service.calculate_authentication_confidence(comparison_result)
    
    def authenticate_voice(
        self, 
        input_embedding: List[float], 
        stored_embeddings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Complete voice authentication workflow.
        
        Args:
            input_embedding: Voice embedding to authenticate
            stored_embeddings: User's stored voice embeddings
            
        Returns:
            Complete authentication result with similarity analysis and confidence
            
        Raises:
            ValueError: If inputs are invalid or insufficient
        """
        return self.voice_auth_service.authenticate_voice(input_embedding, stored_embeddings)
    
    def get_authentication_config(self) -> Dict[str, Any]:
        """
        Get authentication configuration and settings.
        
        Returns:
            Dictionary with current authentication configuration
        """
        return self.voice_auth_service.config.to_dict()
