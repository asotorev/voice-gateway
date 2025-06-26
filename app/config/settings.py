"""
Application settings with DynamoDB configuration and audio storage.
All configuration values sourced from environment files for maximum flexibility.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings with validation and type safety.
    All values configurable via environment variables.
    """
    
    # Environment
    environment: str
    
    # Application Network
    app_host: str = "localhost"
    app_port: int = 8080
    app_protocol: str = "http"
    
    # DynamoDB Configuration
    aws_region: str
    dynamodb_endpoint_url: Optional[str] = None
    users_table_name: str
    
    # Audio Storage Configuration
    audio_base_url: str
    
    # Configuration
    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env.development", ".env.staging", ".env.production"],
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
    
    @property
    def app_url(self) -> str:
        """Get full application URL for testing and documentation."""
        if self.app_port in (80, 443):
            return f"{self.app_protocol}://{self.app_host}"
        return f"{self.app_protocol}://{self.app_host}:{self.app_port}"
    
    def get_full_audio_url(self, audio_path: str) -> str:
        """
        Convert relative audio path to full URL.
        
        Args:
            audio_path: Relative path like 'user123/sample1.wav'
            
        Returns:
            Full URL like 's3://voice-gateway-audio/user123/sample1.wav'
        """
        base_url = self.audio_base_url
        if not base_url.endswith('/'):
            base_url += '/'
        path = audio_path.lstrip('/')
        return base_url + path


# Global settings instance
settings = Settings()