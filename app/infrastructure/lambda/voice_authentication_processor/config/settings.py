"""
Settings and configuration for Voice Authentication Processor Lambda.

Centralizes all configuration parameters for the voice authentication
processing Lambda function.
"""
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class VoiceAuthSettings:
    """Voice authentication processor settings."""
    
    # AWS Configuration
    aws_region: str = os.getenv('AWS_REGION', 'us-east-1')
    stage: str = os.getenv('STAGE', 'dev')
    
    # Storage Configuration
    s3_bucket_name: str = os.getenv('S3_BUCKET_NAME', '')
    s3_auth_prefix: str = os.getenv('S3_AUTH_PREFIX', 'voice-auth/')
    
    # Database Configuration
    users_table_name: str = os.getenv('USERS_TABLE_NAME', '')
    
    # Lambda Configuration
    lambda_timeout: int = int(os.getenv('LAMBDA_TIMEOUT', '300'))
    lambda_memory_size: int = int(os.getenv('LAMBDA_MEMORY_SIZE', '2048'))
    max_concurrent_executions: int = int(os.getenv('LAMBDA_CONCURRENT_EXECUTIONS', '5'))
    
    # Audio Processing Configuration
    max_audio_file_size_mb: int = int(os.getenv('MAX_AUDIO_FILE_SIZE_MB', '10'))
    processing_timeout_seconds: int = int(os.getenv('PROCESSING_TIMEOUT_SECONDS', '180'))
    
    # Authentication Configuration
    voice_auth_threshold: float = float(os.getenv('VOICE_AUTH_THRESHOLD', '0.80'))
    voice_auth_min_similarity: float = float(os.getenv('VOICE_AUTH_MIN_SIMILARITY', '0.75'))
    voice_auth_high_confidence: float = float(os.getenv('VOICE_AUTH_HIGH_CONFIDENCE', '0.85'))
    
    # Whisper Configuration
    whisper_model_size: str = os.getenv('WHISPER_MODEL_SIZE', 'base')
    whisper_language: str = os.getenv('WHISPER_LANGUAGE', 'es')
    transcription_confidence_threshold: float = float(os.getenv('TRANSCRIPTION_CONFIDENCE_THRESHOLD', '0.7'))
    
    # Password Validation Configuration
    expected_word_count: int = int(os.getenv('EXPECTED_WORD_COUNT', '3'))
    word_separator: str = os.getenv('WORD_SEPARATOR', '-')
    min_word_length: int = int(os.getenv('MIN_WORD_LENGTH', '3'))
    
    # Logging Configuration
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Security Configuration
    max_retries: int = int(os.getenv('LAMBDA_MAX_RETRIES', '3'))
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.s3_bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable is required")
        
        if not self.users_table_name:
            raise ValueError("USERS_TABLE_NAME environment variable is required")
        
        if not (0.0 <= self.voice_auth_threshold <= 1.0):
            raise ValueError("VOICE_AUTH_THRESHOLD must be between 0.0 and 1.0")
        
        if not (0.0 <= self.transcription_confidence_threshold <= 1.0):
            raise ValueError("TRANSCRIPTION_CONFIDENCE_THRESHOLD must be between 0.0 and 1.0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            'aws_region': self.aws_region,
            'stage': self.stage,
            's3_bucket_name': self.s3_bucket_name,
            's3_auth_prefix': self.s3_auth_prefix,
            'users_table_name': self.users_table_name,
            'lambda_timeout': self.lambda_timeout,
            'lambda_memory_size': self.lambda_memory_size,
            'max_concurrent_executions': self.max_concurrent_executions,
            'max_audio_file_size_mb': self.max_audio_file_size_mb,
            'processing_timeout_seconds': self.processing_timeout_seconds,
            'voice_auth_threshold': self.voice_auth_threshold,
            'voice_auth_min_similarity': self.voice_auth_min_similarity,
            'voice_auth_high_confidence': self.voice_auth_high_confidence,
            'whisper_model_size': self.whisper_model_size,
            'whisper_language': self.whisper_language,
            'transcription_confidence_threshold': self.transcription_confidence_threshold,
            'expected_word_count': self.expected_word_count,
            'word_separator': self.word_separator,
            'min_word_length': self.min_word_length,
            'log_level': self.log_level,
            'max_retries': self.max_retries
        }


# Global settings instance
settings = VoiceAuthSettings()


def get_settings() -> VoiceAuthSettings:
    """Get voice authentication processor settings."""
    return settings


def get_environment_info() -> Dict[str, Any]:
    """Get environment information for debugging."""
    return {
        'stage': settings.stage,
        'aws_region': settings.aws_region,
        'lambda_memory_size': settings.lambda_memory_size,
        'lambda_timeout': settings.lambda_timeout,
        'voice_auth_threshold': settings.voice_auth_threshold,
        'whisper_model_size': settings.whisper_model_size,
        'expected_word_count': settings.expected_word_count
    }
