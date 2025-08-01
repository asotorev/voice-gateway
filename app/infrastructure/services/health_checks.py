"""
Health checks service for infrastructure components.
Coordinates health checks from DynamoDB setup service.
"""
from typing import Dict, Any
from app.infrastructure.config.infrastructure_settings import infra_settings
from app.infrastructure.config.aws_config import aws_config
from app.infrastructure.databases.dynamodb_setup import DynamoDBSetup


class HealthCheckService:
    """
    Service for performing comprehensive health checks on infrastructure components.
    """
    
    def __init__(self):
        self.dynamodb_setup = DynamoDBSetup()
    
    def check_all_services(self) -> Dict[str, Any]:
        """
        Perform comprehensive health checks on all infrastructure services.
        
        Returns:
            Dictionary with detailed health check results for all services
        """
        results = {}
        
        results["dynamodb"] = self._check_dynamodb()
        return results
    
    def _check_dynamodb(self) -> Dict[str, Any]:
        """
        Check DynamoDB connectivity and health using DynamoDBSetup.
        
        Returns:
            Dictionary with comprehensive DynamoDB health status
        """
        try:
            # Use DynamoDBSetup for comprehensive health checks
            dynamodb_health = self.dynamodb_setup.health_check()

            return {
                "status": "healthy" if dynamodb_health.get("dynamodb_connection", False) else "unhealthy",
                "type": "local" if infra_settings.use_local_dynamodb else "aws",
                "endpoint": infra_settings.dynamodb_endpoint_url or "AWS Default",
                "details": dynamodb_health
            }
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e),
                "type": "local" if infra_settings.use_local_dynamodb else "aws",
                "endpoint": infra_settings.dynamodb_endpoint_url or "AWS Default"
            }
    
    def check_basic_connectivity(self) -> Dict[str, Any]:
        """
        Check basic connectivity for quick health assessment.
        
        Returns:
            Dictionary with basic connectivity status
        """
        results = {}
        
        # Basic DynamoDB connectivity
        try:
            aws_config.dynamodb_client.list_tables(Limit=1)
            results["dynamodb"] = {
                "status": "healthy",
                "type": "local" if infra_settings.use_local_dynamodb else "aws",
                "note": "Basic connectivity only"
            }
        except Exception as e:
            results["dynamodb"] = {
                "status": "unhealthy",
                "error": str(e),
                "type": "local" if infra_settings.use_local_dynamodb else "aws"
            }
        
        return results


# Global health check service instance
health_check_service = HealthCheckService()