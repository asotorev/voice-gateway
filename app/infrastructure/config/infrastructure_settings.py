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
    
    # Audio Storage Configuration
    audio_base_url: str
    audio_upload_expiration_minutes: int = 15
    audio_download_expiration_minutes: int = 60
    
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

# Global infrastructure settings instance
infra_settings = InfrastructureSettings() 