"""
Pytest configuration and fixtures for Voice Authentication Processor tests.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

# Test fixtures
@pytest.fixture
def mock_s3_event():
    """Mock S3 event for testing."""
    return {
        'bucket': 'test-bucket',
        'key': 'voice-auth/user123/auth_request.wav',
        'size': 1024000,
        'etag': 'test-etag',
        'event_name': 's3:ObjectCreated:Put',
        'timestamp': '2023-01-01T00:00:00.000Z'
    }

@pytest.fixture
def mock_user_data():
    """Mock user data for testing."""
    return {
        'user_id': 'user123',
        'email': 'test@example.com',
        'password_hash': 'abcdef123456789',
        'voice_embeddings': [
            {
                'embedding': [0.1] * 256,
                'quality_score': 0.95,
                'created_at': '2023-01-01T00:00:00.000Z'
            }
        ],
        'registration_complete': True
    }

@pytest.fixture
def mock_audio_data():
    """Mock audio data for testing."""
    return b'fake_audio_data' * 1000

@pytest.fixture
def mock_transcription_result():
    """Mock Whisper transcription result."""
    return {
        'text': 'gato luna sol',
        'confidence': 0.95,
        'language': 'es',
        'processing_time_ms': 150
    }

@pytest.fixture
def mock_auth_result():
    """Mock authentication result."""
    return {
        'authentication_successful': True,
        'confidence_score': 0.85,
        'authentication_result': 'authenticated',
        'similarity_analysis': {
            'average_similarity': 0.82,
            'max_similarity': 0.88,
            'total_comparisons': 3
        },
        'user_embeddings_count': 3
    }

@pytest.fixture
def mock_dependencies():
    """Mock all dependencies for testing."""
    deps = Mock()
    deps.audio_processor = Mock()
    deps.storage_service = Mock()
    deps.user_repository = Mock()
    deps.authenticate_voice_use_case = Mock()
    
    # Setup async methods
    deps.storage_service.download_file = AsyncMock()
    deps.storage_service.extract_user_id_from_path = Mock(return_value='user123')
    deps.storage_service.get_file_metadata = Mock(return_value={})
    
    deps.user_repository.get_user = AsyncMock()
    deps.authenticate_voice_use_case.execute_from_file = AsyncMock()
    
    return deps

@pytest.fixture
def lambda_context():
    """Mock Lambda context for testing."""
    context = Mock()
    context.aws_request_id = 'test-request-id'
    context.function_name = 'voice-auth-processor'
    context.function_version = '1'
    context.get_remaining_time_in_millis = Mock(return_value=30000)
    return context
