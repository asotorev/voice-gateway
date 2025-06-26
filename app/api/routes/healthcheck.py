"""
Health check routes for Voice Gateway.
Provides application and infrastructure health status.
"""
from fastapi import APIRouter, HTTPException
from app.config.aws_config import aws_config
from app.config.settings import settings
from datetime import datetime


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
        # Check DynamoDB connectivity
        health_status = aws_config.health_check()
        
        response = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": settings.environment,
            "services": {
                "dynamodb": {
                    "status": health_status["dynamodb"]["status"],
                    "endpoint": settings.dynamodb_endpoint_url,
                    "type": health_status["dynamodb"]["type"]
                }
            }
        }
        
        # Check if any critical service is down
        if health_status["dynamodb"]["status"] != "healthy":
            raise HTTPException(
                status_code=503,
                detail="DynamoDB service unavailable"
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}"
        )