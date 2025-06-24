"""
Application settings with DynamoDB configuration.
Focused on local development setup for now.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings with validation and type safety.
    """
    
    # Environment
    environment: str = "development"
    
    # DynamoDB Configuration for local development
    aws_region: str = "us-east-1"
    dynamodb_endpoint_url: Optional[str] = "http://localhost:8000"  # Local DynamoDB
    users_table_name: str = "voice-gateway-users-local"
    
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


# Global settings instance
settings = Settings() 