"""
AWS services integration modules for Lambda audio processing.

This package contains modules for interacting with AWS services
like S3 and DynamoDB in the Lambda processing pipeline.

Modules:
- s3_operations: S3 audio file operations
- dynamodb_operations: DynamoDB user record operations
"""

from .s3_operations import s3_operations
from .dynamodb_operations import dynamodb_operations

__all__ = ['s3_operations', 'dynamodb_operations']
