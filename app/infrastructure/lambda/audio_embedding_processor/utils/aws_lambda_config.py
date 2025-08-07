"""
AWS Lambda configuration wrapper for audio processing.

This module provides a centralized AWS services configuration with proper setup
for Lambda execution environment. Handles connection management, retries,
and error handling for S3 and DynamoDB services specifically for Lambda functions.
"""
import os
import logging
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AWSLambdaConfigManager:
    """
    Centralized AWS client management for Lambda function.
    
    Provides configured S3 and DynamoDB clients with proper error handling,
    retries, and Lambda-optimized settings.
    """
    
    def __init__(self):
        """Initialize AWS client manager with Lambda environment configuration."""
        self._s3_client: Optional[boto3.client] = None
        self._dynamodb_client: Optional[boto3.client] = None
        self._dynamodb_resource: Optional[boto3.resource] = None
        
        # Lambda environment configuration
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.max_retries = int(os.getenv('LAMBDA_MAX_RETRIES', '3'))
        
        # Create boto3 config optimized for Lambda
        self._boto_config = Config(
            region_name=self.region,
            retries={
                'max_attempts': self.max_retries,
                'mode': 'adaptive'
            },
            max_pool_connections=50,
            connect_timeout=60,
            read_timeout=60
        )
        
        logger.info("AWS client manager initialized", extra={
            "region": self.region,
            "max_retries": self.max_retries
        })
    
    @property
    def s3_client(self) -> boto3.client:
        """
        Get or create S3 client with proper configuration.
        
        Returns:
            Configured S3 client
            
        Raises:
            NoCredentialsError: If AWS credentials are not available
        """
        if self._s3_client is None:
            try:
                self._s3_client = boto3.client('s3', config=self._boto_config)
                logger.debug("S3 client created successfully")
            except NoCredentialsError:
                logger.error("AWS credentials not found for S3 client")
                raise
            except Exception as e:
                logger.error("Failed to create S3 client", extra={"error": str(e)})
                raise
        
        return self._s3_client
    
    @property
    def dynamodb_client(self) -> boto3.client:
        """
        Get or create DynamoDB client with proper configuration.
        
        Returns:
            Configured DynamoDB client
            
        Raises:
            NoCredentialsError: If AWS credentials are not available
        """
        if self._dynamodb_client is None:
            try:
                self._dynamodb_client = boto3.client('dynamodb', config=self._boto_config)
                logger.debug("DynamoDB client created successfully")
            except NoCredentialsError:
                logger.error("AWS credentials not found for DynamoDB client")
                raise
            except Exception as e:
                logger.error("Failed to create DynamoDB client", extra={"error": str(e)})
                raise
        
        return self._dynamodb_client
    
    @property
    def dynamodb_resource(self) -> boto3.resource:
        """
        Get or create DynamoDB resource with proper configuration.
        
        Returns:
            Configured DynamoDB resource
            
        Raises:
            NoCredentialsError: If AWS credentials are not available
        """
        if self._dynamodb_resource is None:
            try:
                self._dynamodb_resource = boto3.resource('dynamodb', config=self._boto_config)
                logger.debug("DynamoDB resource created successfully")
            except NoCredentialsError:
                logger.error("AWS credentials not found for DynamoDB resource")
                raise
            except Exception as e:
                logger.error("Failed to create DynamoDB resource", extra={"error": str(e)})
                raise
        
        return self._dynamodb_resource
    
    def test_connections(self) -> Dict[str, bool]:
        """
        Test AWS service connections.
        
        Returns:
            Dict with connection test results for each service
        """
        results = {
            's3': False,
            'dynamodb': False
        }
        
        # Test S3 connection
        try:
            self.s3_client.list_buckets()
            results['s3'] = True
            logger.info("S3 connection test successful")
        except Exception as e:
            logger.warning("S3 connection test failed", extra={"error": str(e)})
        
        # Test DynamoDB connection
        try:
            self.dynamodb_client.list_tables()
            results['dynamodb'] = True
            logger.info("DynamoDB connection test successful")
        except Exception as e:
            logger.warning("DynamoDB connection test failed", extra={"error": str(e)})
        
        return results
    
    def get_s3_bucket_name(self) -> str:
        """
        Get S3 bucket name from environment variables.
        
        Returns:
            S3 bucket name
            
        Raises:
            ValueError: If bucket name is not configured
        """
        bucket_name = os.getenv('S3_BUCKET_NAME')
        if not bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable not set")
        return bucket_name
    
    def get_users_table_name(self) -> str:
        """
        Get DynamoDB users table name from environment variables.
        
        Returns:
            DynamoDB table name
            
        Raises:
            ValueError: If table name is not configured
        """
        table_name = os.getenv('USERS_TABLE_NAME')
        if not table_name:
            raise ValueError("USERS_TABLE_NAME environment variable not set")
        return table_name
    
    def handle_aws_error(self, error: Exception, operation: str, resource: str = "") -> None:
        """
        Handle and log AWS service errors.
        
        Args:
            error: The AWS error that occurred
            operation: Description of the operation that failed
            resource: Resource identifier (bucket, table, key, etc.)
        """
        if isinstance(error, ClientError):
            error_code = error.response['Error']['Code']
            error_message = error.response['Error']['Message']
            
            logger.error("AWS ClientError occurred", extra={
                "operation": operation,
                "resource": resource,
                "error_code": error_code,
                "error_message": error_message,
                "request_id": error.response.get('ResponseMetadata', {}).get('RequestId')
            })
            
            # Handle specific error codes
            if error_code == 'NoSuchBucket':
                logger.error("S3 bucket does not exist", extra={"bucket": resource})
            elif error_code == 'ResourceNotFoundException':
                logger.error("DynamoDB resource not found", extra={"table": resource})
            elif error_code == 'AccessDenied':
                logger.error("AWS access denied", extra={"operation": operation})
                
        elif isinstance(error, NoCredentialsError):
            logger.error("AWS credentials not available", extra={
                "operation": operation,
                "resource": resource
            })
        else:
            logger.error("Unexpected AWS error", extra={
                "operation": operation,
                "resource": resource,
                "error": str(error),
                "error_type": type(error).__name__
            })


# Global AWS Lambda config manager instance for Lambda function
aws_lambda_config_manager = AWSLambdaConfigManager()
