"""
Unit tests for Lambda handler.

Tests the main entry point of the Lambda function including event parsing,
error handling, and response formatting.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from handler import lambda_handler, process_single_audio_file, extract_user_id_from_key


@pytest.mark.unit
class TestLambdaHandler:
    """Test cases for Lambda handler functionality."""
    
    def test_lambda_handler_success(self, mock_s3_event, mock_lambda_context):
        """Test successful Lambda handler execution."""
        with patch('handler.S3EventParser') as mock_parser, \
             patch('handler.process_single_audio_file') as mock_process:
            
            # Setup mocks
            mock_parser.return_value.parse_event.return_value = [
                {'bucket': 'test-bucket', 'key': 'audio-uploads/user123/sample1.wav', 'size': 1048576}
            ]
            mock_process.return_value = {
                'bucket': 'test-bucket',
                'key': 'audio-uploads/user123/sample1.wav',
                'user_id': 'user123',
                'success': True,
                'embedding_generated': True,
                'registration_complete': False
            }
            
            # Execute
            result = lambda_handler(mock_s3_event, mock_lambda_context)
            
            # Verify
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed_files'] == 1
            assert body['failed_files'] == 0
            assert len(body['results']) == 1
    
    def test_lambda_handler_no_events(self, mock_lambda_context):
        """Test Lambda handler with no valid S3 events."""
        with patch('handler.S3EventParser') as mock_parser:
            mock_parser.return_value.parse_event.return_value = []
            
            result = lambda_handler({}, mock_lambda_context)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed_files'] == 0
    
    def test_lambda_handler_processing_failure(self, mock_s3_event, mock_lambda_context):
        """Test Lambda handler with processing failure."""
        with patch('handler.S3EventParser') as mock_parser, \
             patch('handler.process_single_audio_file') as mock_process:
            
            mock_parser.return_value.parse_event.return_value = [
                {'bucket': 'test-bucket', 'key': 'audio-uploads/user123/sample1.wav', 'size': 1048576}
            ]
            mock_process.side_effect = ValueError("File validation failed")
            
            result = lambda_handler(mock_s3_event, mock_lambda_context)
            
            assert result['statusCode'] == 207  # Multi-Status
            body = json.loads(result['body'])
            assert body['failed_files'] == 1
            assert len(body['errors']) == 1
    
    def test_lambda_handler_exception(self, mock_lambda_context):
        """Test Lambda handler with unexpected exception."""
        with patch('handler.S3EventParser') as mock_parser:
            mock_parser.side_effect = Exception("Unexpected error")
            
            result = lambda_handler({}, mock_lambda_context)
            
            assert result['statusCode'] == 500
            body = json.loads(result['body'])
            assert 'Internal server error' in body['message']


@pytest.mark.unit
class TestProcessSingleAudioFile:
    """Test cases for single audio file processing."""
    
    def test_process_single_audio_file_success(self):
        """Test successful audio file processing."""
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'audio-uploads/user123/sample1.wav',
            'size': 1048576
        }
        
        mock_pipeline_result = {
            'success': True,
            'embedding_stage': {'status': 'success'},
            'completion_stage': {'is_complete': False},
            'processing_time_ms': 1500,
            'processing_stages': {},
            'completion_response': None,
            'progress_response': {'message': 'Sample recorded'},
            'error_details': None
        }
        
        with patch('handler.extract_user_id_from_key') as mock_extract, \
             patch('handler.AudioProcessingPipeline') as mock_pipeline_class:
            
            mock_extract.return_value = 'user123'
            mock_pipeline = Mock()
            mock_pipeline_class.return_value = mock_pipeline
            mock_pipeline.process_s3_event.return_value = mock_pipeline_result
            
            result = process_single_audio_file(s3_event)
            
            assert result['success'] is True
            assert result['user_id'] == 'user123'
            assert result['embedding_generated'] is True
            assert result['registration_complete'] is False
            assert result['processing_time_ms'] == 1500
    
    def test_process_single_audio_file_pipeline_failure(self):
        """Test audio file processing with pipeline failure."""
        s3_event = {
            'bucket': 'test-bucket',
            'key': 'audio-uploads/user123/sample1.wav',
            'size': 1048576
        }
        
        with patch('handler.extract_user_id_from_key') as mock_extract, \
             patch('handler.AudioProcessingPipeline') as mock_pipeline_class:
            
            mock_extract.return_value = 'user123'
            mock_pipeline = Mock()
            mock_pipeline_class.return_value = mock_pipeline
            mock_pipeline.process_s3_event.side_effect = RuntimeError("Pipeline failed")
            
            result = process_single_audio_file(s3_event)
            
            assert result['success'] is False
            assert result['user_id'] is None
            assert result['embedding_generated'] is False
            assert 'Pipeline failed' in result['error']


@pytest.mark.unit
class TestExtractUserId:
    """Test cases for user ID extraction."""
    
    def test_extract_user_id_success(self):
        """Test successful user ID extraction."""
        with patch('handler.infra_settings') as mock_settings:
            mock_settings.s3_trigger_prefix = 'audio-uploads/'
            
            user_id = extract_user_id_from_key('audio-uploads/user123/sample1.wav')
            assert user_id == 'user123'
    
    def test_extract_user_id_invalid_prefix(self):
        """Test user ID extraction with invalid prefix."""
        with patch('handler.infra_settings') as mock_settings:
            mock_settings.s3_trigger_prefix = 'audio-uploads/'
            
            with pytest.raises(ValueError, match="Key does not start with expected prefix"):
                extract_user_id_from_key('wrong-prefix/user123/sample1.wav')
    
    def test_extract_user_id_no_user_id(self):
        """Test user ID extraction with no user ID."""
        with patch('handler.infra_settings') as mock_settings:
            mock_settings.s3_trigger_prefix = 'audio-uploads/'
            
            with pytest.raises(ValueError, match="Could not extract user_id"):
                extract_user_id_from_key('audio-uploads/')
    
    def test_extract_user_id_invalid_format(self):
        """Test user ID extraction with invalid key format."""
        with patch('handler.infra_settings') as mock_settings:
            mock_settings.s3_trigger_prefix = 'audio-uploads/'
            
            with pytest.raises(ValueError, match="Invalid S3 key format"):
                extract_user_id_from_key('completely-wrong-format')


@pytest.mark.integration
class TestHandlerIntegration:
    """Integration tests for handler with real components."""
    
    def test_handler_with_real_event_parser(self, mock_s3_event, mock_lambda_context):
        """Test handler with real S3EventParser."""
        with patch('handler.process_single_audio_file') as mock_process:
            mock_process.return_value = {
                'bucket': 'test-voice-uploads',
                'key': 'audio-uploads/user123/sample1.wav',
                'user_id': 'user123',
                'success': True,
                'embedding_generated': True,
                'registration_complete': False
            }
            
            result = lambda_handler(mock_s3_event, mock_lambda_context)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed_files'] == 1
            mock_process.assert_called_once()
    
    def test_handler_end_to_end_flow(self, mock_s3_event, mock_lambda_context, sample_audio_data):
        """Test end-to-end handler flow with mocked AWS services."""
        with patch('handler.AudioProcessingPipeline') as mock_pipeline_class, \
             patch('services.s3_operations.s3_operations') as mock_s3_ops, \
             patch('services.dynamodb_operations.dynamodb_operations') as mock_db_ops:
            
            # Setup comprehensive mocks
            mock_pipeline = Mock()
            mock_pipeline_class.return_value = mock_pipeline
            mock_pipeline.process_s3_event.return_value = {
                'success': True,
                'embedding_stage': {'status': 'success'},
                'completion_stage': {'is_complete': True},
                'processing_time_ms': 2000,
                'processing_stages': {
                    'extract_user_id': {'status': 'success'},
                    'download_and_validate': {'status': 'success'},
                    'generate_embedding': {'status': 'success'},
                    'update_user_record': {'status': 'success'},
                    'check_completion': {'status': 'success'}
                }
            }
            
            result = lambda_handler(mock_s3_event, mock_lambda_context)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed_files'] == 1
            assert body['failed_files'] == 0
