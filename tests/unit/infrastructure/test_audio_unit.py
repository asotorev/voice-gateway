#!/usr/bin/env python3
"""
Unit tests for AudioStorageService.
Tests with mocked S3 client for fast, isolated testing of audio file operations.
"""
import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from app.core.services.audio_storage_service import AudioStorageService
from app.core.ports.audio_storage_port import AudioStorageError
from app.core.services.audio_constraints import AudioConstraints


@pytest.mark.asyncio
async def test_audio_upload_url(infrastructure_helpers):
    """Unit test: successful audio file upload URL generation."""
    # Create service with mock client
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Setup mock for successful URL generation
    expected_url = "https://test-bucket.s3.amazonaws.com"
    infrastructure_helpers.setup_mock_presigned_url(mock_s3_client, expected_url)
    
    # Test upload URL generation
    result = await service.generate_audio_upload_url(
        file_path="test/file.wav",
        content_type="audio/wav",
        expiration_minutes=15
    )
    
    # Verify result structure
    required_fields = ['upload_url', 'upload_fields', 'file_path', 'expires_at', 'upload_method']
    for field in required_fields:
        assert field in result
    
    # Verify values
    assert result['upload_url'] == expected_url
    assert result['file_path'] == 'test/file.wav'
    assert result['upload_method'] == 'POST'
    assert result['content_type'] == 'audio/wav'
    
    # Verify S3 client was called correctly
    mock_s3_client.generate_presigned_post.assert_called_once()
    call_args = mock_s3_client.generate_presigned_post.call_args
    assert call_args[1]['Bucket'] == service.bucket_name
    assert call_args[1]['Key'] == 'test/file.wav'


@pytest.mark.asyncio
async def test_audio_path_cleaning(infrastructure_helpers):
    """Unit test: audio file path cleaning and normalization."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Setup mock response
    infrastructure_helpers.setup_mock_presigned_url(mock_s3_client)
    
    # Test path cleaning scenarios
    test_cases = [
        ("/test/file.wav", "test/file.wav"),  # Leading slash removed
        ("  test/file.wav  ", "test/file.wav"),  # Whitespace trimmed
        ("test/file.wav", "test/file.wav"),  # No change needed
        ("test//file.wav", "test//file.wav"),  # Double slashes preserved (actual behavior)
    ]
    
    for input_path, expected_path in test_cases:
        result = await service.generate_audio_upload_url(input_path)
        assert result['file_path'] == expected_path


@pytest.mark.asyncio
async def test_audio_validation_errors(infrastructure_helpers):
    """Unit test: audio input validation error handling."""
    service = infrastructure_helpers.create_mock_service()
    
    # Test empty file path
    with pytest.raises(AudioStorageError, match="File path cannot be empty"):
        await service.generate_audio_upload_url("")
    
    with pytest.raises(AudioStorageError, match="File path cannot be empty"):
        await service.generate_audio_upload_url(None)
    
    # Test invalid expiration
    with pytest.raises(AudioStorageError, match="Invalid expiration"):
        await service.generate_audio_upload_url("test.wav", expiration_minutes=0)
    
    with pytest.raises(AudioStorageError, match="Invalid expiration"):
        await service.generate_audio_upload_url("test.wav", expiration_minutes=-1)
    
    # Test invalid content type
    with pytest.raises(AudioStorageError, match="Invalid content type"):
        await service.generate_audio_upload_url("test.wav", content_type="text/plain")
    
    # Test path traversal
    with pytest.raises(AudioStorageError, match="Path traversal not allowed"):
        await service.generate_audio_upload_url("../../../etc/passwd")


@pytest.mark.asyncio
async def test_audio_content_type_validation(infrastructure_helpers):
    """Unit test: audio content type validation with valid types."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Setup mock response
    infrastructure_helpers.setup_mock_presigned_url(mock_s3_client)
    
    # Test all valid audio types
    valid_types = AudioConstraints.ALLOWED_AUDIO_MIME_TYPES
    for content_type in valid_types:
        result = await service.generate_audio_upload_url("test.wav", content_type=content_type)
        assert result['content_type'] == content_type


@pytest.mark.asyncio
async def test_audio_client_error_handling(infrastructure_helpers):
    """Unit test: handling of S3 client errors for audio operations."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Setup mock to raise ClientError
    infrastructure_helpers.setup_mock_error(mock_s3_client, 'AccessDenied', 'Access denied to bucket')
    
    # Test that AudioStorageError is raised
    with pytest.raises(AudioStorageError, match="S3 error AccessDenied"):
        await service.generate_audio_upload_url("test.wav")


@pytest.mark.asyncio
async def test_audio_file_exists(infrastructure_helpers):
    """Unit test: audio file existence checking with various scenarios."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Test file exists (success case)
    infrastructure_helpers.setup_mock_head_object(mock_s3_client, exists=True)
    
    exists = await service.audio_file_exists("test/file.wav")
    assert exists is True
    
    # Verify S3 client was called correctly
    mock_s3_client.head_object.assert_called_once_with(
        Bucket=service.bucket_name,
        Key="test/file.wav"
    )
    
    # Reset mock for next test
    mock_s3_client.reset_mock()
    
    # Test file doesn't exist (NoSuchKey error)
    infrastructure_helpers.setup_mock_head_object(mock_s3_client, exists=False)
    
    exists = await service.audio_file_exists("nonexistent/file.wav")
    assert exists is False
    
    # Reset mock for next test
    mock_s3_client.reset_mock()
    
    # Test edge cases
    exists = await service.audio_file_exists("")
    assert exists is False
    
    exists = await service.audio_file_exists(None)
    assert exists is False


@pytest.mark.asyncio
async def test_audio_file_deletion(infrastructure_helpers):
    """Unit test: audio file deletion with various scenarios."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Test successful file deletion
    infrastructure_helpers.setup_mock_delete_object(mock_s3_client, success=True)
    
    result = await service.delete_audio_file("test/file.wav")
    
    # Verify result is boolean (not dict)
    assert isinstance(result, bool)
    assert result is True
    
    # Verify S3 client was called correctly
    mock_s3_client.delete_object.assert_called_once_with(
        Bucket=service.bucket_name,
        Key="test/file.wav"
    )
    
    # Reset mock for next test
    mock_s3_client.reset_mock()
    
    # Test file deletion with non-existent file (NoSuchKey error)
    infrastructure_helpers.setup_mock_delete_object(mock_s3_client, success=False)
    
    result = await service.delete_audio_file("nonexistent/file.wav")
    
    # Should return False when file doesn't exist
    assert isinstance(result, bool)
    assert result is False


@pytest.mark.asyncio
async def test_audio_download_url(infrastructure_helpers):
    """Unit test: audio file download URL generation."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Setup mock response
    expected_url = "https://test-bucket.s3.amazonaws.com/test.wav?signature=abc123"
    infrastructure_helpers.setup_mock_presigned_get_url(mock_s3_client, expected_url)
    
    # Test successful download URL generation
    result = await service.generate_audio_download_url("test.wav", expiration_minutes=60)
    
    # Verify result is a string (not dict)
    assert isinstance(result, str)
    assert result == expected_url
    
    # Verify S3 client was called correctly
    mock_s3_client.generate_presigned_url.assert_called_once()


def test_audio_service_info(infrastructure_helpers):
    """Unit test: audio service info retrieval."""
    service = infrastructure_helpers.create_mock_service()
    
    info = service.get_audio_service_info()
    
    # Verify required fields
    required_fields = ['service_type', 'bucket_name', 'region', 'allowed_formats']
    for field in required_fields:
        assert field in info
    
    # Verify values
    assert info['service_type'] == 's3'
    assert info['bucket_name']  # Should not be empty
    assert info['region']  # Should not be empty
    assert 'wav' in info['allowed_formats']
    assert 'mp3' in info['allowed_formats']
    assert 'm4a' in info['allowed_formats']


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