"""
Tests for Registration Orchestrator using Clean Architecture with Dependency Injection.

This module tests the RegistrationOrchestrator class which coordinates
the voice sample processing workflow using the shared layer components
through dependency injection.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from application.registration_orchestrator import RegistrationOrchestrator

# Try to import shared layer components for tests
try:
    from shared.core.usecases.process_voice_sample import ProcessVoiceSampleUseCase
    SHARED_LAYER_AVAILABLE = True
except ImportError:
    SHARED_LAYER_AVAILABLE = False
    ProcessVoiceSampleUseCase = None


class TestRegistrationOrchestrator:
    """Test cases for the RegistrationOrchestrator class."""

    @patch('application.registration_orchestrator.get_audio_processor')
    @patch('application.registration_orchestrator.get_storage_service')
    @patch('application.registration_orchestrator.get_user_repository')
    @patch('application.registration_orchestrator.get_process_voice_sample_use_case')
    @patch('application.registration_orchestrator.completion_checker')
    @patch('application.registration_orchestrator.user_status_manager')
    @patch('application.registration_orchestrator.notification_handler')
    def test_orchestrator_initialization(self, mock_notification_handler, mock_status_manager,
                                       mock_completion_checker, mock_get_use_case, 
                                       mock_get_repo, mock_get_storage, mock_get_audio):
        """Test that the orchestrator initializes correctly with dependency injection."""
        # Setup mock dependencies
        mock_audio_processor = Mock()
        mock_storage_service = Mock()
        mock_user_repository = Mock()
        mock_use_case = Mock()
        
        mock_get_audio.return_value = mock_audio_processor
        mock_get_storage.return_value = mock_storage_service
        mock_get_repo.return_value = mock_user_repository
        mock_get_use_case.return_value = mock_use_case
        
        # Initialize orchestrator
        orchestrator = RegistrationOrchestrator()
        
        # Verify dependencies were retrieved
        mock_get_audio.assert_called_once()
        mock_get_storage.assert_called_once()
        mock_get_repo.assert_called_once()
        mock_get_use_case.assert_called_once()
        
        # Verify orchestrator has the dependencies
        assert orchestrator.audio_processor == mock_audio_processor
        assert orchestrator.storage_service == mock_storage_service
        assert orchestrator.user_repository == mock_user_repository
        assert orchestrator.process_voice_sample_use_case == mock_use_case
        assert orchestrator.completion_checker == mock_completion_checker
        assert orchestrator.user_status_manager == mock_status_manager
        assert orchestrator.notification_handler == mock_notification_handler

    @pytest.mark.asyncio
    @patch('application.registration_orchestrator.get_audio_processor')
    @patch('application.registration_orchestrator.get_storage_service')
    @patch('application.registration_orchestrator.get_user_repository')
    @patch('application.registration_orchestrator.get_process_voice_sample_use_case')
    @patch('application.registration_orchestrator.completion_checker')
    @patch('application.registration_orchestrator.user_status_manager')
    @patch('application.registration_orchestrator.notification_handler')
    async def test_process_registration_audio_success(self, mock_notification_handler, mock_status_manager,
                                                     mock_completion_checker, mock_get_use_case,
                                                     mock_get_repo, mock_get_storage, mock_get_audio):
        """Test successful audio processing workflow."""
        # Setup mock storage service
        mock_storage_service = Mock()
        mock_storage_service.extract_user_id_from_path.return_value = 'user123'
        mock_get_storage.return_value = mock_storage_service
        
        # Setup mock use case
        mock_use_case = AsyncMock()
        mock_voice_embedding = Mock()
        mock_voice_embedding.get_embedding_dimensions.return_value = 256
        mock_voice_embedding.quality_score = 0.85
        
        mock_use_case.execute.return_value = {
            'success': True,
            'user_id': 'user123',
            'voice_embedding': mock_voice_embedding,
            'user_update_result': {
                'total_embeddings': 2,
                'registration_complete': False
            }
        }
        mock_get_use_case.return_value = mock_use_case
        
        # Setup mock user repository
        mock_user_repository = AsyncMock()
        mock_user_repository.get_user.return_value = {
            'user_id': 'user123',
            'registration_complete': False
        }
        mock_user_repository.update_user_status.return_value = {'updated': True}
        mock_get_repo.return_value = mock_user_repository
        
        # Setup completion checker mocks
        mock_completion_checker.check_completion_status.return_value = {
            'is_complete': False,
            'completion_confidence': 0.75,
            'registration_score': 0.8,
            'recommendations': []
        }
        mock_completion_checker.should_trigger_completion_update.return_value = False
        
        # Setup status manager mock
        mock_status_manager.analyze_registration_progress.return_value = {
            'completion_percentage': 66.7,
            'progress_metrics': {
                'samples_collected': 2,
                'required_samples': 3,
                'completion_percentage': 66.7,
                'samples_remaining': 1
            },
            'current_status': 'in_progress',
            'quality_analysis': {
                'average_quality': 0.85,
                'quality_trend': 'stable'
            }
        }
        
        # Setup notification handler mock
        mock_notification_handler.notify_sample_recorded.return_value = {
            'sent': True
        }
        
        # Initialize orchestrator and process
        orchestrator = RegistrationOrchestrator()
        
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'audio-uploads/user123/sample.wav',
            'size': 1048576
        }
        
        result = await orchestrator.process_registration_audio(s3_event)
        
        # Verify success
        assert result['success'] is True
        assert result['user_id'] == 'user123'
        assert 'processing_time_ms' in result
        assert result['embedding_dimensions'] == 256
        assert result['quality_score'] == 0.85
        assert result['user_embedding_count'] == 2
        assert result['registration_complete'] is False
        
        # Verify use case was called
        mock_use_case.execute.assert_called_once_with('audio-uploads/user123/sample.wav')
        
        # Verify completion checking was performed
        mock_completion_checker.check_completion_status.assert_called_once()
        mock_status_manager.analyze_registration_progress.assert_called_once()

    @pytest.mark.asyncio
    @patch('application.registration_orchestrator.get_audio_processor')
    @patch('application.registration_orchestrator.get_storage_service')
    @patch('application.registration_orchestrator.get_user_repository')
    @patch('application.registration_orchestrator.get_process_voice_sample_use_case')
    @patch('application.registration_orchestrator.completion_checker')
    @patch('application.registration_orchestrator.user_status_manager')
    @patch('application.registration_orchestrator.notification_handler')
    async def test_process_registration_audio_use_case_failure(self, mock_notification_handler, mock_status_manager,
                                                              mock_completion_checker, mock_get_use_case,
                                                              mock_get_repo, mock_get_storage, mock_get_audio):
        """Test handling of use case failures."""
        # Setup mock storage service
        mock_storage_service = Mock()
        mock_storage_service.extract_user_id_from_path.return_value = 'user123'
        mock_get_storage.return_value = mock_storage_service
        
        # Setup mock use case to raise exception
        mock_use_case = AsyncMock()
        mock_use_case.execute.side_effect = Exception("Processing failed")
        mock_get_use_case.return_value = mock_use_case
        
        # Initialize orchestrator
        orchestrator = RegistrationOrchestrator()
        
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'audio-uploads/user123/sample.wav',
            'size': 1048576
        }
        
        # Expect exception to be raised
        with pytest.raises(Exception, match="Processing failed"):
            await orchestrator.process_registration_audio(s3_event)

    @pytest.mark.asyncio
    @patch('application.registration_orchestrator.get_audio_processor')
    @patch('application.registration_orchestrator.get_storage_service')
    @patch('application.registration_orchestrator.get_user_repository')
    @patch('application.registration_orchestrator.get_process_voice_sample_use_case')
    @patch('application.registration_orchestrator.completion_checker')
    @patch('application.registration_orchestrator.user_status_manager')
    @patch('application.registration_orchestrator.notification_handler')
    async def test_process_registration_audio_completion_trigger(self, mock_notification_handler, mock_status_manager,
                                                               mock_completion_checker, mock_get_use_case,
                                                               mock_get_repo, mock_get_storage, mock_get_audio):
        """Test that completion checking triggers appropriate updates."""
        # Setup mock storage service
        mock_storage_service = Mock()
        mock_storage_service.extract_user_id_from_path.return_value = 'user123'
        mock_get_storage.return_value = mock_storage_service
        
        # Setup mock use case
        mock_use_case = AsyncMock()
        mock_voice_embedding = Mock()
        mock_voice_embedding.get_embedding_dimensions.return_value = 256
        mock_voice_embedding.quality_score = 0.95
        
        mock_use_case.execute.return_value = {
            'success': True,
            'user_id': 'user123',
            'voice_embedding': mock_voice_embedding,
            'user_update_result': {
                'total_embeddings': 3,
                'registration_complete': True
            }
        }
        mock_get_use_case.return_value = mock_use_case
        
        # Setup mock user repository
        mock_user_repository = AsyncMock()
        mock_user_repository.get_user.return_value = {
            'user_id': 'user123',
            'registration_complete': True,
            'voice_embeddings': [{'id': 1}, {'id': 2}, {'id': 3}]
        }
        mock_user_repository.update_user_status.return_value = {'updated': True}
        mock_get_repo.return_value = mock_user_repository
        
        # Setup completion checker to indicate completion
        mock_completion_checker.check_completion_status.return_value = {
            'is_complete': True,
            'completion_confidence': 0.95,
            'registration_score': 0.92,
            'recommendations': []
        }
        mock_completion_checker.should_trigger_completion_update.return_value = True
        
        # Setup status manager
        mock_status_manager.analyze_registration_progress.return_value = {
            'completion_percentage': 100.0,
            'progress_metrics': {
                'samples_collected': 3,
                'required_samples': 3,
                'completion_percentage': 100.0,
                'samples_remaining': 0
            },
            'current_status': 'completed',
            'quality_analysis': {
                'average_quality': 0.95,
                'quality_trend': 'excellent'
            }
        }
        
        # Setup notification handler
        mock_notification_handler.notify_registration_completed.return_value = {
            'sent': True
        }
        
        # Initialize orchestrator and process
        orchestrator = RegistrationOrchestrator()
        
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'audio-uploads/user123/final_sample.wav',
            'size': 1048576
        }
        
        result = await orchestrator.process_registration_audio(s3_event)
        
        # Verify completion was detected
        assert result['success'] is True
        assert result['registration_complete'] is True
        assert result['user_embedding_count'] == 3
        assert result['embedding_dimensions'] == 256
        assert result['quality_score'] == 0.95
        
        # Verify completion notification was sent
        mock_notification_handler.notify_registration_completed.assert_called_once()


class TestProcessVoiceSampleUseCase:
    """Test cases for the ProcessVoiceSampleUseCase integration."""

    @pytest.mark.asyncio
    async def test_use_case_execution_success(self, mock_s3_event):
        """Test successful execution of the process voice sample use case."""
        with patch('shared.adapters.audio_processors.resemblyzer_processor.get_audio_processor') as mock_get_processor, \
             patch('shared.adapters.storage.s3_audio_storage.S3AudioStorageService') as mock_storage_class, \
             patch('shared.adapters.repositories.dynamodb_user_repository.DynamoDBUserRepository') as mock_repo_class:
            
            # Setup mocks
            mock_processor = Mock()
            mock_embedding = [0.1] * 256  # Mock 256-dimensional embedding
            mock_processor.validate_audio_quality.return_value = {
                'is_valid': True,
                'overall_quality_score': 0.85,
                'issues': []
            }
            mock_processor.generate_embedding.return_value = mock_embedding
            mock_processor.get_processor_info.return_value = {
                'processor_type': 'mock',
                'embedding_dimensions': 256
            }
            mock_get_processor.return_value = mock_processor
            
            mock_storage = Mock()
            mock_storage.download_audio_file = AsyncMock(return_value=b'fake_audio_data')
            mock_storage.get_file_metadata = AsyncMock(return_value={
                'ContentLength': 1048576,
                'ContentType': 'audio/wav',
                'size_bytes': 1048576,
                'file_extension': 'wav'
            })
            mock_storage.extract_user_id_from_path.return_value = 'user123'
            mock_storage_class.return_value = mock_storage
            
            mock_repository = Mock()
            mock_repository.add_voice_embedding = AsyncMock(return_value={
                'user_id': 'user123',
                'total_embeddings': 2,
                'registration_complete': False,
                'updated_user': {}
            })
            mock_repo_class.return_value = mock_repository
            
            # Import and create use case
            if not SHARED_LAYER_AVAILABLE:
                pytest.skip("Shared layer not available")
            use_case = ProcessVoiceSampleUseCase(mock_processor, mock_storage, mock_repository)
            
            # Execute use case - ProcessVoiceSampleUseCase.execute expects file_path string
            file_path = 'audio-uploads/user123/sample.wav'
            
            result = await use_case.execute(file_path)
            
            # Verify result
            assert result['success'] is True
            assert result['user_id'] == 'user123'
            assert result['quality_score'] == 0.85
            assert 'voice_embedding' in result
            assert 'user_update_result' in result
            assert result['user_update_result']['total_embeddings'] == 2


class TestOrchestrationIntegration:
    """Integration tests for the complete orchestration workflow."""

    @pytest.mark.asyncio
    @patch('application.registration_orchestrator.get_audio_processor')
    @patch('application.registration_orchestrator.get_storage_service')
    @patch('application.registration_orchestrator.get_user_repository')
    @patch('application.registration_orchestrator.get_process_voice_sample_use_case')
    @patch('application.registration_orchestrator.completion_checker')
    @patch('application.registration_orchestrator.user_status_manager')
    @patch('application.registration_orchestrator.notification_handler')
    async def test_full_orchestration_flow(self, mock_notification_handler, mock_status_manager,
                                         mock_completion_checker, mock_get_use_case,
                                         mock_get_repo, mock_get_storage, mock_get_audio):
        """Test the complete orchestration flow with all components."""
        # Setup mock storage service
        mock_storage_service = Mock()
        mock_storage_service.extract_user_id_from_path.return_value = 'user123'
        mock_get_storage.return_value = mock_storage_service
        
        # Setup complete mock workflow
        mock_voice_embedding = Mock()
        mock_voice_embedding.get_embedding_dimensions.return_value = 256
        mock_voice_embedding.quality_score = 0.88
        
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = {
            'success': True,
            'user_id': 'user123',
            'voice_embedding': mock_voice_embedding,
            'user_update_result': {
                'total_embeddings': 3,
                'registration_complete': True
            }
        }
        mock_get_use_case.return_value = mock_use_case
        
        # Setup mock user repository
        mock_user_repository = AsyncMock()
        mock_user_repository.get_user.return_value = {
            'user_id': 'user123',
            'registration_complete': True
        }
        mock_user_repository.update_user_status.return_value = {'updated': True}
        mock_get_repo.return_value = mock_user_repository
        
        # Setup completion flow
        mock_completion_checker.check_completion_status.return_value = {
            'is_complete': True,
            'completion_confidence': 0.90,
            'registration_score': 0.88,
            'recommendations': []
        }
        mock_completion_checker.should_trigger_completion_update.return_value = True
        
        mock_status_manager.analyze_registration_progress.return_value = {
            'completion_percentage': 100.0,
            'progress_metrics': {
                'samples_collected': 3,
                'required_samples': 3,
                'completion_percentage': 100.0,
                'samples_remaining': 0
            },
            'current_status': 'completed',
            'quality_analysis': {
                'average_quality': 0.88,
                'quality_trend': 'excellent'
            }
        }
        
        mock_notification_handler.notify_registration_completed.return_value = {
            'sent': True
        }
        
        # Execute full flow
        orchestrator = RegistrationOrchestrator()
        
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'audio-uploads/user123/final_sample.wav',
            'size': 1048576
        }
        
        result = await orchestrator.process_registration_audio(s3_event)
        
        # Verify complete flow
        assert result['success'] is True
        assert result['user_id'] == 'user123'
        assert result['registration_complete'] is True
        assert result['embedding_dimensions'] == 256
        assert result['quality_score'] == 0.88
        assert result['user_embedding_count'] == 3
        
        # Verify all services were called
        mock_use_case.execute.assert_called_once()
        mock_completion_checker.check_completion_status.assert_called_once()
        mock_status_manager.analyze_registration_progress.assert_called_once()
        mock_notification_handler.notify_registration_completed.assert_called_once()