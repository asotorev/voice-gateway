"""
Registration orchestrator for audio processing pipeline.

This module orchestrates the complete audio processing workflow using
Clean Architecture principles and shared layer components.
"""
import sys
import os
import logging
import time
from typing import Dict, Any
from datetime import datetime, timezone

# Add shared layer to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared_layer', 'python'))

# Import from shared layer and application dependencies
from shared.core.usecases.process_voice_sample import ProcessVoiceSampleUseCase
from shared.core.services import (
    completion_checker,
    user_status_manager,
    notification_handler
)
from application.dependencies import (
    get_audio_processor,
    get_storage_service,
    get_user_repository,
    get_process_voice_sample_use_case
)

logger = logging.getLogger(__name__)


class RegistrationOrchestrator:
    """
    Orchestrates the complete audio registration workflow.
    
    Coordinates between the shared layer use cases and completion tracking
    services for registration workflow and user notifications.
    """
    
    def __init__(self):
        """Initialize the registration orchestrator with dependencies."""
        # Get dependencies from dependency injection container
        self.audio_processor = get_audio_processor()
        self.storage_service = get_storage_service()
        self.user_repository = get_user_repository()
        self.process_voice_sample_use_case = get_process_voice_sample_use_case()
        self.completion_checker = completion_checker
        self.user_status_manager = user_status_manager
        self.notification_handler = notification_handler
        
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
            voice_processing_result = await self.process_voice_sample_use_case.execute(key)
            
            # Extract results from use case
            voice_embedding = voice_processing_result['voice_embedding']
            user_update_result = voice_processing_result['user_update_result']
            processing_metadata = voice_processing_result['processing_metadata']
            
            # Check for security validation warnings
            security_validation = processing_metadata.get('security_validation', {})
            security_warnings = security_validation.get('warnings', [])
            
            processing_result['processing_stages']['voice_processing'] = {
                'status': 'success',
                'embedding_dimensions': voice_embedding.get_embedding_dimensions(),
                'quality_score': voice_embedding.quality_score,
                'total_embeddings': user_update_result['total_embeddings'],
                'security_warnings': security_warnings,
                'validation_summary': {
                    'security_score': security_validation.get('overall_score', 1.0),
                    'ml_quality_valid': processing_metadata.get('ml_quality_validation', {}).get('is_valid', True)
                },
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Stage 5: Completion checking and notifications
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
        Completion checking and notification stage.
        
        This maintains compatibility with existing notification system
        while using the new architecture for core processing.
        """
        stage_name = "check_completion"
        logger.debug(f"Starting stage: {stage_name}")
        
        try:
            # Get complete user data for analysis
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
                completion_response = notification_handler.send_registration_completed_notification(user_id, {
                    'total_samples': progress_analysis['progress_metrics']['samples_collected'],
                    'average_quality': progress_analysis['quality_analysis']['average_quality'],
                    'completion_confidence': completion_analysis['completion_confidence'],
                    'registration_score': completion_analysis['registration_score']
                })
            
            # Create progress response for non-completed registrations
            if not completion_analysis['is_complete']:
                # Check if we should send quality warning
                if progress_analysis['quality_analysis']['average_quality'] < 0.7:
                    quality_issues = [
                        f"Average quality {progress_analysis['quality_analysis']['average_quality']:.2f} below threshold",
                        f"Quality trend: {progress_analysis['quality_analysis']['quality_trend']}"
                    ]
                    progress_response = notification_handler.send_quality_warning_notification(
                        user_id, 
                        quality_issues,
                        progress_analysis['quality_analysis']['average_quality']
                    )
                else:
                    # Create regular progress response
                    sample_info = {
                        'sample_number': progress_analysis['progress_metrics']['samples_collected'],
                        'total_samples': progress_analysis['progress_metrics']['samples_collected'],
                        'required_samples': progress_analysis['progress_metrics']['required_samples'],
                        'completion_percentage': progress_analysis['progress_metrics']['completion_percentage'],
                        'samples_remaining': progress_analysis['progress_metrics']['samples_remaining']
                    }
                    progress_response = notification_handler.send_sample_recorded_notification(user_id, sample_info)
            
            # Check for security warnings from current processing
            security_warnings = result.get('processing_stages', {}).get('voice_processing', {}).get('security_warnings', [])
            if security_warnings:
                security_response = notification_handler.send_quality_warning_notification(
                    user_id,
                    [f"Security warning: {warning}" for warning in security_warnings],
                    0.5  # Lower quality score for security issues
                )
            
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
                
            # Add security response if available
            if 'security_response' in locals():
                enhanced_result['security_response'] = security_response
            
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
