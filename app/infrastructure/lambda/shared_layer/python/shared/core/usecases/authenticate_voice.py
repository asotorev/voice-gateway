"""
Authenticate voice use case.

This module contains the business logic for authenticating users through voice,
following Clean Architecture principles with dependency inversion.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..models.voice_embedding import VoiceEmbedding
from ..ports.audio_processor import AudioProcessorPort
from ..ports.storage_service import StorageServicePort
from ..ports.user_repository import UserRepositoryPort
from ..ports.voice_authentication import VoiceAuthenticationPort
from ..services.audio_quality_validator import validate_audio_quality

logger = logging.getLogger(__name__)


class AuthenticateVoiceUseCase:
    """
    Use case for authenticating users through voice comparison.
    
    Orchestrates the complete process of processing input audio,
    retrieving user embeddings, and performing authentication.
    """
    
    def __init__(
        self,
        audio_processor: AudioProcessorPort,
        storage_service: StorageServicePort,
        user_repository: UserRepositoryPort,
        voice_authentication: VoiceAuthenticationPort
    ):
        """
        Initialize the authenticate voice use case.
        
        Args:
            audio_processor: Audio processing implementation
            storage_service: Storage service implementation
            user_repository: User repository implementation
            voice_authentication: Voice authentication implementation
        """
        self.audio_processor = audio_processor
        self.storage_service = storage_service
        self.user_repository = user_repository
        self.voice_authentication = voice_authentication
        
        logger.info("Authenticate voice use case initialized")
    
    async def execute_from_file(self, user_id: str, file_path: str) -> Dict[str, Any]:
        """
        Authenticate user using voice audio file from storage.
        
        Args:
            user_id: User identifier to authenticate
            file_path: Path to the audio file in storage
            
        Returns:
            Dict with authentication results and analysis
            
        Raises:
            ValueError: If user or audio data is invalid
            Exception: If processing fails
        """
        logger.info("Starting voice authentication from file", extra={
            "user_id": user_id,
            "file_path": file_path
        })
        
        start_time = datetime.now(timezone.utc)
        
        authentication_result = {
            'user_id': user_id,
            'file_path': file_path,
            'authentication_successful': False,
            'confidence_score': 0.0,
            'processing_stages': {},
            'error_details': None,
            'started_at': start_time.isoformat(),
            'completed_at': None
        }
        
        try:
            # Stage 1: Download and validate audio file
            logger.debug("Stage 1: Downloading audio file")
            audio_data = await self.storage_service.download_file(file_path)
            file_metadata = self.storage_service.get_file_metadata(file_path)
            
            authentication_result['processing_stages']['download_audio'] = {
                'status': 'success',
                'file_size': len(audio_data),
                'metadata': file_metadata,
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Stage 2: Validate audio quality and security
            logger.debug("Stage 2: Validating audio quality")
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
            
            # Stage 3: Generate embedding from input audio
            logger.debug("Stage 3: Generating embedding from input audio")
            input_embedding = self.audio_processor.generate_embedding(audio_data, file_metadata)
            
            authentication_result['processing_stages']['generate_embedding'] = {
                'status': 'success',
                'embedding_dimensions': len(input_embedding),
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Stage 4: Perform authentication
            auth_result = await self._authenticate_with_embedding(user_id, input_embedding)
            
            # Merge authentication results
            authentication_result.update({
                'authentication_successful': auth_result['authentication_successful'],
                'confidence_score': auth_result['confidence_score'],
                'authentication_result': auth_result['authentication_result'],
                'is_high_confidence': auth_result['is_high_confidence'],
                'similarity_analysis': auth_result['similarity_analysis'],
                'confidence_analysis': auth_result['confidence_analysis'],
                'user_embeddings_count': auth_result['user_embeddings_count']
            })
            
            authentication_result['processing_stages']['voice_authentication'] = {
                'status': 'success',
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info("Voice authentication completed successfully", extra={
                "user_id": user_id,
                "authentication_successful": auth_result['authentication_successful'],
                "confidence_score": auth_result['confidence_score']
            })
            
        except Exception as e:
            logger.error("Voice authentication failed", extra={
                "user_id": user_id,
                "file_path": file_path,
                "error": str(e)
            })
            
            authentication_result['error_details'] = {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'failed_at': datetime.now(timezone.utc).isoformat()
            }
            
            raise
        
        finally:
            authentication_result['completed_at'] = datetime.now(timezone.utc).isoformat()
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            authentication_result['processing_time_ms'] = processing_time
        
        return authentication_result
    
    async def execute_with_embedding(self, user_id: str, input_embedding: List[float]) -> Dict[str, Any]:
        """
        Authenticate user using pre-generated voice embedding.
        
        Args:
            user_id: User identifier to authenticate
            input_embedding: Voice embedding to authenticate
            
        Returns:
            Dict with authentication results and analysis
            
        Raises:
            ValueError: If user or embedding data is invalid
        """
        logger.info("Starting voice authentication with embedding", extra={
            "user_id": user_id,
            "embedding_dimensions": len(input_embedding) if input_embedding else 0
        })
        
        return await self._authenticate_with_embedding(user_id, input_embedding)
    
    async def _authenticate_with_embedding(self, user_id: str, input_embedding: List[float]) -> Dict[str, Any]:
        """
        Internal method to perform authentication with embedding.
        
        Args:
            user_id: User identifier to authenticate
            input_embedding: Voice embedding to authenticate
            
        Returns:
            Dict with authentication results
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Validate input embedding
            if not input_embedding:
                raise ValueError("Input embedding cannot be empty")
            
            if not isinstance(input_embedding, list):
                raise ValueError("Input embedding must be a list of floats")
            
            # Validate user exists
            user_exists = await self.user_repository.user_exists(user_id)
            if not user_exists:
                raise ValueError(f"User {user_id} not found")
            
            # Get user's stored embeddings
            logger.debug("Retrieving user's stored embeddings")
            user_embeddings = await self.user_repository.get_user_embeddings(user_id)
            
            if not user_embeddings:
                logger.warning("No stored embeddings found for user", extra={"user_id": user_id})
                return {
                    'authentication_successful': False,
                    'confidence_score': 0.0,
                    'authentication_result': 'insufficient_data',
                    'is_high_confidence': False,
                    'user_embeddings_count': 0,
                    'similarity_analysis': {
                        'total_comparisons': 0,
                        'error': 'No stored embeddings found'
                    },
                    'confidence_analysis': {
                        'error': 'Cannot authenticate without stored embeddings'
                    },
                    'processed_at': datetime.now(timezone.utc).isoformat(),
                    'processing_time_ms': (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                }
            
            # Convert VoiceEmbedding objects to format expected by authentication service
            stored_embeddings_data = []
            for voice_embedding in user_embeddings:
                stored_embeddings_data.append({
                    'embedding': voice_embedding.embedding,
                    'quality_score': voice_embedding.quality_score,
                    'created_at': voice_embedding.created_at.isoformat() if voice_embedding.created_at else None,
                    'audio_metadata': voice_embedding.sample_metadata
                })
            
            logger.debug("Performing voice authentication", extra={
                "user_id": user_id,
                "stored_embeddings_count": len(stored_embeddings_data),
                "input_embedding_dimensions": len(input_embedding)
            })
            
            # Perform authentication using voice authentication service
            auth_result = self.voice_authentication.authenticate_voice(
                input_embedding=input_embedding,
                stored_embeddings=stored_embeddings_data
            )
            
            # Add metadata
            auth_result['user_embeddings_count'] = len(stored_embeddings_data)
            auth_result['processing_time_ms'] = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.info("Voice authentication analysis completed", extra={
                "user_id": user_id,
                "authentication_successful": auth_result['authentication_successful'],
                "confidence_score": auth_result['confidence_score'],
                "stored_embeddings_used": len(stored_embeddings_data)
            })
            
            return auth_result
            
        except Exception as e:
            logger.error("Authentication with embedding failed", extra={
                "user_id": user_id,
                "error": str(e),
                "input_embedding_dimensions": len(input_embedding) if input_embedding else 0
            })
            raise
    
    async def validate_user_for_authentication(self, user_id: str) -> Dict[str, Any]:
        """
        Validate if user is ready for voice authentication.
        
        Args:
            user_id: User identifier to validate
            
        Returns:
            Dict with validation results and requirements
        """
        logger.debug("Validating user for authentication", extra={"user_id": user_id})
        
        try:
            # Check if user exists
            user_exists = await self.user_repository.user_exists(user_id)
            if not user_exists:
                return {
                    'is_ready': False,
                    'user_exists': False,
                    'error': f"User {user_id} not found"
                }
            
            # Check embeddings count
            embeddings_count = await self.user_repository.get_user_embedding_count(user_id)
            
            # Get minimum required embeddings from authentication config
            auth_config = self.voice_authentication.get_authentication_config()
            min_required = auth_config.get('minimum_embeddings_required', 1)
            
            is_ready = embeddings_count >= min_required
            
            return {
                'is_ready': is_ready,
                'user_exists': True,
                'embeddings_count': embeddings_count,
                'minimum_required': min_required,
                'can_authenticate': is_ready,
                'validation_message': (
                    f"User has {embeddings_count} embeddings, requires {min_required} minimum"
                )
            }
            
        except Exception as e:
            logger.error("User validation failed", extra={
                "user_id": user_id,
                "error": str(e)
            })
            return {
                'is_ready': False,
                'user_exists': None,
                'error': f"Validation failed: {str(e)}"
            }
