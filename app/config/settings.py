"""
Application settings with DynamoDB configuration and audio storage.
Focused on local development setup with storage provider independence.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings with validation and type safety.
    """
    
    # Environment
    environment: str
    
    # DynamoDB Configuration
    aws_region: str
    dynamodb_endpoint_url: Optional[str] = None
    users_table_name: str
    
    # Audio Storage Configuration
    audio_base_url: str
    
    # Configuration
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ("development", "dev", "local")
    
    @property
    def use_local_dynamodb(self) -> bool:
        """Check if should use local DynamoDB."""
        return self.dynamodb_endpoint_url is not None
    
    def get_full_audio_url(self, audio_path: str) -> str:
        """
        Convert relative audio path to full URL.
        
        This method eliminates coupling between database storage and 
        audio storage provider by combining configurable base URL 
        with relative paths stored in DynamoDB.
        
        Args:
            audio_path: Relative path like 'user123/sample1.wav'
            
        Returns:
            Full URL like 's3://voice-gateway-audio/user123/sample1.wav'
        """
        # Ensure base URL ends with slash
        base_url = self.audio_base_url
        if not base_url.endswith('/'):
            base_url += '/'
        
        # Ensure path doesn't start with slash
        path = audio_path.lstrip('/')
        
        return base_url + path


# Global settings instance
settings = Settings()