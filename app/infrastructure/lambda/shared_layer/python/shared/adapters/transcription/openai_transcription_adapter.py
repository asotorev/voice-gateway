"""
OpenAI Transcription Adapter.

Adapter implementation that connects the TranscriptionServicePort interface
with the OpenAI Whisper transcription service, following Clean Architecture
principles and adapter pattern.
"""
import logging
from typing import Dict, Any

from ...core.ports.transcription_service import TranscriptionServicePort, TranscriptionError
from ...core.services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)


class OpenAITranscriptionAdapter(TranscriptionServicePort):
    """
    Adapter that implements TranscriptionServicePort using OpenAI Whisper API.
    
    This adapter connects the Clean Architecture port interface with the
    OpenAI transcription service implementation, allowing for dependency
    inversion and testability.
    """
    
    def __init__(self, transcription_service: TranscriptionService):
        """
        Initialize the OpenAI transcription adapter.
        
        Args:
            transcription_service: TranscriptionService implementation
        """
        self.transcription_service = transcription_service
        logger.debug("OpenAI transcription adapter initialized")
    
    async def transcribe_audio(
        self, 
        audio_data: bytes, 
        language: str = "es",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Transcribe audio data to text using OpenAI Whisper.
        
        Args:
            audio_data: Raw audio bytes to transcribe
            language: Language code (e.g., 'es', 'en', 'auto')
            **kwargs: Additional transcription parameters
            
        Returns:
            Dictionary containing transcription results
            
        Raises:
            TranscriptionError: If transcription fails
            ValueError: If audio data is invalid
        """
        try:
            # Extract filename from kwargs if provided
            filename = kwargs.get('filename', 'audio.wav')
            
            # Use the underlying transcription service
            result = await self.transcription_service.transcribe_audio(
                audio_data=audio_data,
                language=language,
                filename=filename
            )
            
            logger.debug("OpenAI transcription completed successfully", extra={
                "text_length": len(result.get('text', '')),
                "confidence": result.get('confidence', 0.0),
                "language": result.get('language', language)
            })
            
            return result
            
        except ValueError as e:
            # Re-raise validation errors as-is
            logger.error("Audio validation failed", extra={"error": str(e)})
            raise
            
        except Exception as e:
            # Wrap other exceptions in TranscriptionError
            error_message = f"OpenAI transcription failed: {str(e)}"
            logger.error("OpenAI transcription failed", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "audio_size": len(audio_data) if audio_data else 0
            })
            
            # Determine error code based on exception type
            error_code = "TRANSCRIPTION_FAILED"
            if "timeout" in str(e).lower():
                error_code = "TIMEOUT"
            elif "api" in str(e).lower() or "request" in str(e).lower():
                error_code = "API_ERROR"
            elif "audio" in str(e).lower():
                error_code = "AUDIO_ERROR"
            
            raise TranscriptionError(
                message=error_message,
                error_code=error_code,
                details={
                    "original_error": str(e),
                    "error_type": type(e).__name__,
                    "audio_size_bytes": len(audio_data) if audio_data else 0
                }
            )
    
    async def validate_audio_for_transcription(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Validate audio data for transcription compatibility.
        
        Args:
            audio_data: Raw audio bytes to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            return await self.transcription_service.validate_audio_for_transcription(audio_data)
            
        except Exception as e:
            logger.error("Audio validation failed", extra={
                "error": str(e),
                "audio_size": len(audio_data) if audio_data else 0
            })
            
            return {
                'is_valid': False,
                'format': 'unknown',
                'size_mb': len(audio_data) / (1024 * 1024) if audio_data else 0,
                'issues': [f"Validation error: {str(e)}"]
            }
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get supported languages for transcription.
        
        Returns:
            Dictionary mapping language codes to language names
        """
        return self.transcription_service.get_supported_languages()
    
    def get_transcription_config(self) -> Dict[str, Any]:
        """
        Get current transcription configuration.
        
        Returns:
            Dictionary with current configuration settings
        """
        config = self.transcription_service.get_transcription_config()
        
        # Add adapter-specific metadata
        config['adapter'] = 'OpenAI'
        config['adapter_version'] = '1.0.0'
        
        return config
