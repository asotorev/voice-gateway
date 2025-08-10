"""
OpenAI Whisper Transcription Service.

Provides audio transcription capabilities using OpenAI's Whisper API,
designed for serverless Lambda environments with proper error handling
and configuration management.
"""
import os
import io
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

try:
    import openai
    from openai import OpenAI
except ImportError:
    # Graceful degradation for environments without OpenAI
    openai = None
    OpenAI = None

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionConfig:
    """Configuration for OpenAI Whisper transcription service."""
    
    # OpenAI Configuration
    api_key: str = ""
    model: str = "whisper-1"
    
    # Transcription Settings
    language: str = "es"  # Default to Spanish
    temperature: float = 0.0  # Deterministic output
    
    # Audio Constraints
    max_file_size_mb: int = 25  # OpenAI limit
    supported_formats: tuple = ("mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm")
    
    # Timeout Settings
    request_timeout_seconds: int = 30
    max_retries: int = 3
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.api_key:
            self.api_key = os.getenv('OPENAI_API_KEY', '')
            
        if not self.api_key:
            logger.warning("OpenAI API key not found. Transcription will not work.")
            
        if self.temperature < 0.0 or self.temperature > 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
    
    @classmethod
    def from_environment(cls) -> "TranscriptionConfig":
        """Create configuration from environment variables."""
        return cls(
            api_key=os.getenv('OPENAI_API_KEY', ''),
            model=os.getenv('TRANSCRIPTION_MODEL', 'whisper-1'),
            language=os.getenv('TRANSCRIPTION_LANGUAGE', 'es'),
            temperature=float(os.getenv('TRANSCRIPTION_TEMPERATURE', '0.0')),
            request_timeout_seconds=int(os.getenv('TRANSCRIPTION_TIMEOUT', '30')),
            max_retries=int(os.getenv('TRANSCRIPTION_MAX_RETRIES', '3'))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'model': self.model,
            'language': self.language,
            'temperature': self.temperature,
            'max_file_size_mb': self.max_file_size_mb,
            'supported_formats': list(self.supported_formats),
            'request_timeout_seconds': self.request_timeout_seconds,
            'max_retries': self.max_retries
        }


class TranscriptionService:
    """
    OpenAI Whisper transcription service for audio-to-text conversion.
    
    Provides reliable audio transcription using OpenAI's Whisper API
    with proper error handling, retry logic, and configuration management.
    """
    
    def __init__(self, config: Optional[TranscriptionConfig] = None):
        """
        Initialize the transcription service.
        
        Args:
            config: Transcription configuration, defaults to environment-based config
        """
        self.config = config or TranscriptionConfig.from_environment()
        self._client: Optional[OpenAI] = None
        
        if openai is None:
            logger.error("OpenAI library not installed. Cannot initialize transcription service.")
            raise ImportError("OpenAI library is required for transcription service")
        
        logger.info("Transcription service initialized", extra=self.config.to_dict())
    
    @property
    def client(self) -> OpenAI:
        """Get OpenAI client (lazy initialization)."""
        if self._client is None:
            if not self.config.api_key:
                raise ValueError("OpenAI API key is required for transcription")
            
            self._client = OpenAI(
                api_key=self.config.api_key,
                timeout=self.config.request_timeout_seconds
            )
            logger.debug("OpenAI client initialized")
        
        return self._client
    
    async def transcribe_audio(
        self, 
        audio_data: bytes, 
        language: str = None,
        filename: str = "audio.wav"
    ) -> Dict[str, Any]:
        """
        Transcribe audio data to text using OpenAI Whisper.
        
        Args:
            audio_data: Raw audio bytes
            language: Language code override (defaults to config)
            filename: Filename for the audio (affects format detection)
            
        Returns:
            Dictionary with transcription results
            
        Raises:
            ValueError: If audio data is invalid
            Exception: If transcription fails
        """
        start_time = time.time()
        
        logger.info("Starting audio transcription", extra={
            "audio_size_bytes": len(audio_data),
            "language": language or self.config.language,
            "filename": filename
        })
        
        try:
            # Validate audio data
            validation_result = await self.validate_audio_for_transcription(audio_data)
            if not validation_result['is_valid']:
                raise ValueError(f"Audio validation failed: {validation_result['issues']}")
            
            # Prepare audio file for API
            audio_file = io.BytesIO(audio_data)
            audio_file.name = filename
            
            # Prepare transcription parameters
            transcription_params = {
                'file': audio_file,
                'model': self.config.model,
                'language': language or self.config.language,
                'temperature': self.config.temperature,
                'response_format': 'verbose_json'  # Get detailed response
            }
            
            # Perform transcription with retry logic
            response = await self._transcribe_with_retries(transcription_params)
            
            # Process response
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            result = {
                'text': response.text.strip(),
                'confidence': getattr(response, 'confidence', 0.95),  # Whisper doesn't always provide confidence
                'language': response.language if hasattr(response, 'language') else (language or self.config.language),
                'duration': getattr(response, 'duration', 0.0),
                'processing_time_ms': processing_time_ms,
                'model_used': self.config.model,
                'transcribed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Add segments if available (detailed breakdown)
            if hasattr(response, 'segments') and response.segments:
                result['segments'] = [
                    {
                        'text': segment.text.strip(),
                        'start': segment.start,
                        'end': segment.end,
                        'confidence': getattr(segment, 'avg_logprob', 0.95)
                    }
                    for segment in response.segments
                ]
            
            logger.info("Audio transcription completed successfully", extra={
                "text_length": len(result['text']),
                "confidence": result['confidence'],
                "duration": result['duration'],
                "processing_time_ms": processing_time_ms
            })
            
            return result
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.error("Audio transcription failed", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "audio_size_bytes": len(audio_data),
                "processing_time_ms": processing_time_ms
            })
            
            raise
    
    async def _transcribe_with_retries(self, params: Dict[str, Any]) -> Any:
        """Perform transcription with retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Transcription attempt {attempt + 1}/{self.config.max_retries}")
                
                # Reset file pointer for retries
                if hasattr(params['file'], 'seek'):
                    params['file'].seek(0)
                
                # Call OpenAI API
                response = self.client.audio.transcriptions.create(**params)
                
                logger.debug(f"Transcription successful on attempt {attempt + 1}")
                return response
                
            except Exception as e:
                last_exception = e
                
                logger.warning(f"Transcription attempt {attempt + 1} failed", extra={
                    "error": str(e),
                    "attempt": attempt + 1,
                    "max_retries": self.config.max_retries
                })
                
                # Don't retry on certain errors
                if isinstance(e, openai.BadRequestError):
                    logger.error("Bad request error - not retrying", extra={"error": str(e)})
                    break
                
                # Wait before retry (exponential backoff)
                if attempt < self.config.max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s...
                    logger.debug(f"Waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
        
        # All retries failed
        raise Exception(f"Transcription failed after {self.config.max_retries} attempts: {last_exception}")
    
    async def validate_audio_for_transcription(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Validate audio data for transcription compatibility.
        
        Args:
            audio_data: Raw audio bytes to validate
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        
        # Check file size
        size_mb = len(audio_data) / (1024 * 1024)
        if size_mb > self.config.max_file_size_mb:
            issues.append(f"File size {size_mb:.1f}MB exceeds limit of {self.config.max_file_size_mb}MB")
        
        # Check minimum size
        if len(audio_data) < 1024:  # 1KB minimum
            issues.append("Audio file too small (minimum 1KB)")
        
        # Basic format validation (simple magic number checks)
        format_detected = self._detect_audio_format(audio_data)
        
        return {
            'is_valid': len(issues) == 0,
            'format': format_detected,
            'size_mb': size_mb,
            'issues': issues
        }
    
    def _detect_audio_format(self, audio_data: bytes) -> str:
        """Detect audio format from file header."""
        if len(audio_data) < 12:
            return "unknown"
        
        # Check common audio format magic numbers
        header = audio_data[:12]
        
        if header.startswith(b'RIFF') and b'WAVE' in header:
            return "wav"
        elif header.startswith(b'ID3') or header[1:4] == b'ID3':
            return "mp3"
        elif header.startswith(b'\xff\xfb') or header.startswith(b'\xff\xf3') or header.startswith(b'\xff\xf2'):
            return "mp3"
        elif header[4:8] == b'ftyp':
            return "m4a"
        else:
            return "unknown"
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages for transcription."""
        return {
            'es': 'Spanish',
            'en': 'English',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'auto': 'Auto-detect'
        }
    
    def get_transcription_config(self) -> Dict[str, Any]:
        """Get current transcription configuration."""
        return self.config.to_dict()


# Global service instance
_transcription_service = None


def get_transcription_service(config: Optional[TranscriptionConfig] = None) -> TranscriptionService:
    """Get global transcription service instance."""
    global _transcription_service
    
    if _transcription_service is None:
        _transcription_service = TranscriptionService(config)
    
    return _transcription_service


# Import asyncio at the end to avoid circular imports
import asyncio
