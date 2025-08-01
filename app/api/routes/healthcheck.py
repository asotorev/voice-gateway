"""
Health check routes for Voice Gateway.
Provides application and infrastructure health status.
"""
from fastapi import APIRouter, HTTPException
from app.config.app_settings import app_settings
from app.infrastructure.config.infrastructure_settings import infra_settings
from datetime import datetime, UTC
from app.infrastructure.services.health_checks import health_check_service


router = APIRouter()


@router.get("/ping", tags=["Health"])
async def ping():
    """
    Basic health check endpoint.
    
    Returns:
        dict: Simple pong response
    """
    return {"message": "pong"}


@router.get("/health", tags=["Health"])
async def health_check():
    """
    Comprehensive health check including DynamoDB connectivity.
    
    Returns:
        dict: Health status of application and dependencies
        
    Raises:
        HTTPException: 503 if critical services are unavailable
    """
    try:
        # Check all infrastructure services
        health_status = health_check_service.check_all_services()
        
        response = {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "environment": app_settings.environment,
            "services": health_status
        }
        
        # Check if any critical service is down
        critical_services = ["dynamodb", "s3"]
        unhealthy_services = [
            service for service in critical_services 
            if health_status.get(service, {}).get("status") != "healthy"
        ]
        
        if unhealthy_services:
            raise HTTPException(
                status_code=503,
                detail=f"Services unavailable: {', '.join(unhealthy_services)}"
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}"
        )