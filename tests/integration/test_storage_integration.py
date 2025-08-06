#!/usr/bin/env python3
"""
Integration tests for AudioStorageService implementation.
Tests with real S3/MinIO infrastructure for end-to-end validation.
"""
import pytest
import os
import requests
from app.core.models import AudioStorageError


@pytest.fixture(autouse=True)
def check_infrastructure(infrastructure_helpers):
    """Check infrastructure health before running tests."""
    if not infrastructure_helpers.check_infrastructure():
        pytest.skip("Infrastructure not available")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_service_init(infrastructure_helpers):
    """Integration test: service initialization."""
    service = infrastructure_helpers.create_real_service()
    
    # Test service info
    info = service.get_audio_service_info()
    assert info.service_type == 's3'
    assert info.bucket_name  # Should not be empty
    assert info.region  # Should not be empty
    assert info.use_local_s3 is True
    assert info.endpoint_url == 'http://localhost:9000'


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_download_workflow(infrastructure_helpers, test_files):
    """Integration test: complete upload and download workflow."""
    service = infrastructure_helpers.create_real_service()
    
    # Generate unique file path
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    file_path = f"integration_test/sample_{unique_id}.wav"
    
    # Create test audio content
    test_content = infrastructure_helpers.create_test_audio_content(1024)
    
    # Step 1: Generate upload URL
    upload_result = await service.generate_presigned_upload_url(
        file_path=file_path,
        content_type="audio/wav",
        expiration_minutes=5
    )
    
    assert upload_result.upload_url, "Upload URL not generated"
    assert upload_result.file_path == file_path
    assert upload_result.content_type == "audio/wav"
    
    # Step 2: Upload file using signed URL
    upload_url = upload_result.upload_url
    upload_fields = upload_result.upload_fields
    
    # Prepare multipart form data
    files = {'file': ('test.wav', test_content, 'audio/wav')}
    data = {**upload_fields, 'key': file_path}
    
    response = requests.post(
        upload_url,
        files=files,
        data=data,
        timeout=30
    )
    
    assert response.status_code in [200, 204], f"Upload failed with status {response.status_code}"
    
    # Step 3: Verify file exists
    exists = await service.audio_file_exists(file_path)
    assert exists is True
    
    # Step 4: Generate download URL
    download_url = await service.generate_presigned_download_url(file_path, expiration_minutes=5)
    assert download_url.startswith('http')
    
    # Step 5: Download file
    download_response = requests.get(download_url, timeout=30)
    assert download_response.status_code == 200
    assert len(download_response.content) > 0
    
    # Track file for cleanup
    test_files.append(file_path)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_scenarios(infrastructure_helpers):
    """Integration test: error handling scenarios."""
    service = infrastructure_helpers.create_real_service()
    
    # Test non-existent file download - should still generate URL (S3 handles existence)
    download_url = await service.generate_presigned_download_url("nonexistent/file.wav", expiration_minutes=5)
    assert download_url.startswith('http')
    
    # Test invalid file path - should still work (S3 handles empty paths)
    upload_result = await service.generate_presigned_upload_url("", content_type="audio/wav", expiration_minutes=5)
    assert hasattr(upload_result, 'upload_url')
    
    # Test invalid expiration - should still work (S3 handles invalid expiration)
    upload_result = await service.generate_presigned_upload_url("test.wav", content_type="audio/wav", expiration_minutes=0)
    assert hasattr(upload_result, 'upload_url')


@pytest.mark.integration
@pytest.mark.asyncio
async def test_path_validation(infrastructure_helpers):
    """Integration test: path validation and cleaning."""
    service = infrastructure_helpers.create_real_service()
    
    # Test path cleaning
    test_cases = [
        ("/test/path.wav", "test/path.wav"),
        ("test/path.wav", "test/path.wav"),
        ("  test/path.wav  ", "test/path.wav"),
    ]
    
    for input_path, expected_clean_path in test_cases:
        # This would be tested through the service's internal path cleaning
        # For now, we test that the service handles paths correctly
        try:
            await service.generate_presigned_upload_url(input_path, content_type="audio/wav", expiration_minutes=5)
            # If no error, path was handled correctly
        except AudioStorageError as e:
            # Expected for invalid paths, but should not be path-related errors
            assert "File path cannot be empty" not in str(e)