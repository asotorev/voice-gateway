#!/usr/bin/env python3
"""
S3 Configuration Test Suite for Voice Gateway.
Validates S3 settings, URL generation, and configuration properties.
"""
import pytest

from app.core.services.audio_constraints import AudioConstraints


@pytest.mark.unit
def test_settings_loading(test_settings):
    """Test that infrastructure settings load correctly with S3 configuration."""
    assert test_settings.environment == "test"
    assert test_settings.aws_region == "us-east-1"
    assert test_settings.s3_bucket_name == "test-bucket"
    assert test_settings.audio_base_url == "s3://test-bucket/"


@pytest.mark.unit
def test_s3_properties(test_settings):
    """Test S3-related computed properties."""
    assert test_settings.use_local_s3 is True
    assert test_settings.s3_endpoint_url == "http://localhost:9000"
    assert test_settings.s3_use_ssl is False
    assert test_settings.s3_signature_version == "s3v4"


@pytest.mark.unit
def test_audio_properties(test_settings):
    """Test audio storage configuration properties."""
    assert AudioConstraints.ALLOWED_AUDIO_FORMATS == ["wav", "mp3", "m4a"]
    assert AudioConstraints.get_max_audio_file_size_bytes() == 10 * 1024 * 1024  # 10MB
    assert test_settings.audio_upload_expiration_minutes == 15
    assert test_settings.audio_download_expiration_minutes == 60


@pytest.mark.unit
def test_s3_config_generation(test_settings):
    """Test S3 configuration dictionary generation for boto3."""
    s3_config = test_settings.get_s3_config()
    
    assert s3_config["region_name"] == "us-east-1"
    assert s3_config["signature_version"] == "s3v4"
    assert s3_config["use_ssl"] is False
    assert s3_config["endpoint_url"] == "http://localhost:9000"
    assert s3_config["aws_access_key_id"] == "minioadmin"
    assert s3_config["aws_secret_access_key"] == "minioadmin"


@pytest.mark.unit
def test_audio_url_generation(test_settings):
    """Test audio URL generation from relative paths."""
    test_cases = [
        ("user123/sample1.wav", "s3://test-bucket/user123/sample1.wav"),
        ("user456/sample2.mp3", "s3://test-bucket/user456/sample2.mp3"),
        ("/user789/sample3.m4a", "s3://test-bucket/user789/sample3.m4a"),  # Leading slash
    ]
    
    for input_path, expected_url in test_cases:
        result = test_settings.get_full_audio_url(input_path)
        assert result == expected_url, f"Failed for input: {input_path}"


@pytest.mark.unit
def test_audio_url_edge_cases(test_settings):
    """Test edge cases for audio URL generation."""
    # Empty path should raise ValueError
    with pytest.raises(ValueError, match="Audio path cannot be empty"):
        test_settings.get_full_audio_url("")
    
    # None should raise error
    with pytest.raises((ValueError, TypeError)):
        test_settings.get_full_audio_url(None)


@pytest.mark.unit
def test_audio_format_validation(test_settings):
    """Test audio format configuration parsing."""
    formats = AudioConstraints.ALLOWED_AUDIO_FORMATS
    
    assert len(formats) == 3
    assert all(fmt in formats for fmt in ["wav", "mp3", "m4a"])
    assert all(isinstance(fmt, str) for fmt in formats)
    assert all(fmt.islower() for fmt in formats)


@pytest.mark.unit
def test_file_size_conversion(test_settings):
    """Test file size conversion from MB to bytes."""
    size_mb = AudioConstraints.MAX_AUDIO_FILE_SIZE_MB
    size_bytes = AudioConstraints.get_max_audio_file_size_bytes()
    
    assert size_mb == 10
    assert size_bytes == 10485760  # 10 * 1024 * 1024
    assert size_bytes == size_mb * 1024 * 1024


@pytest.mark.integration
def test_complete_s3_workflow(test_settings):
    """Integration test simulating complete S3 configuration workflow."""
    # 1. Verify settings are loaded
    assert test_settings.environment == "test"
    
    # 2. Generate S3 config
    s3_config = test_settings.get_s3_config()
    assert "endpoint_url" in s3_config
    
    # 3. Generate audio URL
    test_path = "integration_test/sample.wav"
    audio_url = test_settings.get_full_audio_url(test_path)
    assert audio_url.startswith(test_settings.audio_base_url)
    
    # 4. Validate format is allowed
    file_extension = test_path.split('.')[-1]
    assert file_extension in AudioConstraints.ALLOWED_AUDIO_FORMATS