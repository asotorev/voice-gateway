"""
AWS service configuration and client management.
Handles connection to DynamoDB with environment-specific settings.
"""
import boto3
from botocore.config import Config
from typing import Optional, Dict, Any
from .infrastructure_settings import infra_settings


class AWSConfig:
    """
    Manages AWS service connections and configuration.
    Centralized configuration for DynamoDB.
    """
    
    def __init__(self):
        self._dynamodb_resource: Optional[boto3.resource] = None
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
    def dynamodb_client(self) -> boto3.client:
        """Get or create DynamoDB client with proper configuration."""
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
        """Create DynamoDB client with environment-specific configuration."""
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
    
    def health_check(self) -> dict:
        """
        Perform health check on AWS services.
        
        Returns:
            Dictionary with health check results
        """
        results = {}
        
        try:
            # Test DynamoDB connectivity
            dynamodb = self.dynamodb_resource
            
            if infra_settings.use_local_dynamodb:
                # For local, try to list tables
                list(dynamodb.tables.all())
                results["dynamodb"] = {
                    "status": "healthy", 
                    "type": "local",
                    "endpoint": infra_settings.dynamodb_endpoint_url
                }
            else:
                # For AWS, test with a simple operation
                list(dynamodb.tables.limit(1))
                results["dynamodb"] = {
                    "status": "healthy", 
                    "type": "aws",
                    "region": infra_settings.aws_region
                }
                
        except Exception as e:
            results["dynamodb"] = {
                "status": "unhealthy", 
                "error": str(e),
                "type": "local" if infra_settings.use_local_dynamodb else "aws"
            }
        
        return results


# Global AWS configuration instance
aws_config = AWSConfig() 