"""
Process voice sample use case.

This module contains the business logic for processing voice samples,
following Clean Architecture principles with dependency inversion.
"""
from typing import Dict, Any
from ..models.audio_sample import AudioSample
from ..models.voice_embedding import VoiceEmbedding
from ..ports.audio_processor import AudioProcessorPort
from ..ports.storage_service import StorageServicePort
from ..ports.user_repository import UserRepositoryPort


class ProcessVoiceSampleUseCase:
    """
    Use case for processing voice samples and generating embeddings.
    
    Orchestrates the complete process of downloading, validating,
    processing, and storing voice sample data.
    """
    
    def __init__(
        self,
        audio_processor: AudioProcessorPort,
        storage_service: StorageServicePort,
        user_repository: UserRepositoryPort
    ):
        """
        Initialize the process voice sample use case.
        
        Args:
            audio_processor: Audio processing implementation
            storage_service: Storage service implementation  
            user_repository: User repository implementation
        """
        self.audio_processor = audio_processor
        self.storage_service = storage_service
        self.user_repository = user_repository
    
    async def execute(self, file_path: str) -> Dict[str, Any]:
        """
        Process a voice sample from storage.
        
        Args:
            file_path: Path to the audio file in storage
            
        Returns:
            Dict with processing results
            
        Raises:
            ValueError: If validation fails
            RuntimeError: If processing fails
        """
        # Extract user ID from file path
        user_id = self.storage_service.extract_user_id_from_path(file_path)
        
        # Get file metadata
        file_metadata = await self.storage_service.get_file_metadata(file_path)
        
        # Create audio sample domain object
        audio_sample = AudioSample.create(
            file_path=file_path,
            file_size_bytes=file_metadata['size_bytes'],
            format=file_metadata['file_extension'],
            user_id=user_id,
            sample_metadata=file_metadata
        )
        
        # Download audio data
        audio_data = await self.storage_service.download_audio_file(file_path)
        
        # Validate audio quality
        quality_result = self.audio_processor.validate_audio_quality(
            audio_data, file_metadata
        )
        
        if not quality_result['is_valid']:
            raise ValueError(f"Audio quality validation failed: {quality_result['issues']}")
        
        # Generate voice embedding
        embedding = self.audio_processor.generate_embedding(audio_data, file_metadata)
        quality_score = quality_result['overall_quality_score']
        
        # Update audio sample with processing results
        audio_sample.set_processing_result(embedding, quality_score)
        
        # Create voice embedding domain object
        voice_embedding = VoiceEmbedding.create(
            embedding=embedding,
            quality_score=quality_score,
            user_id=user_id,
            sample_metadata=file_metadata,
            processor_info=self.audio_processor.get_processor_info()
        )
        
        # Store embedding in user record
        user_update_result = await self.user_repository.add_voice_embedding(
            user_id=user_id,
            embedding=embedding,
            metadata={
                'file_name': file_metadata.get('file_name', ''),
                'size_bytes': file_metadata.get('size_bytes', 0),
                'quality_score': quality_score,
                'processor_type': voice_embedding.processor_info.get('processor_type', 'unknown')
            }
        )
        
        # Return processing result
        return {
            'success': True,
            'user_id': user_id,
            'file_path': file_path,
            'embedding_dimensions': voice_embedding.get_embedding_dimensions(),
            'quality_score': quality_score,
            'voice_embedding': voice_embedding,
            'user_update_result': user_update_result,
            'processing_metadata': {
                'file_size_bytes': audio_sample.file_size_bytes,
                'format': audio_sample.format,
                'processor_info': voice_embedding.processor_info,
                'validation_result': quality_result
            }
        }
