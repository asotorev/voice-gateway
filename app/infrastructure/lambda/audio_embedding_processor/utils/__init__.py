"""
Utility modules for Lambda audio processing.

This package contains helper modules and utilities used by the Lambda function
for processing audio files, managing S3 events, and AWS configuration.

Modules:
- event_parser: S3 event parsing and validation utilities
- file_validator: Audio file validation and security checks
- aws_lambda_config: AWS client configuration for Lambda environment
- audio_processor: Audio processing and embedding generation utilities
"""

from .event_parser import S3EventParser
from .file_validator import audio_file_validator
from .aws_lambda_config import aws_lambda_config_manager
from .audio_processor import process_audio_file, get_audio_processor

__all__ = ['S3EventParser', 'audio_file_validator', 'aws_lambda_config_manager', 'process_audio_file', 'get_audio_processor']
