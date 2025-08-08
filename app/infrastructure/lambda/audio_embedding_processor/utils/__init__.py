"""
Utility modules for Lambda audio processing.

This package contains helper modules and utilities used by the Lambda function
for processing audio files, managing S3 events, AWS configuration, and user
registration tracking.

Modules:
- event_parser: S3 event parsing and validation utilities
- file_validator: Audio file validation and security checks
- aws_lambda_config: AWS client configuration for Lambda environment
- audio_processor: Audio processing and embedding generation utilities
- user_status_manager: User registration status tracking and analysis
- completion_checker: Registration completion detection and validation
- notification_handler: Event notifications and status broadcasting
"""

from .event_parser import S3EventParser
from .file_validator import audio_file_validator
from .aws_lambda_config import aws_lambda_config_manager
from .audio_processor import process_audio_file, get_audio_processor
from .user_status_manager import user_status_manager
from .completion_checker import completion_checker
from .notification_handler import notification_handler

__all__ = [
    'S3EventParser', 
    'audio_file_validator', 
    'aws_lambda_config_manager', 
    'process_audio_file', 
    'get_audio_processor',
    'user_status_manager',
    'completion_checker',
    'notification_handler'
]
