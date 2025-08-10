"""
Authentication orchestrator for voice authentication pipeline.

This module orchestrates the complete voice authentication workflow using
Clean Architecture principles, integrating Whisper transcription and
password validation with voice embedding authentication.
"""
import sys
import os
import logging
import time
import hashlib
from typing import Dict, Any, List
from datetime import datetime, timezone

# Add shared layer to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared_layer', 'python'))

# Import from shared layer and application dependencies
from shared.core.usecases.authenticate_voice import AuthenticateVoiceUseCase
from shared.core.services.audio_quality_validator import validate_audio_quality
from application.dependencies import (
    get_audio_processor,
    get_storage_service,
    get_user_repository,
    get_authenticate_voice_use_case,
    get_transcription_service
)

logger = logging.getLogger(__name__)


class AuthOrchestrator:
    """
    Orchestrates the complete voice authentication workflow.
    
    Coordinates dual authentication: password words validation + voice embedding
    comparison for secure voice-based user authentication.
    """
    
    def __init__(self):
        """Initialize the authentication orchestrator with dependencies."""
        # Get dependencies from dependency injection container
        self.audio_processor = get_audio_processor()
        self.storage_service = get_storage_service()
        self.user_repository = get_user_repository()
        self.authenticate_voice_use_case = get_authenticate_voice_use_case()
        self.transcription_service = get_transcription_service()
        
        logger.info("Authentication orchestrator initialized")
    
    async def process_authentication_audio(self, s3_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single S3 audio file for voice authentication.
        
        Performs dual validation:
        1. Transcription + password word validation
        2. Voice embedding comparison
        
        Args:
            s3_event: Parsed S3 event with bucket, key, size info
            
        Returns:
            Dict with complete authentication results
        """
        start_time = time.time()
        bucket = s3_event['bucket']
        key = s3_event['key']
        
        logger.info("Starting voice authentication processing", extra={
            "bucket": bucket,
            "key": key,
            "event_size": s3_event.get('size', 0)
        })
        
        authentication_result = {
            'bucket': bucket,
            'key': key,
            'user_id': None,
            'authentication_successful': False,
            'confidence_score': 0.0,
            'authentication_result': 'failed',
            'processing_stages': {},
            'error_details': None,
            'processing_time_ms': 0,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'completed_at': None
        }
        
        try:
            # Stage 1: Extract user ID from file path
            user_id = self.storage_service.extract_user_id_from_path(key)
            authentication_result['user_id'] = user_id
            
            authentication_result['processing_stages']['extract_user_id'] = {
                'status': 'success',
                'user_id': user_id,
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Stage 2: Download and validate audio file
            logger.debug("Stage 2: Downloading authentication audio file")
            audio_data = await self.storage_service.download_file(key)
            file_metadata = self.storage_service.get_file_metadata(key)
            
            authentication_result['processing_stages']['download_audio'] = {
                'status': 'success',
                'file_size': len(audio_data),
                'metadata': file_metadata,
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Stage 3: Validate audio quality and security
            logger.debug("Stage 3: Validating authentication audio quality")
            security_validation = validate_audio_quality(audio_data, file_metadata)
            
            if not security_validation['is_valid']:
                raise ValueError(f"Audio validation failed: {security_validation['validation_failed']}")
            
            ml_quality_validation = self.audio_processor.validate_audio_quality(audio_data, file_metadata)
            
            if not ml_quality_validation['is_valid']:
                raise ValueError(f"Audio ML quality validation failed: {ml_quality_validation['issues']}")
            
            authentication_result['processing_stages']['validate_audio'] = {
                'status': 'success',
                'security_validation': security_validation,
                'ml_quality_validation': ml_quality_validation,
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Stage 4: Dual Authentication - Transcription + Password Validation
            transcription_result = await self._perform_transcription_validation(
                user_id, audio_data, file_metadata, authentication_result
            )
            
            # Stage 5: Voice Embedding Authentication
            embedding_result = await self._perform_embedding_authentication(
                user_id, key, authentication_result
            )
            
            # Stage 6: Combine authentication results
            final_result = await self._combine_authentication_results(
                user_id, transcription_result, embedding_result, authentication_result
            )
            
            # Calculate processing time
            authentication_result['processing_time_ms'] = int((time.time() - start_time) * 1000)
            authentication_result['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            logger.info("Voice authentication processing completed", extra={
                "user_id": user_id,
                "authentication_successful": final_result['authentication_successful'],
                "confidence_score": final_result['confidence_score'],
                "processing_time_ms": authentication_result['processing_time_ms']
            })
            
            return authentication_result
            
        except Exception as e:
            authentication_result['processing_time_ms'] = int((time.time() - start_time) * 1000)
            authentication_result['error_details'] = {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'failed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.error("Voice authentication processing failed", extra={
                "bucket": bucket,
                "key": key,
                "user_id": authentication_result.get('user_id'),
                "error": str(e),
                "processing_time_ms": authentication_result['processing_time_ms']
            })
            
            raise
    
    async def _perform_transcription_validation(
        self, 
        user_id: str, 
        audio_data: bytes, 
        file_metadata: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform audio transcription and password word validation.
        
        Uses Whisper to transcribe audio and validates against stored password hash.
        """
        stage_name = "transcription_validation"
        logger.debug(f"Starting stage: {stage_name}")
        
        try:
            # Get user's password hash for validation
            user_data = await self.user_repository.get_user(user_id)
            if not user_data:
                raise ValueError(f"User {user_id} not found")
            
            password_hash = user_data.get('password_hash')
            if not password_hash:
                raise ValueError(f"No password hash found for user {user_id}")
            
            # Transcribe audio using Whisper (via audio processor)
            logger.debug("Transcribing audio with Whisper")
            transcription_result = await self._transcribe_audio_with_whisper(audio_data, file_metadata)
            
            transcribed_text = transcription_result['text'].lower().strip()
            confidence = transcription_result.get('confidence', 0.0)
            
            logger.info("Audio transcription completed", extra={
                "user_id": user_id,
                "transcribed_length": len(transcribed_text),
                "confidence": confidence
            })
            
            # Extract words from transcription
            words = self._extract_words_from_transcription(transcribed_text)
            
            # Validate words against password hash
            password_validation = self._validate_password_words(words, password_hash)
            
            transcription_validation_result = {
                'transcribed_text': transcribed_text,
                'extracted_words': words,
                'transcription_confidence': confidence,
                'password_validation': password_validation,
                'words_match': password_validation['words_match'],
                'word_match_confidence': password_validation['confidence']
            }
            
            result['processing_stages'][stage_name] = {
                'status': 'success',
                'transcribed_text': transcribed_text,
                'word_count': len(words),
                'words_match': password_validation['words_match'],
                'transcription_confidence': confidence,
                'word_match_confidence': password_validation['confidence'],
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info("Transcription validation completed", extra={
                "user_id": user_id,
                "words_match": password_validation['words_match'],
                "transcription_confidence": confidence,
                "word_match_confidence": password_validation['confidence']
            })
            
            return transcription_validation_result
            
        except Exception as e:
            result['processing_stages'][stage_name] = {
                'status': 'failed',
                'error': str(e),
                'failed_at': datetime.now(timezone.utc).isoformat()
            }
            raise
    
    async def _perform_embedding_authentication(
        self, 
        user_id: str, 
        file_path: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform voice embedding authentication using existing use case.
        """
        stage_name = "embedding_authentication"
        logger.debug(f"Starting stage: {stage_name}")
        
        try:
            # Use the existing AuthenticateVoiceUseCase for embedding authentication
            embedding_auth_result = await self.authenticate_voice_use_case.execute_from_file(
                user_id=user_id,
                file_path=file_path
            )
            
            result['processing_stages'][stage_name] = {
                'status': 'success',
                'authentication_successful': embedding_auth_result['authentication_successful'],
                'confidence_score': embedding_auth_result['confidence_score'],
                'authentication_result': embedding_auth_result['authentication_result'],
                'user_embeddings_count': embedding_auth_result.get('user_embeddings_count', 0),
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info("Embedding authentication completed", extra={
                "user_id": user_id,
                "authentication_successful": embedding_auth_result['authentication_successful'],
                "confidence_score": embedding_auth_result['confidence_score']
            })
            
            return embedding_auth_result
            
        except Exception as e:
            result['processing_stages'][stage_name] = {
                'status': 'failed',
                'error': str(e),
                'failed_at': datetime.now(timezone.utc).isoformat()
            }
            raise
    
    async def _combine_authentication_results(
        self,
        user_id: str,
        transcription_result: Dict[str, Any],
        embedding_result: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combine transcription and embedding authentication results.
        
        Both validations must pass for successful authentication.
        """
        stage_name = "combine_results"
        logger.debug(f"Starting stage: {stage_name}")
        
        try:
            # Extract results from both validations
            words_match = transcription_result['words_match']
            word_confidence = transcription_result['word_match_confidence']
            
            embedding_success = embedding_result['authentication_successful']
            embedding_confidence = embedding_result['confidence_score']
            
            # Both validations must pass
            authentication_successful = words_match and embedding_success
            
            # Combined confidence score (weighted average)
            # Give equal weight to both factors
            combined_confidence = (word_confidence + embedding_confidence) / 2.0
            
            # Determine final authentication result
            if authentication_successful:
                auth_result = "authenticated"
            elif not words_match and not embedding_success:
                auth_result = "rejected_both"
            elif not words_match:
                auth_result = "rejected_password"
            else:  # not embedding_success
                auth_result = "rejected_voice"
            
            # Update main result
            result.update({
                'authentication_successful': authentication_successful,
                'confidence_score': combined_confidence,
                'authentication_result': auth_result,
                'dual_validation': {
                    'password_validation': {
                        'words_match': words_match,
                        'confidence': word_confidence,
                        'transcribed_text': transcription_result['transcribed_text']
                    },
                    'voice_validation': {
                        'authentication_successful': embedding_success,
                        'confidence': embedding_confidence,
                        'similarity_analysis': embedding_result.get('similarity_analysis', {}),
                        'user_embeddings_count': embedding_result.get('user_embeddings_count', 0)
                    }
                }
            })
            
            result['processing_stages'][stage_name] = {
                'status': 'success',
                'authentication_successful': authentication_successful,
                'combined_confidence': combined_confidence,
                'auth_result': auth_result,
                'password_passed': words_match,
                'voice_passed': embedding_success,
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info("Authentication results combined", extra={
                "user_id": user_id,
                "authentication_successful": authentication_successful,
                "combined_confidence": combined_confidence,
                "auth_result": auth_result,
                "password_passed": words_match,
                "voice_passed": embedding_success
            })
            
            return result
            
        except Exception as e:
            result['processing_stages'][stage_name] = {
                'status': 'failed',
                'error': str(e),
                'failed_at': datetime.now(timezone.utc).isoformat()
            }
            raise
    
    async def _transcribe_audio_with_whisper(self, audio_data: bytes, file_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transcribe audio using OpenAI Whisper API.
        
        Uses the transcription service to convert audio to text for password validation.
        """
        logger.debug("Transcribing audio with OpenAI Whisper")
        
        try:
            # Extract filename from metadata if available
            filename = file_metadata.get('filename', 'auth_audio.wav')
            
            # Use the transcription service
            transcription_result = await self.transcription_service.transcribe_audio(
                audio_data=audio_data,
                language="es",  # Spanish for password validation
                filename=filename
            )
            
            logger.info("Whisper transcription completed", extra={
                'text_length': len(transcription_result['text']),
                'confidence': transcription_result.get('confidence', 0.0),
                'processing_time_ms': transcription_result.get('processing_time_ms', 0)
            })
            
            return transcription_result
            
        except Exception as e:
            logger.error("Whisper transcription failed", extra={
                'error': str(e),
                'file_size': len(audio_data),
                'metadata': file_metadata
            })
            
            # Re-raise to be handled by caller
            raise
    
    def _extract_words_from_transcription(self, transcribed_text: str) -> List[str]:
        """
        Extract words from transcribed text.
        
        Removes punctuation and normalizes words for password validation.
        """
        import re
        
        # Remove punctuation and split into words
        words = re.findall(r'\b[a-záéíóúñü]+\b', transcribed_text.lower())
        
        # Filter out very short words (likely artifacts)
        filtered_words = [word for word in words if len(word) >= 3]
        
        logger.debug("Extracted words from transcription", extra={
            'original_text': transcribed_text,
            'extracted_words': filtered_words,
            'word_count': len(filtered_words)
        })
        
        return filtered_words
    
    def _validate_password_words(self, extracted_words: List[str], stored_password_hash: str) -> Dict[str, Any]:
        """
        Validate extracted words against stored password hash.
        
        Creates hash from extracted words and compares with stored hash.
        """
        if not extracted_words:
            return {
                'words_match': False,
                'confidence': 0.0,
                'error': 'No words extracted from transcription'
            }
        
        # Join words with hyphens (same format as original password)
        reconstructed_password = '-'.join(sorted(extracted_words))
        
        # Create hash from reconstructed password
        reconstructed_hash = hashlib.sha256(reconstructed_password.encode('utf-8')).hexdigest()
        
        # Compare hashes
        words_match = reconstructed_hash == stored_password_hash
        
        # Calculate confidence based on word count and exact match
        expected_word_count = 3  # Assuming 3-word passwords
        word_count_confidence = min(len(extracted_words) / expected_word_count, 1.0)
        
        confidence = 1.0 if words_match else word_count_confidence * 0.5
        
        logger.debug("Password validation completed", extra={
            'extracted_words': extracted_words,
            'reconstructed_password': reconstructed_password,
            'words_match': words_match,
            'confidence': confidence
        })
        
        return {
            'words_match': words_match,
            'confidence': confidence,
            'reconstructed_password': reconstructed_password,
            'word_count': len(extracted_words),
            'expected_word_count': expected_word_count
        }
