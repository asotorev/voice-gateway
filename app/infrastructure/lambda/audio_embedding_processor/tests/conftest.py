"""
Test configuration and fixtures for Lambda audio processing pipeline.

This module provides pytest fixtures and configuration for testing the
Lambda function components, including mocked AWS services and test data.
"""
import os
import sys
import pytest
import json
from typing import Dict, Any, List
from unittest.mock import Mock
from datetime import datetime, timezone

# Configure PYTHONPATH to include shared layer for testing
shared_layer_path = os.path.join(os.path.dirname(__file__), '../../shared_layer/python')
if os.path.exists(shared_layer_path) and shared_layer_path not in sys.path:
    sys.path.insert(0, shared_layer_path)
    print(f"Added shared layer to PYTHONPATH for testing: {shared_layer_path}")



# Set test environment variables
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['EMBEDDING_PROCESSOR_TYPE'] = 'mock'
os.environ['MAX_AUDIO_FILE_SIZE_MB'] = '10'
os.environ['SUPPORTED_AUDIO_FORMATS'] = 'wav,mp3,m4a,flac'
os.environ['REQUIRED_AUDIO_SAMPLES'] = '3'
os.environ['MIN_VOICE_QUALITY_SCORE'] = '0.7'
os.environ['S3_BUCKET_NAME'] = 'test-voice-uploads'
os.environ['USERS_TABLE_NAME'] = 'UsersTest'
os.environ['VOICE_EMBEDDING_DIMENSIONS'] = '256'


@pytest.fixture
def mock_s3_event():
    """Sample S3 event for testing."""
    return {
        'Records': [
            {
                'eventVersion': '2.1',
                'eventSource': 'aws:s3',
                'eventName': 'ObjectCreated:Put',
                'eventTime': '2024-01-15T10:30:00.000Z',
                's3': {
                    'bucket': {'name': 'test-voice-uploads'},
                    'object': {
                        'key': 'audio-uploads/user123/sample1.wav',
                        'size': 1048576
                    }
                }
            }
        ]
    }


@pytest.fixture
def mock_lambda_context():
    """Mock Lambda context for testing."""
    context = Mock()
    context.function_name = 'audio-embedding-processor'
    context.aws_request_id = 'test-request-id-123'
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:audio-embedding-processor'
    context.get_remaining_time_in_millis.return_value = 30000
    return context


@pytest.fixture
def sample_audio_data():
    """Sample audio data for testing."""
    # Create fake WAV header + some data
    wav_header = b'RIFF' + (1024).to_bytes(4, 'little') + b'WAVE'
    wav_header += b'fmt ' + (16).to_bytes(4, 'little')
    wav_header += (1).to_bytes(2, 'little')  # PCM format
    wav_header += (1).to_bytes(2, 'little')  # mono
    wav_header += (44100).to_bytes(4, 'little')  # sample rate
    wav_header += (88200).to_bytes(4, 'little')  # byte rate
    wav_header += (2).to_bytes(2, 'little')  # block align
    wav_header += (16).to_bytes(2, 'little')  # bits per sample
    wav_header += b'data' + (1000).to_bytes(4, 'little')
    
    # Add some fake audio data
    audio_data = wav_header + b'\x00' * 1000
    return audio_data


@pytest.fixture
def sample_file_metadata():
    """Sample file metadata for testing."""
    return {
        'file_name': 'sample1.wav',
        'size_bytes': 1048576,
        'content_type': 'audio/wav',
        'uploaded_at': datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def mock_user_data():
    """Sample user data for testing."""
    return {
        'user_id': 'user123',
        'email': 'user@example.com',
        'registration_complete': False,
        'voice_embeddings': [
            {
                'audio_path': 'user123/sample1.wav',
                'embedding': [0.1] * 256,
                'generated_at': '2024-01-15T10:30:00.000Z',
                'audio_metadata': {
                    'quality_score': 0.85,
                    'file_name': 'sample1.wav',
                    'file_size': 1048576
                }
            }
        ],
        'created_at': '2024-01-15T10:00:00.000Z',
        'updated_at': '2024-01-15T10:30:00.000Z'
    }


@pytest.fixture
def mock_s3_client():
    """Mock S3 client for testing."""
    mock_client = Mock()
    
    # Mock successful download
    mock_client.download_fileobj.return_value = None
    
    # Create proper mock response with correct types
    def mock_head_object(*args, **kwargs):
        return {
            'ContentLength': 1048576,  # Always return int
            'ContentType': 'audio/wav',
            'LastModified': datetime.now(timezone.utc)  # Always return datetime
        }
    
    mock_client.head_object.side_effect = mock_head_object
    
    return mock_client


@pytest.fixture
def mock_dynamodb_client():
    """Mock DynamoDB client for testing."""
    mock_client = Mock()
    
    # Mock successful operations
    mock_client.get_item.return_value = {
        'Item': {
            'user_id': {'S': 'user123'},
            'email': {'S': 'user@example.com'},
            'registration_complete': {'BOOL': False},
            'voice_embeddings': {'L': []},
            'created_at': {'S': '2024-01-15T10:00:00.000Z'}
        }
    }
    
    mock_client.update_item.return_value = {'Attributes': {}}
    
    return mock_client


@pytest.fixture
def mock_embedding_result():
    """Sample embedding result for testing."""
    return {
        'embedding': [0.1] * 256,
        'quality_assessment': {
            'overall_quality_score': 0.85,
            'snr_estimate': 25.5,
            'voice_activity_ratio': 0.92,
            'background_noise_level': 0.05,
            'quality_issues': []
        },
        'processor_info': {
            'processor_type': 'mock',
            'processor_name': 'MockAudioProcessor',
            'processor_version': 'mock-1.0.0',
            'processing_time_ms': 150
        },
        'audio_analysis': {
            'duration_seconds': 3.5,
            'sample_rate': 44100,
            'channels': 1,
            'format': 'wav'
        }
    }


@pytest.fixture
def mock_completion_result():
    """Sample completion check result for testing."""
    return {
        'is_complete': False,
        'completion_confidence': 0.65,
        'registration_score': 75.2,
        'embedding_count': 2,
        'required_samples': 3,
        'samples_remaining': 1,
        'completion_percentage': 66.7,
        'status_analysis': 'in_progress',
        'recommendations': ['Upload 1 more audio sample'],
        'quality_analysis': {
            'average_quality': 0.82,
            'quality_trend': 'stable'
        }
    }


@pytest.fixture(scope="function")
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset any global instances that might carry state between tests
    yield
    # Cleanup code would go here if needed


class MockBotoClient:
    """Mock boto3 client for testing."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._responses = {}
    
    def set_response(self, method: str, response: Dict[str, Any]):
        """Set mock response for a method."""
        self._responses[method] = response
    
    def __getattr__(self, name: str):
        """Return mock response for any method call."""
        if name in self._responses:
            return lambda **kwargs: self._responses[name]
        return Mock()


@pytest.fixture
def mock_boto_session():
    """Mock boto3 session for testing."""
    session = Mock()
    session.client.side_effect = lambda service: MockBotoClient(service)
    return session


# Test markers for organizing test runs
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.aws = pytest.mark.aws


def create_mock_getenv(processor_type='mock', dimensions='256'):
    """
    Helper function to create mock getenv for testing audio processor configuration.
    
    Args:
        processor_type: Type of processor to mock ('mock', 'resemblyzer', etc.)
        dimensions: Number of embedding dimensions as string
        
    Returns:
        Function that can be used as side_effect for os.getenv mock
    """
    def mock_getenv(key, default=None):
        if key == 'EMBEDDING_PROCESSOR_TYPE':
            return processor_type
        elif key == 'VOICE_EMBEDDING_DIMENSIONS':
            return dimensions
        return default
    return mock_getenv


def create_pipeline_mocks():
    """
    Helper function to create all pipeline mocks in one place.
    
    Returns:
        Dict with all pipeline mock objects
    """
    mocks = {
        's3_operations': Mock(),
        'dynamodb_operations': Mock(),
        'process_audio_file': Mock(),
        'audio_file_validator': Mock(),
        'completion_checker': Mock(),
        'user_status_manager': Mock(),
        'notification_handler': Mock()
    }
    
    return mocks


def create_handler_mocks():
    """
    Helper function to create all handler mocks in one place.
    
    Returns:
        Dict with all handler mock objects
    """
    mocks = {
        'S3EventParser': Mock(),
        'process_single_audio_file': Mock(),
        'extract_user_id_from_key': Mock(),
        'AudioProcessingPipeline': Mock()
    }
    
    return mocks


def create_s3_client_mock():
    """
    Helper function to create a properly configured S3 client mock.
    
    Returns:
        Mock S3 client with common configurations
    """
    mock_client = Mock()
    
    # Default head_object response
    mock_client.head_object.return_value = {
        'ContentLength': 1048576,
        'ContentType': 'audio/wav',
        'LastModified': datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        'ETag': '"abc123"'
    }
    
    # Default get_object response with proper mock body
    mock_body = Mock()
    mock_body.read.return_value = b'fake_audio_data'
    mock_client.get_object.return_value = {
        'Body': mock_body,
        'ContentType': 'audio/wav'
    }
    
    return mock_client


def create_resemblyzer_mocks():
    """
    Helper function to create Resemblyzer-related mocks.
    
    Returns:
        Dict with Resemblyzer mock objects
    """
    mocks = {
        'VoiceEncoder': Mock(),
        'preprocess_wav': Mock(),
        'librosa': Mock(),
        'soundfile': Mock()
    }
    
    return mocks
