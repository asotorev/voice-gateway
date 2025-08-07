"""
Infrastructure settings for Voice Gateway.
Configuration for external services, databases, and storage systems.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class InfrastructureSettings(BaseSettings):
    """
    Infrastructure configuration.
    Settings for external services and infrastructure components.
    """
    
    # ENVIRONMENT & DEPLOYMENT
    environment: str = "development"
    stage: str = "dev"
    is_production: bool = False
    
    # AWS CORE CONFIGURATION
    aws_region: str
    
    # AWS Client Configuration
    aws_max_retry_attempts: int = 3
    aws_max_pool_connections: int = 50
    
    # DATABASE CONFIGURATION
    # DynamoDB
    dynamodb_endpoint_url: Optional[str] = None
    users_table_name: str
    
    # STORAGE CONFIGURATION
    # S3 Settings
    s3_bucket_name: str
    s3_endpoint_url: Optional[str] = None
    s3_use_ssl: bool = True
    s3_signature_version: str = "s3v4"
    
    # Audio Storage Settings
    audio_base_url: str
    audio_upload_expiration_minutes: int = 15
    audio_download_expiration_minutes: int = 60
    
    # AUDIO PROCESSING CONFIGURATION
    supported_audio_formats: list = ["wav", "mp3", "m4a", "flac"]
    max_audio_file_size_mb: int = 10
    required_audio_samples: int = 3
    processing_timeout_seconds: int = 180
    
    # VOICE EMBEDDING CONFIGURATION
    voice_embedding_dimensions: int = 256
    use_mock_embedding_service: bool = False
    
    # LAMBDA FUNCTION CONFIGURATION
    # Core Lambda Settings
    lambda_function_name: str = "audio-embedding-processor"
    lambda_timeout: int = 900  # 15 minutes default for ML processing
    lambda_memory_size: int = 3008  # MB - High memory for Resemblyzer
    lambda_runtime: str = "python3.9"
    lambda_max_retries: int = 3
    lambda_concurrent_executions: int = 10
    lambda_log_level: str = "INFO"
    
    # Lambda Layers
    lambda_layer_name: str = "resemblyzer-layer"
    lambda_layer_runtime: str = "python3.9"
    
    # SERVERLESS DEPLOYMENT CONFIGURATION
    serverless_service_name: str = "voice-gateway-lambda"
    serverless_provider_name: str = "aws"
    
    # AWS IAM CONFIGURATION
    lambda_execution_role_name: str = "VoiceGatewayLambdaExecutionRole"
    lambda_s3_access_role_name: str = "VoiceGatewayS3AccessRole"
    
    # S3 EVENT TRIGGERS CONFIGURATION
    s3_trigger_event: str = "s3:ObjectCreated:*"
    s3_trigger_prefix: str = "audio-uploads/"
    s3_trigger_suffix: str = ".wav"
    
    # MONITORING & LOGGING CONFIGURATION
    # Application Logging
    log_level: str = "INFO"
    log_format: str = "colored"
    service_name: str = "voice-gateway"
    
    # CloudWatch Configuration
    cloudwatch_log_group: str = "/aws/lambda/audio-embedding-processor"
    cloudwatch_log_retention_days: int = 14
    
    # Configuration
    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env.development", ".env.staging", ".env.production"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def use_local_dynamodb(self) -> bool:
        """Check if should use local DynamoDB."""
        return self.dynamodb_endpoint_url is not None
    
    @property
    def use_local_s3(self) -> bool:
        """Check if should use local S3 (MinIO)."""
        return self.s3_endpoint_url is not None
    
    @property
    def max_audio_file_size_bytes(self) -> int:
        """Convert MB to bytes for file size validation."""
        return self.max_audio_file_size_mb * 1024 * 1024
    
    @property
    def is_production_env(self) -> bool:
        """Check if running in production environment (computed from environment)."""
        return self.environment.lower() == "production"
    



# Global infrastructure settings instance
infra_settings = InfrastructureSettings()