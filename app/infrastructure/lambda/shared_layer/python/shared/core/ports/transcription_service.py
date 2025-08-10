"""
Transcription service port for speech-to-text operations.

This module defines the contract for transcription implementations,
following Clean Architecture principles by defining the interface
without implementation details.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class TranscriptionServicePort(ABC):
    """
    Port (interface) for audio transcription operations.
    
    Defines the contract for converting audio to text using speech
    recognition services. Implementations can vary in their underlying
    transcription engines (OpenAI Whisper, Google Speech, etc.).
    """
    
    @abstractmethod
    async def transcribe_audio(
        self, 
        audio_data: bytes, 
        language: str = "es",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Raw audio bytes to transcribe
            language: Language code (e.g., 'es', 'en', 'auto')
            **kwargs: Additional transcription parameters
            
        Returns:
            Dictionary containing transcription results:
            - text: Transcribed text
            - confidence: Confidence score (0.0-1.0)
            - language: Detected/used language
            - duration: Audio duration in seconds
            - processing_time_ms: Time taken to process
            
        Raises:
            TranscriptionError: If transcription fails
            ValueError: If audio data is invalid
        """
        pass
    
    @abstractmethod
    async def validate_audio_for_transcription(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Validate audio data for transcription compatibility.
        
        Args:
            audio_data: Raw audio bytes to validate
            
        Returns:
            Dictionary with validation results:
            - is_valid: Boolean indicating if audio is suitable
            - format: Detected audio format
            - duration: Audio duration in seconds
            - sample_rate: Audio sample rate
            - issues: List of any issues found
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get supported languages for transcription.
        
        Returns:
            Dictionary mapping language codes to language names
        """
        pass
    
    @abstractmethod
    def get_transcription_config(self) -> Dict[str, Any]:
        """
        Get current transcription configuration.
        
        Returns:
            Dictionary with current configuration settings
        """
        pass


class TranscriptionError(Exception):
    """Exception raised when transcription operations fail."""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        """
        Initialize transcription error.
        
        Args:
            message: Error message
            error_code: Specific error code (e.g., 'AUDIO_TOO_LONG')
            details: Additional error details
        """
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
