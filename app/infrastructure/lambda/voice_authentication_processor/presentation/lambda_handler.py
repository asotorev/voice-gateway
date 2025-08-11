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

# Add shared layer to Python path for Lambda execution
if '/opt/python' not in sys.path:
    sys.path.append('/opt/python')
if '/var/task' not in sys.path:
    sys.path.append('/var/task')

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
    
    Supports two invocation types:
    1. S3 Event-driven: Traditional S3 ObjectCreated events
    2. Stream invocation: Direct audio processing without S3 storage
    
    Args:
        event: AWS Lambda event (S3 ObjectCreated or direct invocation)
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
        # Detect invocation type
        if event.get('invocation_type') == 'stream':
            # Direct stream invocation
            logger.info("Processing stream voice authentication invocation")
            return await handle_stream_invocation(event, context)
        
        # Default: S3 event-driven processing
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


async def handle_stream_invocation(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle direct stream invocation for voice authentication.
    
    Processes audio data directly from the event payload without S3 storage.
    
    Args:
        event: Direct invocation event with audio data
        context: AWS Lambda context
        
    Returns:
        Dict with authentication results
    """
    import base64
    
    logger.info("Starting stream voice authentication", extra={
        "request_id": context.aws_request_id,
        "user_id": event.get('user_id'),
        "has_audio_data": 'audio_data' in event
    })
    
    try:
        # Extract and validate required fields
        user_id = event.get('user_id')
        if not user_id:
            raise ValueError("user_id is required for stream authentication")
        
        audio_data_b64 = event.get('audio_data')
        if not audio_data_b64:
            raise ValueError("audio_data is required for stream authentication")
        
        # Decode audio data
        try:
            audio_data = base64.b64decode(audio_data_b64)
        except Exception as e:
            raise ValueError(f"Invalid base64 audio data: {str(e)}")
        
        # Extract metadata
        metadata = event.get('metadata', {})
        metadata.update({
            'invocation_type': 'stream',
            'request_id': context.aws_request_id,
            'function_name': context.function_name
        })
        
        logger.info("Stream authentication data validated", extra={
            "user_id": user_id,
            "audio_size_bytes": len(audio_data),
            "metadata_keys": list(metadata.keys())
        })
        
        # Initialize orchestrator and process
        orchestrator = AuthOrchestrator()
        auth_result = await orchestrator.stream_process_authentication_audio(
            user_id=user_id,
            audio_data=audio_data,
            metadata=metadata
        )
        
        # Format response for direct invocation
        response = {
            "statusCode": 200,
            "authentication_successful": auth_result.get("authentication_successful", False),
            "confidence_score": auth_result.get("confidence_score", 0.0),
            "authentication_result": auth_result.get("authentication_result", "failed"),
            "user_id": user_id,
            "processing_time_ms": auth_result.get("processing_time_ms", 0),
            "dual_validation": auth_result.get("dual_validation", {}),
            "request_id": context.aws_request_id,
            "processed_at": auth_result.get("completed_at")
        }
        
        logger.info("Stream voice authentication completed", extra={
            "user_id": user_id,
            "authentication_successful": response["authentication_successful"],
            "confidence_score": response["confidence_score"],
            "processing_time_ms": response["processing_time_ms"]
        })
        
        return response
        
    except ValueError as e:
        logger.error("Stream authentication validation error", extra={
            "error": str(e),
            "user_id": event.get('user_id'),
            "request_id": context.aws_request_id
        })
        
        return {
            "statusCode": 400,
            "authentication_successful": False,
            "error_type": "validation_error",
            "error_message": str(e),
            "request_id": context.aws_request_id
        }
        
    except Exception as e:
        logger.error("Stream authentication processing error", extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "user_id": event.get('user_id'),
            "request_id": context.aws_request_id
        })
        
        return {
            "statusCode": 500,
            "authentication_successful": False,
            "error_type": "processing_error",
            "error_message": str(e),
            "request_id": context.aws_request_id
        }
