"""
AWS service configuration and client management.
Handles connection to DynamoDB and S3 with environment-specific settings.
"""
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any
from .infrastructure_settings import infra_settings


class AWSConfig:
    """
    Manages AWS service connections and configuration.
    Centralized configuration for DynamoDB and S3 services.
    """
    
    def __init__(self):
        self._dynamodb_resource: Optional[boto3.resource] = None
        self._s3_client: Optional[boto3.client] = None
        self._dynamodb_client: Optional[boto3.client] = None
        self._boto_config = Config(
            region_name=infra_settings.aws_region,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=50
        )
    
    @property
    def dynamodb_resource(self) -> boto3.resource:
        """Get or create DynamoDB resource with proper configuration."""
        if self._dynamodb_resource is None:
            self._dynamodb_resource = self._create_dynamodb_resource()
        return self._dynamodb_resource
    
    @property
    def s3_client(self) -> boto3.client:
        """
        Get or create S3 client with proper configuration.
        """
        if self._s3_client is None:
            self._s3_client = self._create_s3_client()
        return self._s3_client
    
    @property
    def dynamodb_client(self) -> boto3.client:
        """
        Get or create DynamoDB client with proper configuration.
        """
        if self._dynamodb_client is None:
            self._dynamodb_client = self._create_dynamodb_client()
        return self._dynamodb_client
    
    def _create_dynamodb_resource(self) -> boto3.resource:
        """Create DynamoDB resource with environment-specific configuration."""
        kwargs = {
            'service_name': 'dynamodb',
            'config': self._boto_config
        }
        
        if infra_settings.use_local_dynamodb:
            kwargs.update({
                'endpoint_url': infra_settings.dynamodb_endpoint_url,
                'region_name': infra_settings.aws_region,
                'aws_access_key_id': 'fakeMyKeyId',
                'aws_secret_access_key': 'fakeSecretAccessKey'
            })
        else:
            kwargs.update({
                'region_name': infra_settings.aws_region
            })
        
        return boto3.resource(**kwargs)
    
    def _create_dynamodb_client(self) -> boto3.client:

        """
        Create DynamoDB client with environment-specific configuration.
        """
        kwargs = {
            'service_name': 'dynamodb',
            'config': self._boto_config
        }
        if infra_settings.use_local_dynamodb:
            kwargs.update({
                'endpoint_url': infra_settings.dynamodb_endpoint_url,
                'region_name': infra_settings.aws_region,
                'aws_access_key_id': 'fakeMyKeyId',
                'aws_secret_access_key': 'fakeSecretAccessKey'
            })
        else:
            kwargs.update({
                'region_name': infra_settings.aws_region
            })
        return boto3.client(**kwargs)
    
    def _create_s3_client(self) -> boto3.client:
        """
        Create S3 client with environment-specific configuration.
        """
        # S3-specific configuration
        s3_config = Config(
            region_name=infra_settings.aws_region,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=50,
            signature_version=infra_settings.s3_signature_version
        )
        kwargs = {
            'service_name': 's3',
            'config': s3_config
        }
        if infra_settings.use_local_s3:
            # MinIO configuration
            kwargs.update({
                'endpoint_url': infra_settings.s3_endpoint_url,
                'region_name': infra_settings.aws_region,
                'aws_access_key_id': 'minioadmin',
                'aws_secret_access_key': 'minioadmin',
                'use_ssl': infra_settings.s3_use_ssl
            })
        else:
            # AWS S3 configuration
            kwargs.update({
                'region_name': infra_settings.aws_region
            })
        return boto3.client(**kwargs)
    
    def get_table(self, table_name: str):
        """
        Get DynamoDB table with error handling.
        
        Args:
            table_name: Name of the DynamoDB table
            
        Returns:
            DynamoDB table resource
            
        Raises:
            ConnectionError: If table connection fails
        """
        try:
            table = self.dynamodb_resource.Table(table_name)
            return table
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to DynamoDB table '{table_name}': {str(e)}"
            )
    


# Global AWS configuration instance
aws_config = AWSConfig() 