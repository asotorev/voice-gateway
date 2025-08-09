"""
Unit tests for S3 operations.

Tests S3 file operations including download, metadata extraction,
and error handling.
"""
import os
import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from services.s3_operations import S3AudioOperations
from .conftest import create_s3_client_mock


@pytest.mark.unit
class TestS3AudioOperations:
    """Test cases for S3AudioOperations."""
    
    def setup_method(self):
        """Setup test instance."""
        with patch('services.s3_operations.aws_lambda_config_manager'):
            self.s3_ops = S3AudioOperations()
    
    def test_initialization(self):
        """Test S3AudioOperations initialization."""
        with patch('services.s3_operations.aws_lambda_config_manager') as mock_config:
            mock_config.get_s3_client.return_value = Mock()
            
            s3_ops = S3AudioOperations()
            
            assert s3_ops.bucket_name is not None
            assert s3_ops.s3_client is not None
    
    def test_download_audio_file_success(self, sample_audio_data):
        """Test successful audio file download."""
        with patch.object(self.s3_ops, 's3_client') as mock_s3:
            # Mock head_object response
            mock_s3.head_object.return_value = {
                'ContentLength': len(sample_audio_data),
                'ContentType': 'audio/wav'
            }
            
            # Mock get_object response
            mock_s3.get_object.return_value = {
                'Body': type('MockBody', (), {'read': lambda self: sample_audio_data})()
            }
            
            result = self.s3_ops.download_audio_file('test-key.wav')
            
            assert result == sample_audio_data
            mock_s3.head_object.assert_called_once()
            mock_s3.get_object.assert_called_once()
    
    def test_download_audio_file_not_found(self):
        """Test audio file download with file not found."""
        with patch.object(self.s3_ops, 's3_client') as mock_s3:
            mock_s3.head_object.side_effect = ClientError(
                {'Error': {'Code': 'NoSuchKey', 'Message': 'Key not found'}},
                'HeadObject'
            )
            
            with pytest.raises(ClientError):
                self.s3_ops.download_audio_file('nonexistent-key.wav')
    
    def test_download_audio_file_access_denied(self):
        """Test audio file download with access denied."""
        with patch.object(self.s3_ops, 's3_client') as mock_s3:
            mock_s3.head_object.side_effect = ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
                'HeadObject'
            )
            
            with pytest.raises(ClientError):
                self.s3_ops.download_audio_file('protected-key.wav')
    
    def test_download_audio_file_too_large(self):
        """Test audio file download with file too large."""
        large_size = 11 * 1024 * 1024  # 11MB
        
        with patch.object(self.s3_ops, 's3_client') as mock_s3:
            # Mock head_object to return large file size
            mock_s3.head_object.return_value = {
                'ContentLength': large_size,
                'ContentType': 'audio/wav'
            }
            
            with pytest.raises(ValueError, match="exceeds maximum"):
                self.s3_ops.download_audio_file('large-file.wav')
    
    def test_get_file_info_summary_success(self):
        """Test successful file info summary retrieval."""
        with patch.object(self.s3_ops, 's3_client') as mock_s3:
            mock_s3.head_object.return_value = {
                'ContentLength': 1048576,
                'ContentType': 'audio/wav',
                'LastModified': datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
                'ETag': '"abc123"',
                'Metadata': {'original-name': 'sample1.wav'}
            }
            
            result = self.s3_ops.get_file_info_summary('audio-uploads/user123/test-key.wav')
            
            assert result['file_name'] == 'test-key.wav'
            assert result['size_bytes'] == 1048576
            assert result['content_type'] == 'audio/wav'
    
    def test_get_file_info_summary_not_found(self):
        """Test file info summary with file not found."""
        with patch.object(self.s3_ops, 's3_client') as mock_s3:
            mock_s3.head_object.side_effect = ClientError(
                {'Error': {'Code': 'NoSuchKey', 'Message': 'Key not found'}},
                'HeadObject'
            )
            
            with pytest.raises(ClientError):
                self.s3_ops.get_file_info_summary('nonexistent-key.wav')
    
    def test_extract_user_id_from_key_success(self):
        """Test successful user ID extraction."""
        with patch.dict(os.environ, {'S3_TRIGGER_PREFIX': 'audio-uploads/'}):
            user_id = self.s3_ops.extract_user_id_from_key('audio-uploads/user123/sample1.wav')
            
            assert user_id == 'user123'
    
    def test_extract_user_id_from_key_invalid_prefix(self):
        """Test user ID extraction with invalid prefix."""
        with patch.dict(os.environ, {'S3_TRIGGER_PREFIX': 'audio-uploads/'}):
            with pytest.raises(ValueError, match="Key does not start with expected prefix"):
                self.s3_ops.extract_user_id_from_key('wrong-prefix/user123/sample1.wav')
    
    def test_extract_user_id_from_key_no_user_id(self):
        """Test user ID extraction with no user ID."""
        with patch.dict(os.environ, {'S3_TRIGGER_PREFIX': 'audio-uploads/'}):
            with pytest.raises(ValueError, match="Could not extract user_id"):
                self.s3_ops.extract_user_id_from_key('audio-uploads/')
    
    def test_extract_user_id_from_key_nested_path(self):
        """Test user ID extraction with nested path."""
        with patch.dict(os.environ, {'S3_TRIGGER_PREFIX': 'audio-uploads/'}):
            user_id = self.s3_ops.extract_user_id_from_key('audio-uploads/user123/subfolder/sample1.wav')
            
            assert user_id == 'user123'


@pytest.mark.integration
class TestS3OperationsIntegration:
    """Integration tests for S3 operations."""
    
    def test_s3_operations_with_mock_aws_client(self, sample_audio_data):
        """Test S3 operations with mocked AWS client."""
        with patch('services.s3_operations.aws_lambda_config_manager') as mock_config:
            # Use centralized S3 client mock
            mock_s3_client = create_s3_client_mock()
            mock_config.get_s3_client.return_value = mock_s3_client
            
            # Customize for this specific test
            mock_s3_client.head_object.return_value = {
                'ContentLength': len(sample_audio_data),
                'ContentType': 'audio/wav',
                'LastModified': mock_s3_client.head_object.return_value['LastModified'],
                'ETag': '"abc123"'
            }
            mock_s3_client.get_object.return_value['Body'].read.return_value = sample_audio_data
            
            # Create S3 operations instance and patch its s3_client
            s3_ops = S3AudioOperations()
            s3_ops.s3_client = mock_s3_client
            
            # Test download
            audio_data = s3_ops.download_audio_file('audio-uploads/user123/test-key.wav')
            assert audio_data == sample_audio_data
            
            # Test file info
            file_info = s3_ops.get_file_info_summary('audio-uploads/user123/test-key.wav')
            assert file_info['size_bytes'] == len(sample_audio_data)
            assert file_info['content_type'] == 'audio/wav'
    
    def test_s3_operations_error_handling(self):
        """Test S3 operations error handling with various AWS errors."""
        with patch('services.s3_operations.aws_lambda_config_manager') as mock_config:
            # Use centralized S3 client mock
            mock_s3_client = create_s3_client_mock()
            mock_config.get_s3_client.return_value = mock_s3_client
            
            # Create S3 operations instance and patch its s3_client
            s3_ops = S3AudioOperations()
            s3_ops.s3_client = mock_s3_client
            
            # Test different AWS errors
            aws_errors = [
                ('NoSuchKey', 'Key not found'),
                ('AccessDenied', 'Access denied'),
                ('ServiceUnavailable', 'Service unavailable')
            ]
            
            for error_code, error_message in aws_errors:
                # Configure head_object to raise the error
                mock_s3_client.head_object.side_effect = ClientError(
                    {'Error': {'Code': error_code, 'Message': error_message}},
                    'HeadObject'
                )
                
                with pytest.raises(ClientError) as exc_info:
                    s3_ops.download_audio_file('audio-uploads/user123/test-key.wav')
                
                assert exc_info.value.response['Error']['Code'] == error_code


@pytest.mark.aws
class TestS3OperationsAWS:
    """AWS-specific tests for S3 operations (require AWS credentials)."""
    
    @pytest.mark.skip(reason="Requires AWS credentials and real S3 bucket")
    def test_real_s3_download(self):
        """Test with real S3 service (skipped by default)."""
        # This test would require real AWS credentials and a test bucket
        # Only run when specifically testing against real AWS
        pass
    
    @pytest.mark.skip(reason="Requires AWS credentials and real S3 bucket") 
    def test_real_s3_error_scenarios(self):
        """Test real S3 error scenarios (skipped by default)."""
        # This test would verify real AWS error responses
        pass
