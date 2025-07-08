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
    
    # AWS Configuration
    aws_region: str
    
    # DynamoDB Configuration
    dynamodb_endpoint_url: Optional[str] = None
    users_table_name: str
    
    # S3 Configuration
    s3_bucket_name: str
    s3_endpoint_url: Optional[str] = None
    s3_use_ssl: bool = True
    s3_signature_version: str = "s3v4"
    
    # Audio Storage Configuration
    audio_base_url: str
    audio_upload_expiration_minutes: int = 15
    audio_download_expiration_minutes: int = 60
    
    # Logging configuration context
    log_level: str = "INFO"
    log_format: str = "colored"
    service_name: str = "voice-gateway"
    
    # Environment
    environment: str = "development"
    
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
    
    def get_full_audio_url(self, audio_path: str) -> str:
        """
        Convert relative audio path to full URL.
        
        Args:
            audio_path: Relative path like 'user123/sample1.wav'
            
        Returns:
            Full URL like 's3://voice-gateway-audio/user123/sample1.wav'
        """
        if not audio_path:
            raise ValueError("Audio path cannot be empty")
        
        base_url = self.audio_base_url
        if not base_url.endswith('/'):
            base_url += '/'
        
        path = audio_path.lstrip('/')
        return base_url + path
    
    def get_s3_config(self) -> dict:
        """
        Get S3 configuration for boto3 client.
        
        Returns:
            Dict with S3 client configuration
        """
        config = {
            'region_name': self.aws_region,
            'signature_version': self.s3_signature_version,
            'use_ssl': self.s3_use_ssl
        }
        
        if self.use_local_s3:
            config.update({
                'endpoint_url': self.s3_endpoint_url,
                'aws_access_key_id': 'minioadmin',  # Default MinIO credentials
                'aws_secret_access_key': 'minioadmin'
            })
        
        return config


# Global infrastructure settings instance
infra_settings = InfrastructureSettings()