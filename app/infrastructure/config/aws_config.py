"""
AWS service configuration and client management.
Handles connection to DynamoDB and S3 with environment-specific settings.
"""
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any, List
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
                'max_attempts': infra_settings.aws_max_retry_attempts,
                'mode': 'adaptive'
            },
            max_pool_connections=infra_settings.aws_max_pool_connections
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
                'max_attempts': infra_settings.aws_max_retry_attempts,
                'mode': 'adaptive'
            },
            max_pool_connections=infra_settings.aws_max_pool_connections,
            signature_version=infra_settings.s3_signature_version
        )
        kwargs = {
            'service_name': 's3',
            'config': s3_config
        }
        if infra_settings.use_local_s3:
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
    
    def get_full_audio_url(self, audio_path: str) -> str:
        """
        Convert relative audio path to full URL.
        
        Args:
            audio_path: Relative path like 'user123/sample1.wav'
            
        Returns:
            Full URL like 's3://voice-gateway-audio/user123/sample1.wav'
        """
        if not audio_path:
            raise ValueError("Audio path cannot be empty")
        
        base_url = infra_settings.audio_base_url
        if not base_url.endswith('/'):
            base_url += '/'
        
        path = audio_path.lstrip('/')
        return base_url + path
    
    def get_api_base_url(self) -> str:
        """
        Get API base URL for HTTP requests.
        
        Returns:
            Full API URL like 'http://localhost:8080' or 'https://api.example.com'
        """
        protocol = "https" if infra_settings.is_production else infra_settings.app_protocol
        port_suffix = f":{infra_settings.app_port}" if infra_settings.app_port not in [80, 443] else ""
        return f"{protocol}://{infra_settings.app_host}{port_suffix}"
    
    def get_s3_config(self) -> dict:
        """
        Get S3 configuration for boto3 client.
        
        Returns:
            Dict with S3 client configuration
        """
        config = {
            'region_name': infra_settings.aws_region,
            'signature_version': infra_settings.s3_signature_version,
            'use_ssl': infra_settings.s3_use_ssl
        }
        
        if infra_settings.use_local_s3:
            config.update({
                'endpoint_url': infra_settings.s3_endpoint_url,
                'aws_access_key_id': 'minioadmin',
                'aws_secret_access_key': 'minioadmin'
            })
        
        return config
    
    def get_supported_audio_formats(self) -> List[str]:
        """
        Get supported audio formats from configuration.
        
        Returns:
            List of supported audio format strings
        """
        return infra_settings.supported_audio_formats


# Global AWS configuration instance
aws_config = AWSConfig() 