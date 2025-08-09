"""
Audio processor port (interface) for voice processing operations.

This module defines the contract for audio processing implementations,
following Clean Architecture principles by defining the interface
without implementation details.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class AudioProcessorPort(ABC):
    """
    Port (interface) for audio processing operations.
    
    Defines the contract for processing audio data and generating
    voice embeddings. Implementations can be mock (for development)
    or real ML models (for production).
    """
    
    @abstractmethod
    def generate_embedding(self, audio_data: bytes, metadata: Dict[str, Any]) -> List[float]:
        """
        Generate voice embedding from audio data.
        
        Args:
            audio_data: Raw audio file bytes
            metadata: Audio file metadata (size, format, etc.)
            
        Returns:
            Voice embedding as list of floats
            
        Raises:
            ValueError: If audio data is invalid
            RuntimeError: If processing fails
        """
        pass
    
    @abstractmethod
    def validate_audio_quality(self, audio_data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate audio quality for embedding generation.
        
        Args:
            audio_data: Raw audio file bytes
            metadata: Audio file metadata
            
        Returns:
            Dict with quality assessment results
        """
        pass
    
    @abstractmethod
    def get_processor_info(self) -> Dict[str, Any]:
        """
        Get information about the processor implementation.
        
        Returns:
            Dict with processor details
        """
        pass
