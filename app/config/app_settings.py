"""
Application-level settings for Voice Gateway.
Configuration that affects the application runtime and behavior.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Application-level configuration.
    Settings that control app behavior, networking, and runtime.
    """
    
    # Environment
    environment: str
    
    # Application Network
    app_host: str = "localhost"
    app_port: int = 8080
    app_protocol: str = "http"
    
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
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() in ("production", "prod")
    
    @property
    def app_url(self) -> str:
        """Get full application URL for testing and documentation."""
        if self.app_port in (80, 443):
            return f"{self.app_protocol}://{self.app_host}"
        return f"{self.app_protocol}://{self.app_host}:{self.app_port}"


# Global app settings instance
app_settings = AppSettings() 