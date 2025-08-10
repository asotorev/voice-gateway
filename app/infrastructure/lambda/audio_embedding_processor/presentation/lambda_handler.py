"""
Lambda handler for processing audio files from S3 events.

This module serves as the entry point for the Lambda function following
Clean Architecture principles with dependency injection.
"""
import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any

# Add shared layer to Python path for Lambda execution
if '/opt/python' not in sys.path:
    sys.path.append('/opt/python')
if '/var/task' not in sys.path:
    sys.path.append('/var/task')

# Import from shared layer
from shared.adapters.event_parsers.s3_event_parser import S3EventParser
from application.registration_orchestrator import RegistrationOrchestrator

# Import project configuration (will be available in Lambda environment)
try:
    from app.infrastructure.config.infrastructure_settings import infra_settings
except ImportError:
    # Fallback for Lambda environment - use environment variables directly
    class MockSettings:
        lambda_log_level = os.getenv('LOG_LEVEL', 'INFO')
        s3_trigger_prefix = os.getenv('S3_TRIGGER_PREFIX', 'audio-uploads/')
    infra_settings = MockSettings()

logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, infra_settings.lambda_log_level))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point for processing S3 audio upload events.
    
    Args:
        event: AWS Lambda event containing S3 notifications
        context: AWS Lambda context object
        
    Returns:
        Dict with processing results and status
    """
    logger.info("Lambda function started", extra={
        "function_name": context.function_name if context else "unknown",
        "request_id": context.aws_request_id if context else "unknown"
    })
    
    try:
        # Parse and validate S3 events
        parser = S3EventParser()
        s3_events = parser.parse_event(event)
        
        if not s3_events:
            logger.warning("No valid S3 events found in Lambda trigger")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No valid S3 events to process',
                    'processed_files': 0
                })
            }
        
        # Initialize orchestrator
        orchestrator = RegistrationOrchestrator()
        
        # Process each S3 event
        processed_files = []
        failed_files = []
        
        for s3_event in s3_events:
            try:
                # Note: We'll run async operation in sync context for Lambda compatibility
                result = asyncio.run(orchestrator.process_registration_audio(s3_event))
                processed_files.append(result)
                logger.info("Successfully processed audio file", extra={
                    "bucket": s3_event['bucket'],
                    "key": s3_event['key'],
                    "size": s3_event['size']
                })
                
            except Exception as file_error:
                logger.error("Failed to process audio file", extra={
                    "bucket": s3_event['bucket'], 
                    "key": s3_event['key'],
                    "error": str(file_error)
                })
                failed_files.append({
                    'key': s3_event['key'],
                    'error': str(file_error)
                })
        
        # Return processing summary
        return {
            'statusCode': 200 if not failed_files else 207,  # 207 = Multi-Status
            'body': json.dumps({
                'message': 'Audio processing completed',
                'processed_files': len(processed_files),
                'failed_files': len(failed_files),
                'results': processed_files,
                'errors': failed_files
            })
        }
        
    except Exception as e:
        logger.error("Lambda function failed", extra={
            "error": str(e),
            "event": json.dumps(event) if event else None
        })
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal server error during audio processing',
                'error': str(e)
            })
        }
