"""
Registration orchestrator for audio processing pipeline.

This module orchestrates the complete audio processing workflow using
Clean Architecture principles and shared layer components.
"""
import logging
import time
from typing import Dict, Any
from datetime import datetime, timezone

# Import from shared layer
from shared.core.usecases.process_voice_sample import ProcessVoiceSampleUseCase
from shared.adapters.audio_processors.resemblyzer_processor import get_audio_processor
from shared.adapters.storage.s3_audio_storage import S3AudioStorageService
from shared.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository

# Import legacy components (for completion checking and notifications)
from utils.completion_checker import completion_checker
from utils.notification_handler import notification_handler
from utils.user_status_manager import user_status_manager

logger = logging.getLogger(__name__)


class RegistrationOrchestrator:
    """
    Orchestrates the complete audio registration workflow.
    
    Coordinates between the shared layer use cases and legacy components
    for registration completion tracking and user notifications.
    """
    
    def __init__(self):
        """Initialize the registration orchestrator with dependencies."""
        # Shared layer dependencies
        self.audio_processor = get_audio_processor()
        self.storage_service = S3AudioStorageService()
        self.user_repository = DynamoDBUserRepository()
        
        # Create use case with dependencies
        self.process_voice_sample = ProcessVoiceSampleUseCase(
            audio_processor=self.audio_processor,
            storage_service=self.storage_service,
            user_repository=self.user_repository
        )
        
        logger.info("Registration orchestrator initialized")
    
    async def process_registration_audio(self, s3_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single S3 audio file for user registration.
        
        Args:
            s3_event: Parsed S3 event with bucket, key, size info
            
        Returns:
            Dict with complete processing results
        """
        start_time = time.time()
        bucket = s3_event['bucket']
        key = s3_event['key']
        
        logger.info("Starting registration audio processing", extra={
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
            # Stage 1: Extract user ID from file path
            user_id = self.storage_service.extract_user_id_from_path(key)
            processing_result['user_id'] = user_id
            
            processing_result['processing_stages']['extract_user_id'] = {
                'status': 'success',
                'user_id': user_id,
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Stage 2-4: Process voice sample using shared layer use case
            voice_processing_result = await self.process_voice_sample.execute(key)
            
            # Extract results from use case
            voice_embedding = voice_processing_result['voice_embedding']
            user_update_result = voice_processing_result['user_update_result']
            
            processing_result['processing_stages']['voice_processing'] = {
                'status': 'success',
                'embedding_dimensions': voice_embedding.get_embedding_dimensions(),
                'quality_score': voice_embedding.quality_score,
                'total_embeddings': user_update_result['total_embeddings'],
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Stage 5: Legacy completion checking and notifications
            completion_result = await self._check_completion_stage(user_id, processing_result)
            
            # Calculate processing time
            processing_result['processing_time_ms'] = int((time.time() - start_time) * 1000)
            processing_result['success'] = True
            processing_result['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Compile final result
            processing_result.update({
                'embedding_dimensions': voice_embedding.get_embedding_dimensions(),
                'quality_score': voice_embedding.quality_score,
                'user_embedding_count': user_update_result['total_embeddings'],
                'registration_complete': completion_result['is_complete']
            })
            
            logger.info("Registration audio processing completed successfully", extra={
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
            
            logger.error("Registration audio processing failed", extra={
                "bucket": bucket,
                "key": key,
                "user_id": processing_result.get('user_id'),
                "error": str(e),
                "processing_time_ms": processing_result['processing_time_ms']
            })
            
            raise
    
    async def _check_completion_stage(self, user_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy completion checking and notification stage.
        
        This maintains compatibility with existing notification system
        while using the new architecture for core processing.
        """
        stage_name = "check_completion"
        logger.debug(f"Starting stage: {stage_name}")
        
        try:
            # Get complete user data for analysis (using legacy approach for compatibility)
            user_data = await self.user_repository.get_user(user_id)
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
                
                await self.user_repository.update_user_status(user_id, {
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
