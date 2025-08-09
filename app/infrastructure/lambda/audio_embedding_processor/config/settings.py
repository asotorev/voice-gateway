"""
Configuration settings for audio embedding processor Lambda.

This module provides configuration management following Clean Architecture
principles with environment-based settings.
"""
import os


class LambdaSettings:
    """
    Configuration settings for the Lambda function.
    
    Centralizes environment variable access and provides
    sensible defaults for Lambda execution.
    """
    
    # Processing settings
    MAX_RETRIES = int(os.getenv('LAMBDA_MAX_RETRIES', '3'))
    PROCESSING_TIMEOUT_SECONDS = int(os.getenv('PROCESSING_TIMEOUT_SECONDS', '180'))
    
    # Audio processing settings
    REQUIRED_AUDIO_SAMPLES = int(os.getenv('REQUIRED_AUDIO_SAMPLES', '3'))
    MAX_AUDIO_FILE_SIZE_MB = int(os.getenv('MAX_AUDIO_FILE_SIZE_MB', '10'))
    SUPPORTED_AUDIO_FORMATS = os.getenv('SUPPORTED_AUDIO_FORMATS', 'wav,mp3,m4a,flac').split(',')
    
    # AWS settings
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', '')
    USERS_TABLE_NAME = os.getenv('USERS_TABLE_NAME', '')
    S3_TRIGGER_PREFIX = os.getenv('S3_TRIGGER_PREFIX', 'audio-uploads/')
    
    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Audio processor settings
    EMBEDDING_PROCESSOR_TYPE = os.getenv('EMBEDDING_PROCESSOR_TYPE', 'mock')
    VOICE_EMBEDDING_DIMENSIONS = int(os.getenv('VOICE_EMBEDDING_DIMENSIONS', '256'))
    
    @classmethod
    def get_max_audio_file_size_bytes(cls) -> int:
        """Get maximum audio file size in bytes."""
        return cls.MAX_AUDIO_FILE_SIZE_MB * 1024 * 1024
    
    @classmethod
    def validate_required_settings(cls) -> None:
        """
        Validate that all required settings are present.
        
        Raises:
            ValueError: If required settings are missing
        """
        required_settings = [
            ('S3_BUCKET_NAME', cls.S3_BUCKET_NAME),
            ('USERS_TABLE_NAME', cls.USERS_TABLE_NAME)
        ]
        
        missing_settings = [name for name, value in required_settings if not value]
        
        if missing_settings:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_settings)}")


# Global settings instance
lambda_settings = LambdaSettings()
