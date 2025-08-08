"""
Unit tests for AudioProcessingPipeline.

Tests the main pipeline orchestrator including stage execution,
error handling, and retry logic.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from pipeline_orchestrator import AudioProcessingPipeline


@pytest.mark.unit
class TestAudioProcessingPipeline:
    """Test cases for AudioProcessingPipeline."""
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization with default settings."""
        pipeline = AudioProcessingPipeline()
        
        assert pipeline.max_retries >= 0
        assert pipeline.processing_timeout > 0
    
    def test_process_s3_event_success(self, sample_audio_data, sample_file_metadata, mock_user_data, mock_embedding_result):
        """Test successful S3 event processing through all stages."""
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'audio-uploads/user123/sample1.wav',
            'size': 1048576,
            'user_id': 'user123'
        }
        
        pipeline = AudioProcessingPipeline()
        
        with patch('pipeline_orchestrator.s3_operations') as mock_s3, \
             patch('pipeline_orchestrator.dynamodb_operations') as mock_db, \
             patch('pipeline_orchestrator.process_audio_file') as mock_audio_proc, \
             patch('pipeline_orchestrator.audio_file_validator') as mock_validator, \
             patch('pipeline_orchestrator.completion_checker') as mock_completion, \
             patch('pipeline_orchestrator.user_status_manager') as mock_status, \
             patch('pipeline_orchestrator.notification_handler') as mock_notification:
            
            # Setup mocks for all stages
            mock_s3.extract_user_id_from_key.return_value = 'user123'
            mock_s3.download_audio_file.return_value = sample_audio_data
            mock_s3.get_file_info_summary.return_value = sample_file_metadata
            
            mock_validator.validate_file.return_value = {
                'is_valid': True,
                'validation_passed': ['File size validation', 'File format validation'],
                'validation_failed': [],
                'warnings': []
            }
            
            mock_audio_proc.return_value = mock_embedding_result
            
            mock_db.add_voice_embedding.return_value = {
                'total_embeddings': 2,
                'registration_complete': False
            }
            mock_db.get_user.return_value = mock_user_data
            
            mock_completion.check_completion_status.return_value = {
                'is_complete': False,
                'completion_confidence': 0.65,
                'registration_score': 75.2,
                'recommendations': ['Upload 1 more sample']
            }
            
            mock_status.analyze_registration_progress.return_value = {
                'progress_metrics': {
                    'samples_collected': 2,
                    'required_samples': 3,
                    'samples_remaining': 1,
                    'completion_percentage': 66.7
                },
                'current_status': 'in_progress',
                'quality_analysis': {
                    'average_quality': 0.82,
                    'quality_trend': 'stable'
                }
            }
            
            mock_completion.should_trigger_completion_update.return_value = False
            
            mock_notification.notify_sample_recorded.return_value = {
                'message': 'Sample recorded successfully',
                'progress': 66.7
            }
            
            # Execute
            result = pipeline.process_s3_event(s3_event)
            
            # Verify
            assert result['success'] is True
            assert result['user_id'] == 'user123'
            assert result['processing_time_ms'] > 0
            assert len(result['processing_stages']) == 5
            
            # Verify all stages completed successfully
            for stage_name, stage_result in result['processing_stages'].items():
                assert stage_result['status'] == 'success'
    
    def test_process_s3_event_user_id_extraction_failure(self):
        """Test pipeline failure at user ID extraction stage."""
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'invalid-key-format',
            'size': 1048576
        }
        
        pipeline = AudioProcessingPipeline()
        
        with patch('pipeline_orchestrator.s3_operations') as mock_s3:
            mock_s3.extract_user_id_from_key.side_effect = ValueError("Invalid key format")
            
            with pytest.raises(ValueError, match="Invalid key format"):
                pipeline.process_s3_event(s3_event)
    
    def test_process_s3_event_file_validation_failure(self, sample_audio_data, sample_file_metadata):
        """Test pipeline failure at file validation stage."""
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'audio-uploads/user123/sample1.wav',
            'size': 1048576
        }
        
        pipeline = AudioProcessingPipeline()
        
        with patch('pipeline_orchestrator.s3_operations') as mock_s3, \
             patch('pipeline_orchestrator.audio_file_validator') as mock_validator:
            
            mock_s3.extract_user_id_from_key.return_value = 'user123'
            mock_s3.download_audio_file.return_value = sample_audio_data
            mock_s3.get_file_info_summary.return_value = sample_file_metadata
            
            mock_validator.validate_file.return_value = {
                'is_valid': False,
                'validation_passed': [],
                'validation_failed': ['File too large'],
                'warnings': []
            }
            
            with pytest.raises(ValueError, match="File validation failed"):
                pipeline.process_s3_event(s3_event)
    
    def test_process_s3_event_embedding_generation_failure(self, sample_audio_data, sample_file_metadata):
        """Test pipeline failure at embedding generation stage."""
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'audio-uploads/user123/sample1.wav',
            'size': 1048576
        }
        
        pipeline = AudioProcessingPipeline()
        
        with patch('pipeline_orchestrator.s3_operations') as mock_s3, \
             patch('pipeline_orchestrator.audio_file_validator') as mock_validator, \
             patch('pipeline_orchestrator.process_audio_file') as mock_audio_proc:
            
            mock_s3.extract_user_id_from_key.return_value = 'user123'
            mock_s3.download_audio_file.return_value = sample_audio_data
            mock_s3.get_file_info_summary.return_value = sample_file_metadata
            
            mock_validator.validate_file.return_value = {
                'is_valid': True,
                'validation_passed': ['File size validation'],
                'validation_failed': [],
                'warnings': []
            }
            
            mock_audio_proc.side_effect = RuntimeError("Embedding generation failed")
            
            with pytest.raises(RuntimeError, match="Embedding generation failed"):
                pipeline.process_s3_event(s3_event)
    
    def test_process_with_retry_success_on_first_attempt(self, sample_audio_data):
        """Test retry logic with success on first attempt."""
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'audio-uploads/user123/sample1.wav',
            'size': 1048576
        }
        
        pipeline = AudioProcessingPipeline()
        
        with patch.object(pipeline, 'process_s3_event') as mock_process:
            mock_process.return_value = {'success': True}
            
            result = pipeline.process_with_retry(s3_event, max_retries=3)
            
            assert result['success'] is True
            mock_process.assert_called_once_with(s3_event)
    
    def test_process_with_retry_success_on_second_attempt(self):
        """Test retry logic with success on second attempt."""
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'audio-uploads/user123/sample1.wav',
            'size': 1048576
        }
        
        pipeline = AudioProcessingPipeline()
        
        with patch.object(pipeline, 'process_s3_event') as mock_process, \
             patch('time.sleep'):  # Speed up test by mocking sleep
            
            # First call fails, second succeeds
            mock_process.side_effect = [RuntimeError("Temporary error"), {'success': True}]
            
            result = pipeline.process_with_retry(s3_event, max_retries=3)
            
            assert result['success'] is True
            assert mock_process.call_count == 2
    
    def test_process_with_retry_failure_after_all_attempts(self):
        """Test retry logic with failure after all attempts."""
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'audio-uploads/user123/sample1.wav',
            'size': 1048576
        }
        
        pipeline = AudioProcessingPipeline()
        
        with patch.object(pipeline, 'process_s3_event') as mock_process, \
             patch('time.sleep'):  # Speed up test
            
            mock_process.side_effect = RuntimeError("Persistent error")
            
            with pytest.raises(RuntimeError, match="Persistent error"):
                pipeline.process_with_retry(s3_event, max_retries=2)
            
            assert mock_process.call_count == 3  # Initial + 2 retries
    
    def test_get_pipeline_health_healthy(self):
        """Test pipeline health check when all components are healthy."""
        pipeline = AudioProcessingPipeline()
        
        with patch('pipeline_orchestrator.aws_lambda_config_manager') as mock_aws_config:
            mock_aws_config.test_connections.return_value = {
                's3': True,
                'dynamodb': True
            }
            
            with patch('pipeline_orchestrator.get_audio_processor') as mock_get_processor:
                mock_processor = Mock()
                mock_processor.get_processor_info.return_value = {
                    'processor_type': 'mock',
                    'processor_name': 'MockAudioProcessor'
                }
                mock_get_processor.return_value = mock_processor
                
                health = pipeline.get_pipeline_health()
                
                assert health['status'] == 'healthy'
                assert health['components']['s3_connection'] is True
                assert health['components']['dynamodb_connection'] is True
                assert health['components']['audio_processor'] == 'mock'
    
    def test_get_pipeline_health_degraded(self):
        """Test pipeline health check when some components are unhealthy."""
        pipeline = AudioProcessingPipeline()
        
        with patch('pipeline_orchestrator.aws_lambda_config_manager') as mock_aws_config:
            mock_aws_config.test_connections.return_value = {
                's3': False,  # S3 connection failed
                'dynamodb': True
            }
            
            with patch('pipeline_orchestrator.get_audio_processor') as mock_get_processor:
                mock_processor = Mock()
                mock_processor.get_processor_info.return_value = {
                    'processor_type': 'mock'
                }
                mock_get_processor.return_value = mock_processor
                
                health = pipeline.get_pipeline_health()
                
                assert health['status'] == 'degraded'
                assert health['components']['s3_connection'] is False
    
    def test_get_pipeline_health_exception(self):
        """Test pipeline health check with exception."""
        pipeline = AudioProcessingPipeline()
        
        with patch('pipeline_orchestrator.aws_lambda_config_manager') as mock_aws_config:
            mock_aws_config.test_connections.side_effect = Exception("Connection test failed")
            
            health = pipeline.get_pipeline_health()
            
            assert health['status'] == 'unhealthy'
            assert 'error' in health


@pytest.mark.integration
class TestPipelineIntegration:
    """Integration tests for pipeline with real components."""
    
    def test_pipeline_with_real_audio_processor(self, sample_audio_data, sample_file_metadata):
        """Test pipeline with real MockAudioProcessor."""
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'audio-uploads/user123/sample1.wav',
            'size': len(sample_audio_data)
        }
        
        pipeline = AudioProcessingPipeline()
        
        with patch('pipeline_orchestrator.s3_operations') as mock_s3, \
             patch('pipeline_orchestrator.dynamodb_operations') as mock_db, \
             patch('pipeline_orchestrator.audio_file_validator') as mock_validator, \
             patch('pipeline_orchestrator.completion_checker') as mock_completion, \
             patch('pipeline_orchestrator.user_status_manager') as mock_status, \
             patch('pipeline_orchestrator.notification_handler') as mock_notification:
            
            # Setup basic mocks but use real audio processor
            mock_s3.extract_user_id_from_key.return_value = 'user123'
            mock_s3.download_audio_file.return_value = sample_audio_data
            mock_s3.get_file_info_summary.return_value = sample_file_metadata
            
            mock_validator.validate_file.return_value = {
                'is_valid': True,
                'validation_passed': ['All validations passed'],
                'validation_failed': [],
                'warnings': []
            }
            
            mock_db.add_voice_embedding.return_value = {
                'total_embeddings': 1,
                'registration_complete': False
            }
            mock_db.get_user.return_value = {'user_id': 'user123', 'voice_embeddings': []}
            
            mock_completion.check_completion_status.return_value = {
                'is_complete': False,
                'completion_confidence': 0.33,
                'registration_score': 33.3,
                'recommendations': []
            }
            
            mock_status.analyze_registration_progress.return_value = {
                'progress_metrics': {'samples_collected': 1, 'required_samples': 3},
                'current_status': 'in_progress',
                'quality_analysis': {'average_quality': 0.85}
            }
            
            mock_completion.should_trigger_completion_update.return_value = False
            mock_notification.notify_sample_recorded.return_value = {'message': 'Sample recorded'}
            
            # Execute - this will use real audio processor
            result = pipeline.process_s3_event(s3_event)
            
            # Verify
            assert result['success'] is True
            assert result['embedding_dimensions'] == 256  # MockAudioProcessor returns 256-dim embeddings
            assert 0.0 <= result['quality_score'] <= 1.0
