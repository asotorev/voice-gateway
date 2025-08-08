"""
Lambda handler for processing audio files from S3 events.

This module serves as the entry point for the Lambda function that processes
voice audio samples. It handles S3 ObjectCreated events, validates the files,
and orchestrates the audio processing pipeline.

Event Flow:
1. S3 uploads trigger Lambda with ObjectCreated event
2. Handler validates and parses the S3 event
3. Downloads audio file from S3 
4. Processes audio to generate embedding
5. Updates user record in DynamoDB
6. Checks registration completion status
"""
import json
import logging
import os
import sys
from typing import Dict, Any, List

# Add project root to Python path for Lambda execution
if '/opt/python' not in sys.path:
    sys.path.append('/opt/python')
if '/var/task' not in sys.path:
    sys.path.append('/var/task')

# Import Lambda-specific modules
from utils.event_parser import S3EventParser
from pipeline_orchestrator import AudioProcessingPipeline

# Import project configuration (will be available in Lambda environment)
try:
    from app.infrastructure.config.infrastructure_settings import infra_settings
except ImportError:
    # Fallback for Lambda environment - use environment variables directly
    class MockSettings:
        lambda_log_level = os.getenv('LOG_LEVEL', 'INFO')
        s3_trigger_prefix = os.getenv('S3_TRIGGER_PREFIX', 'audio-uploads/')
    infra_settings = MockSettings()

import logging
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
        
        # Process each S3 event (typically one per Lambda invocation)
        processed_files = []
        failed_files = []
        
        for s3_event in s3_events:
            try:
                result = process_single_audio_file(s3_event)
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


def process_single_audio_file(s3_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single audio file from S3 event.
    
    Args:
        s3_event: Parsed S3 event with bucket, key, size info
        
    Returns:
        Dict with processing results
    """
    bucket = s3_event['bucket']
    key = s3_event['key']
    
    logger.info("Starting audio file processing", extra={
        "bucket": bucket,
        "key": key,
        "size_bytes": s3_event['size']
    })
    
    try:
        # Extract user_id from S3 key
        user_id = extract_user_id_from_key(key)
        
        # Initialize audio processing pipeline
        pipeline = AudioProcessingPipeline()
        
        # Run complete audio processing pipeline
        s3_event_data = {
            'bucket': bucket,
            'key': key,
            'size': s3_event['size'],
            'user_id': user_id
        }
        result = pipeline.process_s3_event(s3_event_data)
        
        logger.info("Audio processing pipeline completed", extra={
            "bucket": bucket,
            "key": key,
            "user_id": user_id,
            "success": result.get('success', False),
            "registration_complete": result.get('completion_stage', {}).get('is_complete', False)
        })
        
        # Return comprehensive result
        return {
            'bucket': bucket,
            'key': key,
            'user_id': user_id,
            'success': result.get('success', False),
            'embedding_generated': result.get('embedding_stage', {}).get('status') == 'success',
            'registration_complete': result.get('completion_stage', {}).get('is_complete', False),
            'processing_time_ms': result.get('processing_time_ms', 0),
            'pipeline_stages': result.get('processing_stages', {}),
            'completion_response': result.get('completion_response'),
            'progress_response': result.get('progress_response'),
            'error_details': result.get('error_details')
        }
        
    except Exception as e:
        logger.error("Audio processing pipeline failed", extra={
            "bucket": bucket,
            "key": key,
            "error": str(e)
        })
        
        return {
            'bucket': bucket,
            'key': key,
            'user_id': None,
            'success': False,
            'embedding_generated': False,
            'registration_complete': False,
            'processing_time_ms': 0,
            'error': str(e)
        }


def extract_user_id_from_key(s3_key: str) -> str:
    """
    Extract user ID from S3 object key.
    
    Expected format: audio-uploads/{user_id}/sample_{n}.wav
    
    Args:
        s3_key: S3 object key
        
    Returns:
        User ID string
        
    Raises:
        ValueError: If key format is invalid
    """
    try:
        # Remove prefix and get user_id part
        if not s3_key.startswith(infra_settings.s3_trigger_prefix):
            raise ValueError(f"Key does not start with expected prefix: {infra_settings.s3_trigger_prefix}")
        
        # Extract path after prefix: audio-uploads/{user_id}/filename.wav
        path_after_prefix = s3_key[len(infra_settings.s3_trigger_prefix):]
        user_id = path_after_prefix.split('/')[0]
        
        if not user_id:
            raise ValueError("Could not extract user_id from key")
        
        return user_id
        
    except Exception as e:
        logger.error("Failed to extract user_id from S3 key", extra={
            "s3_key": s3_key,
            "error": str(e)
        })
        raise ValueError(f"Invalid S3 key format: {s3_key}")
