"""
Lambda presentation layer handler for voice authentication.

Handles S3 events for voice authentication processing, following Clean Architecture
principles with proper error handling, logging, and response formatting.
"""
import sys
import os
import json
import logging
from typing import Dict, Any, List

# Add shared layer to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared_layer', 'python'))

# Setup logging
from shared.infrastructure.aws.aws_config import configure_lambda_logging
configure_lambda_logging()
logger = logging.getLogger(__name__)

# Import shared layer components
from shared.adapters.event_parsers.s3_event_parser import S3EventParser
from application.auth_orchestrator import AuthOrchestrator


async def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for voice authentication processing.
    
    Args:
        event: AWS Lambda event (S3 ObjectCreated)
        context: AWS Lambda context
        
    Returns:
        Dict with processing results and HTTP status codes
    """
    logger.info("Voice authentication Lambda invoked", extra={
        "request_id": context.aws_request_id,
        "function_name": context.function_name,
        "function_version": context.function_version,
        "remaining_time_ms": context.get_remaining_time_in_millis()
    })
    
    # Initialize response structure
    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "X-Request-ID": context.aws_request_id
        },
        "body": {
            "message": "Voice authentication processing completed",
            "request_id": context.aws_request_id,
            "processed_files": [],
            "errors": [],
            "summary": {
                "total_files": 0,
                "successful": 0,
                "failed": 0
            }
        }
    }
    
    try:
        # Parse and validate S3 events
        logger.debug("Parsing S3 events from Lambda trigger")
        parser = S3EventParser()
        s3_events = parser.parse_lambda_event(event)
        
        if not s3_events:
            logger.warning("No valid S3 events found in Lambda trigger")
            response["statusCode"] = 400
            response["body"]["message"] = "No valid S3 events found"
            response["body"]["errors"] = ["Invalid or missing S3 events in trigger"]
            return response
        
        logger.info(f"Processing {len(s3_events)} S3 events for voice authentication")
        response["body"]["summary"]["total_files"] = len(s3_events)
        
        # Initialize authentication orchestrator
        orchestrator = AuthOrchestrator()
        
        # Process each S3 event
        for s3_event in s3_events:
            try:
                logger.info("Processing authentication request", extra={
                    "bucket": s3_event["bucket"],
                    "key": s3_event["key"],
                    "size": s3_event.get("size", 0)
                })
                
                # Process voice authentication
                auth_result = await orchestrator.process_authentication_audio(s3_event)
                
                # Add successful result
                response["body"]["processed_files"].append({
                    "file_key": s3_event["key"],
                    "bucket": s3_event["bucket"], 
                    "status": "success",
                    "user_id": auth_result.get("user_id"),
                    "authentication_successful": auth_result.get("authentication_successful", False),
                    "confidence_score": auth_result.get("confidence_score", 0.0),
                    "processing_time_ms": auth_result.get("processing_time_ms", 0),
                    "authentication_result": auth_result.get("authentication_result")
                })
                
                response["body"]["summary"]["successful"] += 1
                
                logger.info("Voice authentication completed successfully", extra={
                    "file_key": s3_event["key"],
                    "user_id": auth_result.get("user_id"),
                    "authentication_successful": auth_result.get("authentication_successful"),
                    "confidence_score": auth_result.get("confidence_score"),
                    "processing_time_ms": auth_result.get("processing_time_ms")
                })
                
            except Exception as file_error:
                error_details = {
                    "file_key": s3_event["key"],
                    "bucket": s3_event["bucket"],
                    "status": "failed", 
                    "error_type": type(file_error).__name__,
                    "error_message": str(file_error)
                }
                
                response["body"]["processed_files"].append(error_details)
                response["body"]["errors"].append(error_details)
                response["body"]["summary"]["failed"] += 1
                
                logger.error("Voice authentication failed for file", extra={
                    "file_key": s3_event["key"],
                    "bucket": s3_event["bucket"],
                    "error": str(file_error),
                    "error_type": type(file_error).__name__
                })
        
        # Determine final response status
        if response["body"]["summary"]["failed"] > 0:
            if response["body"]["summary"]["successful"] > 0:
                response["statusCode"] = 207  # Multi-Status (partial success)
                response["body"]["message"] = "Voice authentication completed with some failures"
            else:
                response["statusCode"] = 500  # All failed
                response["body"]["message"] = "Voice authentication failed for all files"
        
        logger.info("Voice authentication Lambda processing completed", extra={
            "total_files": response["body"]["summary"]["total_files"],
            "successful": response["body"]["summary"]["successful"],
            "failed": response["body"]["summary"]["failed"],
            "status_code": response["statusCode"]
        })
        
    except Exception as e:
        logger.error("Critical error in voice authentication Lambda", extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "request_id": context.aws_request_id
        })
        
        response["statusCode"] = 500
        response["body"]["message"] = "Critical voice authentication processing error"
        response["body"]["errors"] = [{
            "error_type": type(e).__name__,
            "error_message": str(e),
            "context": "Lambda handler level"
        }]
    
    # Convert body to JSON string for Lambda response
    response_copy = response.copy()
    response_copy["body"] = json.dumps(response["body"])
    
    return response_copy


def health_check_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Health check endpoint for voice authentication Lambda.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Health status response
    """
    try:
        # Basic health check
        health_status = {
            "status": "healthy",
            "service": "voice-authentication-processor",
            "version": "1.0.0",
            "timestamp": context.aws_request_id,
            "function_name": context.function_name,
            "remaining_time_ms": context.get_remaining_time_in_millis()
        }
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(health_status)
        }
        
    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e)})
        
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": "unhealthy",
                "error": str(e)
            })
        }
