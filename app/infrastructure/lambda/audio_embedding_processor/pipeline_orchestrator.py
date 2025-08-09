"""
Pipeline orchestrator for Lambda audio processing workflow.

This module coordinates the complete audio processing pipeline from S3 event
to DynamoDB update, managing the flow between different components and
handling errors, retries, and status tracking throughout the process.
"""
import os
import logging
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone

# Import pipeline components
from services.s3_operations import s3_operations
from services.dynamodb_operations import dynamodb_operations
from utils.audio_processor import process_audio_file, get_audio_processor
from utils.file_validator import audio_file_validator
from utils.user_status_manager import user_status_manager
from utils.completion_checker import completion_checker
from utils.notification_handler import notification_handler
from utils.aws_lambda_config import aws_lambda_config_manager as aws_client_manager

logger = logging.getLogger(__name__)


class AudioProcessingPipeline:
    """
    Orchestrates the complete audio processing workflow.
    
    Manages the flow from S3 event processing through embedding generation
    to DynamoDB updates, with comprehensive error handling and monitoring.
    """
    
    def __init__(self):
        """Initialize the audio processing pipeline."""
        self.max_retries = int(os.getenv('LAMBDA_MAX_RETRIES', '3'))
        self.processing_timeout = int(os.getenv('PROCESSING_TIMEOUT_SECONDS', '180'))
        
        logger.info("Audio processing pipeline initialized", extra={
            "max_retries": self.max_retries,
            "processing_timeout_seconds": self.processing_timeout
        })
    
    def process_s3_event(self, s3_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single S3 event through the complete pipeline.
        
        Args:
            s3_event: Parsed S3 event with bucket, key, size info
            
        Returns:
            Dict with complete processing results
            
        Raises:
            Exception: If processing fails after retries
        """
        start_time = time.time()
        bucket = s3_event['bucket']
        key = s3_event['key']
        
        logger.info("Starting S3 event processing", extra={
            "bucket": bucket,
            "key": key,
            "event_size": s3_event.get('size', 0)
        })
        
        processing_result = {
            'bucket': bucket,
            'key': key,
            'user_id': None,
            'success': False,
            'processing_stages': {},
            'error_details': None,
            'processing_time_ms': 0,
            'started_at': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Stage 1: Extract user ID and validate S3 key
            user_id = self._extract_user_id_stage(s3_event, processing_result)
            processing_result['user_id'] = user_id
            
            # Stage 2: Download and validate audio file
            audio_data, file_metadata = self._download_and_validate_stage(s3_event, processing_result)
            
            # Stage 3: Process audio and generate embedding
            embedding_result = self._generate_embedding_stage(audio_data, file_metadata, processing_result)
            
            # Stage 4: Update user record in DynamoDB
            user_update_result = self._update_user_record_stage(
                user_id, embedding_result, file_metadata, processing_result
            )
            
            # Stage 5: Check registration completion
            completion_result = self._check_completion_stage(user_id, processing_result)
            
            # Calculate processing time
            processing_result['processing_time_ms'] = int((time.time() - start_time) * 1000)
            processing_result['success'] = True
            processing_result['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Compile final result
            processing_result.update({
                'embedding_dimensions': len(embedding_result['embedding']),
                'quality_score': embedding_result['quality_assessment']['overall_quality_score'],
                'user_embedding_count': user_update_result['total_embeddings'],
                'registration_complete': completion_result['is_complete']
            })
            
            logger.info("S3 event processing completed successfully", extra={
                "user_id": user_id,
                "processing_time_ms": processing_result['processing_time_ms'],
                "embedding_count": user_update_result['total_embeddings'],
                "registration_complete": completion_result['is_complete']
            })
            
            return processing_result
            
        except Exception as e:
            processing_result['processing_time_ms'] = int((time.time() - start_time) * 1000)
            processing_result['error_details'] = {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'failed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.error("S3 event processing failed", extra={
                "bucket": bucket,
                "key": key,
                "user_id": processing_result.get('user_id'),
                "error": str(e),
                "processing_time_ms": processing_result['processing_time_ms']
            })
            
            raise
    
    def _extract_user_id_stage(self, s3_event: Dict[str, Any], result: Dict[str, Any]) -> str:
        """
        Stage 1: Extract user ID from S3 key.
        
        Args:
            s3_event: S3 event data
            result: Processing result to update
            
        Returns:
            User ID string
        """
        stage_name = "extract_user_id"
        logger.debug(f"Starting stage: {stage_name}")
        
        try:
            user_id = s3_operations.extract_user_id_from_key(s3_event['key'])
            
            result['processing_stages'][stage_name] = {
                'status': 'success',
                'user_id': user_id,
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug(f"Stage {stage_name} completed", extra={"user_id": user_id})
            return user_id
            
        except Exception as e:
            result['processing_stages'][stage_name] = {
                'status': 'failed',
                'error': str(e),
                'failed_at': datetime.now(timezone.utc).isoformat()
            }
            raise
    
    def _download_and_validate_stage(self, s3_event: Dict[str, Any], result: Dict[str, Any]) -> Tuple[bytes, Dict[str, Any]]:
        """
        Stage 2: Download audio file and perform validation.
        
        Args:
            s3_event: S3 event data
            result: Processing result to update
            
        Returns:
            Tuple of (audio_data, file_metadata)
        """
        stage_name = "download_and_validate"
        logger.debug(f"Starting stage: {stage_name}")
        
        try:
            # Download audio file
            audio_data = s3_operations.download_audio_file(s3_event['key'])
            
            # Get file metadata
            file_metadata = s3_operations.get_file_info_summary(s3_event['key'])
            
            # Validate file
            validation_result = audio_file_validator.validate_file(audio_data, file_metadata)
            
            if not validation_result['is_valid']:
                raise ValueError(f"File validation failed: {validation_result['validation_failed']}")
            
            result['processing_stages'][stage_name] = {
                'status': 'success',
                'file_size_bytes': len(audio_data),
                'validation_passed': len(validation_result['validation_passed']),
                'validation_warnings': len(validation_result['warnings']),
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug(f"Stage {stage_name} completed", extra={
                "file_size": len(audio_data),
                "validation_status": "passed"
            })
            
            return audio_data, file_metadata
            
        except Exception as e:
            result['processing_stages'][stage_name] = {
                'status': 'failed',
                'error': str(e),
                'failed_at': datetime.now(timezone.utc).isoformat()
            }
            raise
    
    def _generate_embedding_stage(self, audio_data: bytes, file_metadata: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 3: Generate voice embedding from audio data.
        
        Args:
            audio_data: Raw audio file bytes
            file_metadata: File metadata
            result: Processing result to update
            
        Returns:
            Embedding generation result
        """
        stage_name = "generate_embedding"
        logger.debug(f"Starting stage: {stage_name}")
        
        try:
            embedding_result = process_audio_file(audio_data, file_metadata)
            
            result['processing_stages'][stage_name] = {
                'status': 'success',
                'embedding_dimensions': len(embedding_result['embedding']),
                'quality_score': embedding_result['quality_assessment']['overall_quality_score'],
                'processor_type': embedding_result['processor_info']['processor_type'],
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug(f"Stage {stage_name} completed", extra={
                "embedding_dimensions": len(embedding_result['embedding']),
                "quality_score": embedding_result['quality_assessment']['overall_quality_score']
            })
            
            return embedding_result
            
        except Exception as e:
            result['processing_stages'][stage_name] = {
                'status': 'failed',
                'error': str(e),
                'failed_at': datetime.now(timezone.utc).isoformat()
            }
            raise
    
    def _update_user_record_stage(self, user_id: str, embedding_result: Dict[str, Any], 
                                 file_metadata: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 4: Update user record with new voice embedding.
        
        Args:
            user_id: User identifier
            embedding_result: Result from embedding generation
            file_metadata: File metadata
            result: Processing result to update
            
        Returns:
            User update result
        """
        stage_name = "update_user_record"
        logger.debug(f"Starting stage: {stage_name}")
        
        try:
            # Prepare audio metadata for storage
            audio_metadata = {
                'file_name': file_metadata.get('file_name', ''),
                'size_bytes': file_metadata.get('size_bytes', 0),
                'quality_score': embedding_result['quality_assessment']['overall_quality_score'],
                'processor_type': embedding_result['processor_info']['processor_type']
            }
            
            # Add embedding to user record
            user_update_result = dynamodb_operations.add_voice_embedding(
                user_id, 
                embedding_result['embedding'], 
                audio_metadata
            )
            
            result['processing_stages'][stage_name] = {
                'status': 'success',
                'total_embeddings': user_update_result['total_embeddings'],
                'registration_complete': user_update_result['registration_complete'],
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug(f"Stage {stage_name} completed", extra={
                "user_id": user_id,
                "total_embeddings": user_update_result['total_embeddings']
            })
            
            return user_update_result
            
        except Exception as e:
            result['processing_stages'][stage_name] = {
                'status': 'failed',
                'error': str(e),
                'failed_at': datetime.now(timezone.utc).isoformat()
            }
            raise
    
    def _check_completion_stage(self, user_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 5: Intelligent completion checking and status tracking.
        
        Args:
            user_id: User identifier
            result: Processing result to update
            
        Returns:
            Enhanced completion check result with notifications
        """
        stage_name = "check_completion"
        logger.debug(f"Starting stage: {stage_name}")
        
        try:
            # Get complete user data for analysis
            user_data = dynamodb_operations.get_user(user_id)
            if not user_data:
                raise ValueError(f"User {user_id} not found")
            
            # Perform comprehensive completion analysis
            completion_analysis = completion_checker.check_completion_status(user_data)
            
            # Get detailed progress analysis
            progress_analysis = user_status_manager.analyze_registration_progress(user_data)
            
            # Check if completion status should be updated
            should_update = completion_checker.should_trigger_completion_update(
                completion_analysis, user_data
            )
            
            # Update user record if completion status changed
            if should_update and completion_analysis['is_complete']:
                logger.info("Updating user registration to complete", extra={
                    "user_id": user_id,
                    "confidence": completion_analysis['completion_confidence']
                })
                
                dynamodb_operations.update_user_status(user_id, {
                    'registration_complete': True,
                    'registration_completed_at': datetime.now(timezone.utc).isoformat(),
                    'completion_confidence': completion_analysis['completion_confidence']
                })
                
                # Create completion response data
                completion_response = notification_handler.notify_registration_completed(user_id, {
                    'completion_confidence': completion_analysis['completion_confidence'],
                    'registration_score': completion_analysis['registration_score'],
                    'total_samples': progress_analysis['progress_metrics']['samples_collected']
                })
            
            # Create progress response for non-completed registrations
            if not completion_analysis['is_complete']:
                # Check if we should send quality warning
                if progress_analysis['quality_analysis']['average_quality'] < 0.7:
                    progress_response = notification_handler.notify_quality_warning(user_id, {
                        'quality_score': progress_analysis['quality_analysis']['average_quality'],
                        'samples_collected': progress_analysis['progress_metrics']['samples_collected'],
                        'quality_trend': progress_analysis['quality_analysis']['quality_trend']
                    })
                else:
                    # Create regular progress response
                    progress_response = notification_handler.notify_sample_recorded(user_id, {
                        'total_samples': progress_analysis['progress_metrics']['samples_collected'],
                        'required_samples': progress_analysis['progress_metrics']['required_samples'],
                        'completion_percentage': progress_analysis['progress_metrics']['completion_percentage'],
                        'samples_remaining': progress_analysis['progress_metrics']['samples_remaining']
                    })
            
            # Compile enhanced completion result
            enhanced_result = {
                'is_complete': completion_analysis['is_complete'],
                'completion_confidence': completion_analysis['completion_confidence'],
                'registration_score': completion_analysis['registration_score'],
                'embedding_count': progress_analysis['progress_metrics']['samples_collected'],
                'required_samples': progress_analysis['progress_metrics']['required_samples'],
                'samples_remaining': progress_analysis['progress_metrics']['samples_remaining'],
                'completion_percentage': progress_analysis['progress_metrics']['completion_percentage'],
                'status_analysis': progress_analysis['current_status'],
                'recommendations': completion_analysis['recommendations'],
                'quality_analysis': progress_analysis['quality_analysis'],
                'updated_record': should_update
            }
            
            # Add completion response if available
            if 'completion_response' in locals():
                enhanced_result['completion_response'] = completion_response
                
            # Add progress response if available  
            if 'progress_response' in locals():
                enhanced_result['progress_response'] = progress_response
            
            result['processing_stages'][stage_name] = {
                'status': 'success',
                'is_complete': enhanced_result['is_complete'],
                'completion_confidence': enhanced_result['completion_confidence'],
                'registration_score': enhanced_result['registration_score'],
                'embedding_count': enhanced_result['embedding_count'],
                'status_analysis': enhanced_result['status_analysis'],
                'updated_record': enhanced_result['updated_record'],
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug(f"Stage {stage_name} completed", extra={
                "user_id": user_id,
                "is_complete": enhanced_result['is_complete'],
                "confidence": enhanced_result['completion_confidence'],
                "score": enhanced_result['registration_score'],
                "embedding_count": enhanced_result['embedding_count']
            })
            
            return enhanced_result
            
        except Exception as e:
            result['processing_stages'][stage_name] = {
                'status': 'failed',
                'error': str(e),
                'failed_at': datetime.now(timezone.utc).isoformat()
            }
            raise
    
    def get_pipeline_health(self) -> Dict[str, Any]:
        """
        Get pipeline health status.
        
        Returns:
            Dict with pipeline health information
        """
        try:
            # Test AWS connections
            aws_health = aws_client_manager.test_connections()
            
            # Test processor
            processor = get_audio_processor()
            processor_info = processor.get_processor_info()
            
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'components': {
                    's3_connection': aws_health.get('s3', False),
                    'dynamodb_connection': aws_health.get('dynamodb', False),
                    'audio_processor': processor_info['processor_type'],
                    'file_validator': 'operational'
                },
                'configuration': {
                    'max_retries': self.max_retries,
                    'processing_timeout': self.processing_timeout,
                    'processor_type': processor_info['processor_type']
                }
            }
            
            # Determine overall health
            all_healthy = all(health_status['components'].values())
            health_status['status'] = 'healthy' if all_healthy else 'degraded'
            
            return health_status
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def process_with_retry(self, s3_event: Dict[str, Any], max_retries: Optional[int] = None) -> Dict[str, Any]:
        """
        Process S3 event with retry logic.
        
        Args:
            s3_event: S3 event to process
            max_retries: Maximum retry attempts (uses default if None)
            
        Returns:
            Processing result
        """
        retries = max_retries if max_retries is not None else self.max_retries
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retrying processing (attempt {attempt + 1}/{retries + 1})", extra={
                        "key": s3_event.get('key', 'unknown')
                    })
                
                return self.process_s3_event(s3_event)
                
            except Exception as e:
                last_error = e
                if attempt < retries:
                    # Wait before retry (exponential backoff)
                    wait_time = min(2 ** attempt, 30)  # Max 30 seconds
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Processing failed after {retries + 1} attempts", extra={
                        "key": s3_event.get('key', 'unknown'),
                        "final_error": str(e)
                    })
                    raise last_error


# Global pipeline orchestrator instance
pipeline_orchestrator = AudioProcessingPipeline()
