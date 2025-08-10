"""
Unit tests for Lambda handler using Clean Architecture.

Tests the main entry point of the Lambda function including event parsing,
error handling, response formatting, and delegation to the presentation layer.
"""
import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock

# Import the handler function to test
from handler import lambda_handler


@pytest.mark.unit
class TestLambdaHandler:
    """Test cases for Clean Architecture Lambda handler functionality."""
    
    def test_lambda_handler_success(self, mock_s3_event, mock_lambda_context):
        """Test successful Lambda handler execution with Clean Architecture."""
        
        # Mock the presentation layer components
        with patch('presentation.lambda_handler.S3EventParser') as mock_parser, \
             patch('presentation.lambda_handler.RegistrationOrchestrator') as mock_orchestrator_class:
            
            # Setup event parser mock
            mock_parser.return_value.parse_event.return_value = [
                {'bucket': 'test-bucket', 'key': 'audio-uploads/user123/sample1.wav', 'size': 1048576}
            ]
            
            # Setup orchestrator mock
            mock_orchestrator = Mock()
            mock_orchestrator_class.return_value = mock_orchestrator
            
            # Mock the async processing method
            async def mock_process_audio(*args, **kwargs):
                return {
                    'bucket': 'test-bucket',
                    'key': 'audio-uploads/user123/sample1.wav',
                    'user_id': 'user123',
                    'success': True,
                    'embedding_dimensions': 256,
                    'quality_score': 0.85,
                    'user_embedding_count': 1,
                    'registration_complete': False,
                    'processing_time_ms': 1500,
                    'processing_stages': {
                        'extract_user_id': {'status': 'success'},
                        'voice_processing': {'status': 'success'},
                        'check_completion': {'status': 'success'}
                    }
                }
            
            # Mock asyncio.run to handle the async call properly
            with patch('asyncio.run', side_effect=lambda coro: asyncio.get_event_loop().run_until_complete(coro)):
                mock_orchestrator.process_registration_audio = AsyncMock(side_effect=mock_process_audio)
                
                # Execute
                result = lambda_handler(mock_s3_event, mock_lambda_context)
                
                # Verify response structure
                assert result['statusCode'] == 200
                body = json.loads(result['body'])
                assert body['processed_files'] == 1
                assert body['failed_files'] == 0
                assert len(body['results']) == 1
                
                # Verify result details
                processed_result = body['results'][0]
                assert processed_result['success'] is True
                assert processed_result['user_id'] == 'user123'
                assert processed_result['embedding_dimensions'] == 256
                assert processed_result['quality_score'] == 0.85
                
                # Verify orchestrator was called
                mock_orchestrator.process_registration_audio.assert_called_once()
    
    def test_lambda_handler_no_events(self, mock_lambda_context):
        """Test Lambda handler with no valid S3 events."""
        
        with patch('presentation.lambda_handler.S3EventParser') as mock_parser:
            mock_parser.return_value.parse_event.return_value = []
            
            result = lambda_handler({}, mock_lambda_context)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed_files'] == 0
            assert 'No valid S3 events to process' in body['message']
    
    def test_lambda_handler_processing_failure(self, mock_s3_event, mock_lambda_context):
        """Test Lambda handler with processing failure."""
        
        with patch('presentation.lambda_handler.S3EventParser') as mock_parser, \
             patch('presentation.lambda_handler.RegistrationOrchestrator') as mock_orchestrator_class:
            
            mock_parser.return_value.parse_event.return_value = [
                {'bucket': 'test-bucket', 'key': 'audio-uploads/user123/sample1.wav', 'size': 1048576}
            ]
            
            mock_orchestrator = Mock()
            mock_orchestrator_class.return_value = mock_orchestrator
            
            # Mock async method to raise exception
            async def mock_process_fail(*args, **kwargs):
                raise ValueError("Audio quality validation failed")
            
            with patch('asyncio.run', side_effect=lambda coro: asyncio.get_event_loop().run_until_complete(coro)):
                mock_orchestrator.process_registration_audio = AsyncMock(side_effect=mock_process_fail)
                
                result = lambda_handler(mock_s3_event, mock_lambda_context)
                
                assert result['statusCode'] == 207  # Multi-Status
                body = json.loads(result['body'])
                assert body['failed_files'] == 1
                assert len(body['errors']) == 1
                assert 'Audio quality validation failed' in body['errors'][0]['error']
    
    def test_lambda_handler_exception(self, mock_lambda_context):
        """Test Lambda handler with unexpected exception."""
        
        with patch('presentation.lambda_handler.S3EventParser') as mock_parser:
            mock_parser.side_effect = Exception("Unexpected error")
            
            result = lambda_handler({}, mock_lambda_context)
            
            assert result['statusCode'] == 500
            body = json.loads(result['body'])
            assert 'Internal server error' in body['message']


# Backwards compatibility functions removed - no longer needed
# Clean Architecture handles all functionality through proper interfaces


@pytest.mark.integration
class TestHandlerIntegration:
    """Integration tests for Clean Architecture handler."""
    
    def test_handler_with_real_event_parser(self, mock_s3_event, mock_lambda_context):
        """Test handler with real S3EventParser using Clean Architecture."""
        
        with patch('presentation.lambda_handler.RegistrationOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator_class.return_value = mock_orchestrator
            
            async def mock_process(*args, **kwargs):
                return {
                    'bucket': 'test-voice-uploads',
                    'key': 'audio-uploads/user123/sample1.wav',
                    'user_id': 'user123',
                    'success': True,
                    'embedding_dimensions': 256,
                    'quality_score': 0.85,
                    'user_embedding_count': 1,
                    'registration_complete': False,
                    'processing_time_ms': 1500
                }
            
            with patch('asyncio.run', side_effect=lambda coro: asyncio.get_event_loop().run_until_complete(coro)):
                mock_orchestrator.process_registration_audio = AsyncMock(side_effect=mock_process)
                
                result = lambda_handler(mock_s3_event, mock_lambda_context)
                
                assert result['statusCode'] == 200
                body = json.loads(result['body'])
                assert body['processed_files'] == 1
                mock_orchestrator.process_registration_audio.assert_called_once()
    
    def test_handler_end_to_end_flow(self, mock_s3_event, mock_lambda_context):
        """Test end-to-end handler flow with Clean Architecture."""
        
        # Mock all Clean Architecture components
        with patch('presentation.lambda_handler.RegistrationOrchestrator') as mock_orchestrator_class, \
             patch('presentation.lambda_handler.S3EventParser') as mock_parser:
            
            # Setup event parser
            mock_parser.return_value.parse_event.return_value = [
                {'bucket': 'test-bucket', 'key': 'audio-uploads/user123/sample1.wav', 'size': 1048576}
            ]
            
            # Setup orchestrator
            mock_orchestrator = Mock()
            mock_orchestrator_class.return_value = mock_orchestrator
            
            async def mock_process(*args, **kwargs):
                return {
                    'bucket': 'test-bucket',
                    'key': 'audio-uploads/user123/sample1.wav',
                    'user_id': 'user123',
                    'success': True,
                    'embedding_dimensions': 256,
                    'quality_score': 0.85,
                    'user_embedding_count': 2,
                    'registration_complete': True,
                    'processing_time_ms': 2000,
                    'processing_stages': {
                        'extract_user_id': {'status': 'success'},
                        'voice_processing': {'status': 'success'},
                        'check_completion': {'status': 'success'}
                    }
                }
            
            with patch('asyncio.run', side_effect=lambda coro: asyncio.get_event_loop().run_until_complete(coro)):
                mock_orchestrator.process_registration_audio = AsyncMock(side_effect=mock_process)
                
                result = lambda_handler(mock_s3_event, mock_lambda_context)
                
                assert result['statusCode'] == 200
                body = json.loads(result['body'])
                assert body['processed_files'] == 1
                assert body['failed_files'] == 0
                
                # Verify the result structure matches expected format
                result_item = body['results'][0]
                assert result_item['success'] is True
                assert result_item['user_id'] == 'user123'
                assert result_item['registration_complete'] is True
                assert result_item['processing_time_ms'] == 2000
