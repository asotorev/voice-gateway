"""
Utility modules for Lambda audio processing.

This package contains helper modules and utilities used by the Lambda function
for processing audio files and managing S3 events.

Modules:
- event_parser: S3 event parsing and validation utilities
"""

from .event_parser import S3EventParser

__all__ = ['S3EventParser']
