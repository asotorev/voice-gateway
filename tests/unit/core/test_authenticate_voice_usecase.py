"""
Unit tests for Authenticate Voice Use Case.

Tests the business logic for voice authentication including audio processing,
embedding comparison, and authentication decision workflow.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any
from datetime import datetime, timezone

# Import the use case (adjust path as needed for test environment)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'app', 'infrastructure', 'lambda', 'shared_layer', 'python'))

from shared.core.usecases.authenticate_voice import AuthenticateVoiceUseCase
from shared.core.models.voice_embedding import VoiceEmbedding


class TestAuthenticateVoiceUseCase:
    """Test AuthenticateVoiceUseCase class."""
    
    @pytest.fixture
    def mock_audio_processor(self):
        """Create mock audio processor."""
        mock = MagicMock()
        mock.validate_audio_quality.return_value = {
            'is_valid': True,
            'issues': [],
            'overall_quality_score': 0.9
        }
        mock.generate_embedding.return_value = [0.1] * 256
        return mock
    
    @pytest.fixture
    def mock_storage_service(self):
        """Create mock storage service."""
        mock = AsyncMock()
        # Create larger mock audio data to pass validation
        mock.download_file.return_value = b'mock_audio_data' * 200  # ~2800 bytes
        # get_file_metadata should be sync
        mock.get_file_metadata = MagicMock(return_value={
            'file_name': 'test_audio.wav',
            'file_size': 2800,
            'content_type': 'audio/wav'
        })
        return mock
    
    @pytest.fixture
    def mock_user_repository(self):
        """Create mock user repository."""
        mock = AsyncMock()
        mock.user_exists.return_value = True
        mock.get_user_embeddings.return_value = [
            VoiceEmbedding.create(
                embedding=[0.2] * 256,
                quality_score=0.85,
                user_id="test_user",
                sample_metadata={'file_name': 'sample1.wav'},
                processor_info={'model': 'resemblyzer'}
            )
        ]
        mock.get_user_embedding_count.return_value = 1
        return mock
    
    @pytest.fixture
    def mock_voice_authentication(self):
        """Create mock voice authentication service."""
        mock = MagicMock()
        mock.authenticate_voice.return_value = {
            'authentication_successful': True,
            'confidence_score': 0.85,
            'authentication_result': 'authenticated',
            'is_high_confidence': True,
            'similarity_analysis': {
                'similarities': [0.85],
                'average_similarity': 0.85,
                'max_similarity': 0.85,
                'total_comparisons': 1
            },
            'confidence_analysis': {
                'confidence_score': 0.85,
                'meets_threshold': True
            }
        }
        mock.get_authentication_config.return_value = {
            'minimum_embeddings_required': 1,
            'authentication_threshold': 0.8
        }
        return mock
    
    @pytest.fixture
    def use_case(self, mock_audio_processor, mock_storage_service, mock_user_repository, mock_voice_authentication):
        """Create AuthenticateVoiceUseCase instance for testing."""
        return AuthenticateVoiceUseCase(
            audio_processor=mock_audio_processor,
            storage_service=mock_storage_service,
            user_repository=mock_user_repository,
            voice_authentication=mock_voice_authentication
        )
    
    @pytest.fixture
    def sample_embedding(self):
        """Create a sample embedding for testing."""
        return [0.1] * 256
    
    @pytest.mark.asyncio
    async def test_initialization(self, use_case):
        """Test use case initialization."""
        assert use_case.audio_processor is not None
        assert use_case.storage_service is not None
        assert use_case.user_repository is not None
        assert use_case.voice_authentication is not None
    
    @pytest.mark.asyncio
    @patch('shared.core.services.audio_quality_validator.validate_audio_quality')
    async def test_execute_from_file_success(self, mock_validate_audio, use_case):
        """Test successful authentication from audio file."""
        # Mock audio quality validation
        mock_validate_audio.return_value = {
            'is_valid': True,
            'validation_failed': [],
            'overall_score': 0.9
        }
        
        result = await use_case.execute_from_file("test_user", "path/to/audio.wav")
        
        # Check main result structure
        assert isinstance(result, dict)
        assert result['user_id'] == "test_user"
        assert result['file_path'] == "path/to/audio.wav"
        assert result['authentication_successful'] is True
        assert isinstance(result['confidence_score'], float)
        assert 'processing_stages' in result
        assert 'started_at' in result
        assert 'completed_at' in result
        
        # Check processing stages
        stages = result['processing_stages']
        assert 'download_audio' in stages
        assert 'validate_audio' in stages
        assert 'generate_embedding' in stages
        assert 'voice_authentication' in stages
        
        # Verify all stages completed successfully
        for stage_name, stage_data in stages.items():
            assert stage_data['status'] == 'success'
            assert 'completed_at' in stage_data
    
    @pytest.mark.asyncio
    async def test_execute_from_file_audio_validation_failure(self, use_case):
        """Test authentication failure due to audio validation."""
        # Create a smaller audio file that will fail validation
        small_storage_service = AsyncMock()
        small_storage_service.download_file.return_value = b'small'  # Too small
        small_storage_service.get_file_metadata = MagicMock(return_value={
            'file_name': 'tiny.wav',
            'file_size': 5,
            'content_type': 'audio/wav'
        })
        
        # Temporarily replace storage service
        original_storage = use_case.storage_service
        use_case.storage_service = small_storage_service
        
        try:
            with pytest.raises(ValueError, match="Audio validation failed"):
                await use_case.execute_from_file("test_user", "path/to/bad_audio.wav")
        finally:
            # Restore original storage service
            use_case.storage_service = original_storage
    
    @pytest.mark.asyncio
    async def test_execute_from_file_ml_quality_failure(self, use_case, mock_audio_processor):
        """Test authentication failure due to ML quality validation."""
        # Mock ML quality validation failure
        mock_audio_processor.validate_audio_quality.return_value = {
            'is_valid': False,
            'issues': ['Audio quality too low'],
            'overall_quality_score': 0.3
        }
        
        with patch('shared.core.services.audio_quality_validator.validate_audio_quality') as mock_validate:
            # Ensure security validation passes first
            mock_validate.return_value = {
                'is_valid': True, 
                'validation_failed': [],
                'overall_score': 0.9
            }
            
            with pytest.raises(ValueError, match="Audio ML quality validation failed"):
                await use_case.execute_from_file("test_user", "path/to/low_quality.wav")
    
    @pytest.mark.asyncio
    async def test_execute_with_embedding_success(self, use_case, sample_embedding):
        """Test successful authentication with pre-generated embedding."""
        result = await use_case.execute_with_embedding("test_user", sample_embedding)
        
        assert isinstance(result, dict)
        assert result['authentication_successful'] is True
        assert isinstance(result['confidence_score'], float)
        assert 'similarity_analysis' in result
        assert 'confidence_analysis' in result
        assert 'user_embeddings_count' in result
        assert 'processing_time_ms' in result
    
    @pytest.mark.asyncio
    async def test_execute_with_embedding_invalid_input(self, use_case):
        """Test authentication with invalid embedding input."""
        with pytest.raises(ValueError, match="Input embedding cannot be empty"):
            await use_case.execute_with_embedding("test_user", [])
        
        with pytest.raises(ValueError, match="Input embedding must be a list"):
            await use_case.execute_with_embedding("test_user", "invalid_embedding")
    
    @pytest.mark.asyncio
    async def test_execute_with_embedding_user_not_found(self, use_case, sample_embedding, mock_user_repository):
        """Test authentication with non-existent user."""
        mock_user_repository.user_exists.return_value = False
        
        with pytest.raises(ValueError, match="User test_user not found"):
            await use_case.execute_with_embedding("test_user", sample_embedding)
    
    @pytest.mark.asyncio
    async def test_execute_with_embedding_no_stored_embeddings(self, use_case, sample_embedding, mock_user_repository):
        """Test authentication with user who has no stored embeddings."""
        mock_user_repository.get_user_embeddings.return_value = []
        
        result = await use_case.execute_with_embedding("test_user", sample_embedding)
        
        assert result['authentication_successful'] is False
        assert result['confidence_score'] == 0.0
        assert result['authentication_result'] == 'insufficient_data'
        assert result['user_embeddings_count'] == 0
        assert 'error' in result['similarity_analysis']
    
    @pytest.mark.asyncio
    async def test_execute_with_embedding_successful_authentication(self, use_case, sample_embedding, mock_user_repository, mock_voice_authentication):
        """Test successful authentication workflow with stored embeddings."""
        # Setup multiple stored embeddings
        mock_user_repository.get_user_embeddings.return_value = [
            VoiceEmbedding.create(
                embedding=[0.2] * 256,
                quality_score=0.85,
                user_id="test_user",
                sample_metadata={'file_name': 'sample1.wav'},
                processor_info={'model': 'resemblyzer'}
            ),
            VoiceEmbedding.create(
                embedding=[0.3] * 256,
                quality_score=0.90,
                user_id="test_user",
                sample_metadata={'file_name': 'sample2.wav'},
                processor_info={'model': 'resemblyzer'}
            )
        ]
        
        result = await use_case.execute_with_embedding("test_user", sample_embedding)
        
        assert result['authentication_successful'] is True
        assert result['user_embeddings_count'] == 2
        assert isinstance(result['processing_time_ms'], float)
        
        # Verify voice authentication was called with correct data
        mock_voice_authentication.authenticate_voice.assert_called_once()
        call_args = mock_voice_authentication.authenticate_voice.call_args
        assert call_args[1]['input_embedding'] == sample_embedding
        assert len(call_args[1]['stored_embeddings']) == 2
    
    @pytest.mark.asyncio
    async def test_validate_user_for_authentication_success(self, use_case, mock_user_repository, mock_voice_authentication):
        """Test successful user validation for authentication."""
        mock_user_repository.get_user_embedding_count.return_value = 3
        
        result = await use_case.validate_user_for_authentication("test_user")
        
        assert result['is_ready'] is True
        assert result['user_exists'] is True
        assert result['embeddings_count'] == 3
        assert result['minimum_required'] == 1
        assert result['can_authenticate'] is True
        assert 'validation_message' in result
    
    @pytest.mark.asyncio
    async def test_validate_user_for_authentication_user_not_found(self, use_case, mock_user_repository):
        """Test user validation when user doesn't exist."""
        mock_user_repository.user_exists.return_value = False
        
        result = await use_case.validate_user_for_authentication("nonexistent_user")
        
        assert result['is_ready'] is False
        assert result['user_exists'] is False
        assert 'error' in result
        assert "not found" in result['error']
    
    @pytest.mark.asyncio
    async def test_validate_user_for_authentication_insufficient_embeddings(self, use_case, mock_user_repository, mock_voice_authentication):
        """Test user validation when user has insufficient embeddings."""
        mock_user_repository.get_user_embedding_count.return_value = 0
        mock_voice_authentication.get_authentication_config.return_value = {
            'minimum_embeddings_required': 2
        }
        
        result = await use_case.validate_user_for_authentication("test_user")
        
        assert result['is_ready'] is False
        assert result['user_exists'] is True
        assert result['embeddings_count'] == 0
        assert result['minimum_required'] == 2
        assert result['can_authenticate'] is False
    
    @pytest.mark.asyncio
    async def test_validate_user_for_authentication_exception_handling(self, use_case, mock_user_repository):
        """Test user validation exception handling."""
        mock_user_repository.user_exists.side_effect = Exception("Database error")
        
        result = await use_case.validate_user_for_authentication("test_user")
        
        assert result['is_ready'] is False
        assert result['user_exists'] is None
        assert 'error' in result
        assert "Validation failed" in result['error']
    
    @pytest.mark.asyncio
    async def test_voice_embedding_conversion(self, use_case, sample_embedding, mock_user_repository):
        """Test conversion of VoiceEmbedding objects to service format."""
        # Create a VoiceEmbedding with specific datetime
        test_datetime = datetime.now(timezone.utc)
        voice_embedding = VoiceEmbedding.create(
            embedding=[0.2] * 256,
            quality_score=0.85,
            user_id="test_user",
            sample_metadata={'file_name': 'sample1.wav', 'duration': 3.0},
            processor_info={'model': 'resemblyzer', 'version': '1.0'}
        )
        voice_embedding.created_at = test_datetime
        
        mock_user_repository.get_user_embeddings.return_value = [voice_embedding]
        
        await use_case.execute_with_embedding("test_user", sample_embedding)
        
        # Verify the conversion was correct
        call_args = use_case.voice_authentication.authenticate_voice.call_args
        stored_embeddings_data = call_args[1]['stored_embeddings']
        
        assert len(stored_embeddings_data) == 1
        converted_embedding = stored_embeddings_data[0]
        
        assert converted_embedding['embedding'] == [0.2] * 256
        assert converted_embedding['quality_score'] == 0.85
        assert converted_embedding['created_at'] == test_datetime.isoformat()
        assert converted_embedding['audio_metadata'] == {'file_name': 'sample1.wav', 'duration': 3.0}


class TestAuthenticateVoiceUseCaseIntegration:
    """Integration tests for AuthenticateVoiceUseCase."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_integration(self):
        """Test full authentication workflow with minimal mocking."""
        pass


if __name__ == "__main__":
    pytest.main([__file__])
