"""
Unified logging configuration for Voice Gateway.
Provides singleton pattern to ensure single configuration.
"""
import logging
import logging.config
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime
from app.infrastructure.config.infrastructure_settings import infra_settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "service": "voice-gateway",
            "environment": infra_settings.environment
        }
        
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable formatter for development."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        level_color = self.COLORS.get(record.levelname, '')
        reset_color = self.COLORS['RESET']
        colored_level = f"{level_color}{record.levelname}{reset_color}"
        
        base_format = f"%(asctime)s - %(name)s - {colored_level} - %(message)s"
        
        if hasattr(record, 'extra_fields'):
            extra_str = " | ".join([f"{k}={v}" for k, v in record.extra_fields.items()])
            base_format += f" | {extra_str}"
        
        formatter = logging.Formatter(base_format)
        return formatter.format(record)


class LoggingManager:
    """Singleton manager for logging configuration."""
    
    _instance: Optional['LoggingManager'] = None
    _configured: bool = False
    
    def __new__(cls) -> 'LoggingManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _configure_logging(self) -> None:
        """Unified logging configuration."""
        if self._configured:
            return
        
        # Determine log level
        log_level = getattr(logging, infra_settings.log_level.upper(), logging.INFO)
        
        # Choose formatter based on environment
        if infra_settings.environment == "production":
            formatter = JSONFormatter()
        else:
            formatter = DevelopmentFormatter()
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        
        # Configure app logger 
        app_logger = logging.getLogger("voice-gateway")
        app_logger.setLevel(log_level)
        app_logger.addHandler(console_handler)
        app_logger.propagate = False
        
        # Configure root logger only if it has no handlers
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            root_handler = logging.StreamHandler(sys.stdout)
            root_handler.setLevel(log_level)
            root_handler.setFormatter(formatter)
            root_logger.addHandler(root_handler)
            root_logger.setLevel(log_level)
        
        # Reduce third-party library noise
        self._configure_third_party_loggers()
        
        self._configured = True
        
        # Log successful configuration
        app_logger.info("Logging configuration initialized", extra={
            'extra_fields': {
                "environment": infra_settings.environment,
                "log_level": logging.getLevelName(log_level),
                "formatter": "json" if infra_settings.environment == "production" else "development",
                "app_logger_handlers": len(app_logger.handlers),
                "root_logger_handlers": len(root_logger.handlers)
            }
        })
    
    def _configure_third_party_loggers(self) -> None:
        """
        Configure third-party library loggers to reduce noise.        
        """
        third_party_loggers = ["boto3", "botocore", "urllib3", "requests"]
        
        for logger_name in third_party_loggers:
            logger = logging.getLogger(logger_name)
            if logger.level < logging.WARNING:
                logger.setLevel(logging.WARNING)
                
        # Log what we configured
        app_logger = logging.getLogger("voice-gateway")
        app_logger.debug("Third-party logger noise reduction applied", extra={
            'extra_fields': {
                "configured_loggers": third_party_loggers,
                "new_level": "WARNING"
            }
        })
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a configured logger instance under voice-gateway namespace."""
        self._configure_logging()
        
        # Ensure all our loggers are under voice-gateway namespace
        if not name.startswith("voice-gateway"):
            name = f"voice-gateway.{name}"
        
        return logging.getLogger(name)


# Singleton instance
logging_manager = LoggingManager()


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__ or component name)
        
    Returns:
        Configured logger instance under voice-gateway namespace
        
    Example:
        logger = get_logger("DatabaseSetup")
        # Results in logger named: "voice-gateway.DatabaseSetup"
    """
    return logging_manager.get_logger(name)