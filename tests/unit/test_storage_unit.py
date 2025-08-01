#!/usr/bin/env python3
"""
Unit tests for AudioStorageService implementation.
Tests with mocked S3 client for fast, isolated testing.
"""
import pytest

from app.core.ports.storage_service import StorageError
from app.infrastructure.config.infrastructure_settings import infra_settings
from app.core.services.audio_constraints import AudioConstraints


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_url_success(infrastructure_helpers):
    """Unit test: successful upload URL generation."""
    # Create service with mock client
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Setup mock for successful URL generation
    expected_url = "https://test-bucket.s3.amazonaws.com"
    infrastructure_helpers.setup_mock_presigned_url(mock_s3_client, expected_url)
    
    # Test upload URL generation
    result = await service.generate_upload_url("user123/sample1.wav")
    
    # Verify result structure
    assert 'upload_url' in result
    assert 'file_path' in result
    assert 'upload_method' in result
    assert 'content_type' in result
    assert 'upload_fields' in result
    assert 'expires_at' in result
    assert 'max_file_size_bytes' in result
    
    # Verify values
    assert result['upload_url'] == expected_url
    assert result['file_path'] == "user123/sample1.wav"
    assert result['upload_method'] == "POST"
    assert result['content_type'] == "audio/wav"
    assert isinstance(result['upload_fields'], dict)
    assert isinstance(result['expires_at'], str)
    assert result['max_file_size_bytes'] > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validation_errors(infrastructure_helpers):
    """Unit test: validation error scenarios."""
    # Create service with mock client
    service = infrastructure_helpers.create_mock_service()
    
    # Test empty file path
    with pytest.raises(StorageError, match="File path cannot be empty"):
        await service.generate_upload_url("")
    
    # Test None file path
    with pytest.raises(StorageError, match="File path cannot be empty"):
        await service.generate_upload_url(None)
    
    # Test invalid expiration
    with pytest.raises(StorageError, match="Invalid expiration"):
        await service.generate_upload_url("test.wav", expiration_minutes=0)
    
    # Test negative expiration
    with pytest.raises(StorageError, match="Invalid expiration"):
        await service.generate_upload_url("test.wav", expiration_minutes=-1)
    
    # Test access denied error
    mock_s3_client = service.s3_client
    infrastructure_helpers.setup_mock_error(mock_s3_client, 'AccessDenied', 'Access denied to bucket')
    
    with pytest.raises(StorageError, match="Access denied"):
        await service.generate_upload_url("test.wav")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_content_type_validation(infrastructure_helpers):
    """Unit test: content type validation against settings."""
    # Create service with mock client
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Setup mock for successful URL generation
    infrastructure_helpers.setup_mock_presigned_url(mock_s3_client)
    
    # Test valid content types from AudioConstraints
    valid_types = AudioConstraints.ALLOWED_AUDIO_MIME_TYPES
    for content_type in valid_types:
        result = await service.generate_upload_url(
            "test.wav",
            content_type=content_type
        )
        assert result['content_type'] == content_type


@pytest.mark.unit
def test_file_size_validation(infrastructure_helpers):
    """Unit test: file size validation."""
    service = infrastructure_helpers.create_mock_service()
    
    # Test valid file sizes
    max_size = AudioConstraints.get_max_audio_file_size_bytes()
    valid_sizes = [1, 1024, 1024*1024, max_size]
    for size in valid_sizes:
        service._validate_audio_file_size(size, "test")  # Should not raise
    
    # Test invalid file sizes
    invalid_sizes = [0, -1, max_size + 1]
    for size in invalid_sizes:
        with pytest.raises(StorageError, match="Audio file size"):
            service._validate_audio_file_size(size, "test")


@pytest.mark.unit
def test_audio_constraints_validation():
    """Unit test: AudioConstraints validation."""
    
    # Test that AudioConstraints has valid values
    assert len(AudioConstraints.ALLOWED_AUDIO_FORMATS) > 0, "Audio formats list should not be empty"
    assert len(AudioConstraints.ALLOWED_AUDIO_MIME_TYPES) > 0, "MIME types list should not be empty"
    assert AudioConstraints.MAX_AUDIO_FILE_SIZE_MB > 0, "Max file size should be positive"
    
    # Test that all formats are valid
    for format in AudioConstraints.ALLOWED_AUDIO_FORMATS:
        assert AudioConstraints.is_valid_audio_format(format), f"Format {format} should be valid"
    
    # Test that all MIME types are valid
    for mime_type in AudioConstraints.ALLOWED_AUDIO_MIME_TYPES:
        assert AudioConstraints.is_valid_mime_type(mime_type), f"MIME type {mime_type} should be valid"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_file_exists(infrastructure_helpers):
    """Unit test: file existence checking."""
    service = infrastructure_helpers.create_mock_service()
    mock_s3_client = service.s3_client
    
    # Test file exists
    infrastructure_helpers.setup_mock_head_object(mock_s3_client, exists=True)
    exists = await service.file_exists("test.wav")
    assert exists is True
    
    # Test file doesn't exist
    infrastructure_helpers.setup_mock_head_object(mock_s3_client, exists=False)
    exists = await service.file_exists("nonexistent.wav")
    assert exists is False
    
    # Test empty path
    exists = await service.file_exists("")
    assert exists is False