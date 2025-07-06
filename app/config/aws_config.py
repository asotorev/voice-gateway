"""
AWS service configuration and client management.
Handles connection to DynamoDB with environment-specific settings.
"""
import boto3
from typing import Optional
from botocore.config import Config
from botocore.exceptions import ClientError
from .settings import settings


class AWSConfig:
    """
    Manages AWS service connections and configuration.
    """
    
    def __init__(self):
        self._dynamodb_resource: Optional[boto3.resource] = None
        self._boto_config = Config(
            region_name=settings.aws_region,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=50
        )
    
    @property
    def dynamodb_resource(self) -> boto3.resource:
        """
        Get or create DynamoDB resource with proper configuration.
        """
        if self._dynamodb_resource is None:
            self._dynamodb_resource = self._create_dynamodb_resource()
        return self._dynamodb_resource
    
    def _create_dynamodb_resource(self) -> boto3.resource:
        """
        Create DynamoDB resource with environment-specific configuration.
        """
        kwargs = {
            'service_name': 'dynamodb',
            'config': self._boto_config
        }
        
        # Configure for local DynamoDB or AWS
        if settings.use_local_dynamodb:
            kwargs.update({
                'endpoint_url': settings.dynamodb_endpoint_url,
                'region_name': settings.aws_region,
                'aws_access_key_id': 'fakeMyKeyId',
                'aws_secret_access_key': 'fakeSecretAccessKey'
            })
        else:
            # Production AWS configuration
            # boto3 will use IAM roles, environment variables, or AWS config
            kwargs.update({
                'region_name': settings.aws_region
            })
        
        return boto3.resource(**kwargs)
    
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
            
            if settings.use_local_dynamodb:
                # For local, try to list tables
                list(dynamodb.tables.all())
                results["dynamodb"] = {
                    "status": "healthy", 
                    "type": "local",
                    "endpoint": settings.dynamodb_endpoint_url
                }
            else:
                # For AWS, test with a simple operation
                list(dynamodb.tables.limit(1))
                results["dynamodb"] = {
                    "status": "healthy", 
                    "type": "aws",
                    "region": settings.aws_region
                }
                
        except Exception as e:
            results["dynamodb"] = {
                "status": "unhealthy", 
                "error": str(e),
                "type": "local" if settings.use_local_dynamodb else "aws"
            }
        
        return results

    @property
    def dynamodb_client(self):
        """
        Get or create DynamoDB client with proper configuration.
        """
        if not hasattr(self, '_dynamodb_client'):
            kwargs = {
                'service_name': 'dynamodb',
                'config': self._boto_config
            }
            if settings.use_local_dynamodb:
                kwargs.update({
                    'endpoint_url': settings.dynamodb_endpoint_url,
                    'region_name': settings.aws_region,
                    'aws_access_key_id': 'fakeMyKeyId',
                    'aws_secret_access_key': 'fakeSecretAccessKey'
                })
            else:
                kwargs.update({
                    'region_name': settings.aws_region
                })
            self._dynamodb_client = boto3.client(**kwargs)
        return self._dynamodb_client


# Global AWS configuration instance
aws_config = AWSConfig()