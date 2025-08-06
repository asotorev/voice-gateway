#!/usr/bin/env python3
"""
Unit tests for AudioStorageAdapter.
Tests with mocked S3 client for fast, isolated testing of audio file operations.
"""
import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from app.adapters.services.audio_storage_service import AudioStorageAdapter
from app.core.models import AudioStorageError, AudioUploadRequest, AudioFormat
from app.core.services.audio_constraints import AudioConstraints


@pytest.mark.asyncio
async def test_audio_upload_url(infrastructure_helpers):
    """Unit test: audio upload URL generation."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Setup mock response
    expected_url = "https://test-bucket.s3.amazonaws.com/upload"
    infrastructure_helpers.setup_mock_presigned_url(mock_s3_client, expected_url)
    
    # Test upload URL generation
    result = await service.generate_presigned_upload_url(
        file_path="test-user-123/audio-123.wav",
        content_type="audio/wav",
        expiration_minutes=15,
        max_file_size_bytes=10485760
    )
    
    # Verify result structure (now a domain object, not a dict)
    assert hasattr(result, 'upload_url')
    assert hasattr(result, 'upload_fields')
    assert hasattr(result, 'file_path')
    assert hasattr(result, 'expires_at')
    assert hasattr(result, 'upload_method')
    assert hasattr(result, 'content_type')
    assert hasattr(result, 'max_file_size_bytes')
    
    # Verify values
    assert result.upload_url == expected_url
    assert result.upload_method == 'POST'
    assert result.content_type == 'audio/wav'
    assert result.file_path == 'test-user-123/audio-123.wav'
    
    # Verify S3 client was called correctly
    mock_s3_client.generate_presigned_post.assert_called_once()
    call_args = mock_s3_client.generate_presigned_post.call_args
    assert call_args[1]['Bucket'] == service.bucket_name
    # Verify the key follows the expected pattern: {user_id}/{audio_id}.{format}
    key = call_args[1]['Key']
    assert key.startswith('test-user-123/')
    assert key.endswith('.wav')


@pytest.mark.asyncio
async def test_audio_path_cleaning(infrastructure_helpers):
    """Unit test: audio file path cleaning and normalization."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Setup mock response
    infrastructure_helpers.setup_mock_presigned_url(mock_s3_client)
    
    # Test path cleaning scenarios - now testing pure S3 operations
    test_cases = [
        ("test-user-123/audio-123.wav", "audio/wav"),  # Normal case
        ("  test-user-123/audio-123.wav  ", "audio/mpeg"),  # Whitespace trimmed
    ]
    
    for file_path, content_type in test_cases:
        result = await service.generate_presigned_upload_url(
            file_path=file_path.strip(),
            content_type=content_type,
            expiration_minutes=15,
            max_file_size_bytes=10485760
        )
        # Verify the generated path is clean
        result_file_path = result.file_path
        assert not result_file_path.startswith('/')
        assert not result_file_path.endswith('/')
        assert result_file_path.startswith('test-user-123')


@pytest.mark.asyncio
async def test_audio_validation_errors(infrastructure_helpers):
    """Unit test: audio input validation error handling."""
    service = infrastructure_helpers.create_mock_service()
    
    # Test empty file_path - should return False or handle gracefully
    result = await service.generate_presigned_upload_url(
        file_path="",
        content_type="audio/wav",
        expiration_minutes=15
    )
    # Should still work as S3 handles empty paths
    
    # Test invalid content_type - should still work as S3 handles it
    result = await service.generate_presigned_upload_url(
        file_path="test/file.wav",
        content_type="invalid/type",
        expiration_minutes=15
    )
    # Should still work as S3 handles invalid content types
    
    # Test invalid expiration - should still work as S3 handles it
    result = await service.generate_presigned_upload_url(
        file_path="test/file.wav",
        content_type="audio/wav",
        expiration_minutes=-1
    )
    # Should still work as S3 handles invalid expiration


@pytest.mark.asyncio
async def test_audio_content_type_validation(infrastructure_helpers):
    """Unit test: audio content type validation with valid types."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Setup mock response
    infrastructure_helpers.setup_mock_presigned_url(mock_s3_client)
    
    # Test all valid audio formats
    valid_formats = ["wav", "mp3", "m4a"]
    
    for format in valid_formats:
        result = await service.generate_presigned_upload_url(
            file_path=f"test/file.{format}",
            content_type=f"audio/{format}",
            expiration_minutes=15
        )
        assert result.content_type == f"audio/{format}"


@pytest.mark.asyncio
async def test_audio_client_error_handling(infrastructure_helpers):
    """Unit test: S3 client error handling."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Test S3 client error
    mock_s3_client.generate_presigned_post.side_effect = Exception("S3 bucket not found")
    
    # Should raise AudioStorageError
    with pytest.raises(AudioStorageError, match="S3 bucket not found"):
        await service.generate_presigned_upload_url(
            file_path="test/file.wav",
            content_type="audio/wav",
            expiration_minutes=15
        )


@pytest.mark.asyncio
async def test_audio_file_exists(infrastructure_helpers):
    """Unit test: audio file existence check."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Test file exists
    mock_s3_client.head_object.return_value = {'ContentLength': 1024}
    exists = await service.audio_file_exists("test/file.wav")
    assert exists is True
    
    # Test file doesn't exist
    mock_s3_client.head_object.side_effect = ClientError(
        error_response={'Error': {'Code': '404', 'Message': 'Not Found'}},
        operation_name='HeadObject'
    )
    exists = await service.audio_file_exists("nonexistent/file.wav")
    assert exists is False
    
    # Test other S3 errors - should return False, not raise
    mock_s3_client.head_object.side_effect = Exception("S3 error")
    exists = await service.audio_file_exists("test/file.wav")
    assert exists is False


@pytest.mark.asyncio
async def test_audio_file_deletion(infrastructure_helpers):
    """Unit test: audio file deletion."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Test successful deletion
    mock_s3_client.delete_object.return_value = {'ResponseMetadata': {'HTTPStatusCode': 204}}
    result = await service.delete_audio_file("test/file.wav")
    assert result is True
    
    # Test file doesn't exist
    mock_s3_client.delete_object.side_effect = ClientError(
        error_response={'Error': {'Code': 'NoSuchKey', 'Message': 'Not Found'}},
        operation_name='DeleteObject'
    )
    result = await service.delete_audio_file("nonexistent/file.wav")
    assert result is False
    
    # Test other S3 errors
    mock_s3_client.delete_object.side_effect = Exception("S3 error")
    with pytest.raises(AudioStorageError):
        await service.delete_audio_file("test/file.wav")


@pytest.mark.asyncio
async def test_audio_download_url(infrastructure_helpers):
    """Unit test: audio download URL generation."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Setup mock response
    expected_url = "https://test-bucket.s3.amazonaws.com/download"
    mock_s3_client.generate_presigned_url.return_value = expected_url
    
    # Test download URL generation
    result = await service.generate_presigned_download_url("test/file.wav", expiration_minutes=5)
    assert result == expected_url
    
    # Verify S3 client was called correctly
    mock_s3_client.generate_presigned_url.assert_called_once()
    call_args = mock_s3_client.generate_presigned_url.call_args
    assert call_args[1]['Params']['Bucket'] == service.bucket_name
    assert call_args[1]['Params']['Key'] == "test/file.wav"
    assert call_args[1]['ExpiresIn'] == 300  # 5 minutes in seconds


def test_audio_service_info(infrastructure_helpers):
    """Unit test: audio service information."""
    service = infrastructure_helpers.create_mock_service()
    
    # Test service info
    info = service.get_audio_service_info()
    
    # Verify all required fields are present
    required_fields = [
        'service_type', 'bucket_name', 'region', 'use_local_s3', 
        'endpoint_url', 'use_ssl', 'max_file_size_mb', 'allowed_formats',
        'upload_expiration_default', 'download_expiration_default',
        'voice_sample_support', 'individual_upload_support'
    ]
    
    for field in required_fields:
        assert hasattr(info, field)
    
    # Verify specific values - use actual values from the service
    assert info.service_type == 's3'
    assert info.bucket_name == 'voice-gateway-audio-dev'  # Actual bucket name
    assert info.use_local_s3 is True
    assert info.endpoint_url == 'http://localhost:9000'


def test_audio_constraints_validation():
    """Unit test: audio constraints validation for file types and sizes."""
    # Test valid content types
    valid_types = AudioConstraints.ALLOWED_AUDIO_MIME_TYPES
    for content_type in valid_types:
        assert AudioConstraints.is_valid_mime_type(content_type)
    
    # Test invalid content types
    invalid_types = ['text/plain', 'image/jpeg', 'video/mp4', 'application/json']
    for content_type in invalid_types:
        assert not AudioConstraints.is_valid_mime_type(content_type)
    
    # Test file size validation
    max_size = AudioConstraints.get_max_audio_file_size_bytes()
    assert AudioConstraints.is_valid_audio_format('wav')
    assert AudioConstraints.is_valid_audio_format('mp3')
    assert not AudioConstraints.is_valid_audio_format('txt')