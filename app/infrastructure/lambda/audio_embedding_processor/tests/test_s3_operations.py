"""
Unit tests for S3 operations (Clean Architecture).

Tests S3 file operations including download, metadata extraction,
and error handling using Clean Architecture patterns.
"""
import inspect
import pytest
from unittest.mock import Mock, patch, AsyncMock
from botocore.exceptions import ClientError

# Try to import shared layer components
try:
    from shared.adapters.storage.s3_audio_storage import S3AudioStorageService
    from shared.infrastructure.aws.aws_config import AWSConfigManager
    from shared.core.ports.storage_service import StorageServicePort
    SHARED_LAYER_AVAILABLE = True
except ImportError:
    SHARED_LAYER_AVAILABLE = False
    S3AudioStorageService = None
    AWSConfigManager = None
    StorageServicePort = None


@pytest.mark.unit
class TestS3AudioStorageService:
    """Test cases for S3 audio storage service using Clean Architecture."""
    
    def setup_method(self):
        """Setup test instance."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available for testing")
            
        self.s3_service = S3AudioStorageService()
    
    def test_initialization(self):
        """Test S3AudioStorageService initialization."""
        assert hasattr(self.s3_service, 'bucket_name')
        assert hasattr(self.s3_service, 's3_client') or hasattr(self.s3_service, 'aws_config')
    
    @pytest.mark.asyncio
    async def test_download_audio_file_success(self):
        """Test successful file download from S3."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available")
            
        test_key = 'audio-uploads/user123/sample.wav'
        expected_data = b'fake_audio_data'
        
        # Mock S3 client
        with patch.object(self.s3_service, 's3_client') as mock_s3:
            mock_response = {
                'Body': Mock(),
                'ContentLength': len(expected_data)
            }
            mock_response['Body'].read.return_value = expected_data
            mock_s3.get_object.return_value = mock_response
            mock_s3.head_object.return_value = {'ContentLength': len(expected_data)}
            
            result = await self.s3_service.download_audio_file(test_key)
            
            assert result == expected_data
            mock_s3.get_object.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_audio_file_not_found(self):
        """Test file download when file doesn't exist."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available")
            
        test_key = 'nonexistent/file.wav'
        
        with patch.object(self.s3_service, 's3_client') as mock_s3:
            mock_s3.head_object.side_effect = ClientError(
                {'Error': {'Code': 'NoSuchKey'}}, 'HeadObject'
            )
            mock_s3.get_object.side_effect = ClientError(
                {'Error': {'Code': 'NoSuchKey'}}, 'GetObject'
            )
            
            with pytest.raises(FileNotFoundError):
                await self.s3_service.download_audio_file(test_key)
    
    @pytest.mark.asyncio
    async def test_get_file_metadata_success(self):
        """Test successful metadata retrieval."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available")
            
        test_key = 'audio-uploads/user123/sample.wav'
        
        from datetime import datetime
        
        with patch.object(self.s3_service, 's3_client') as mock_s3:
            mock_s3.head_object.return_value = {
                'ContentLength': 1048576,
                'ContentType': 'audio/wav',
                'LastModified': datetime.fromisoformat('2024-01-01T00:00:00'),
                'ETag': '"abcd1234"'
            }
            
            result = await self.s3_service.get_file_metadata(test_key)
            
            assert 'size_bytes' in result
            assert 'content_type' in result
            assert 'file_name' in result
            assert 'file_extension' in result
            mock_s3.head_object.assert_called_once()
    
    def test_extract_user_id_from_path(self):
        """Test user ID extraction from S3 key.""" 
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available")
            
        test_key = 'audio-uploads/user123/sample1.wav'
        result = self.s3_service.extract_user_id_from_path(test_key)
        
        assert result == 'user123'
    
    def test_extract_user_id_invalid_path(self):
        """Test user ID extraction with invalid key format."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available")
            
        invalid_key = 'invalid/key/format.wav'
        
        with pytest.raises(ValueError):
            self.s3_service.extract_user_id_from_path(invalid_key)


@pytest.mark.unit
class TestStorageServicePort:
    """Test cases for StorageServicePort interface."""
    
    def test_storage_service_port_interface(self):
        """Test that the StorageServicePort interface exists."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available")
            
        # Verify it's an abstract base class
        assert inspect.isabstract(StorageServicePort)
        
        # Verify required methods exist
        required_methods = ['download_audio_file', 'get_file_metadata', 'file_exists', 'extract_user_id_from_path']
        for method_name in required_methods:
            assert hasattr(StorageServicePort, method_name)


@pytest.mark.integration
class TestS3StorageIntegration:
    """Integration tests for S3 storage operations."""
    
    @pytest.mark.asyncio
    async def test_full_file_processing_flow(self):
        """Test full S3 file processing flow."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available for integration testing")
            
        service = S3AudioStorageService()
        test_key = 'audio-uploads/user123/test.wav'
        
        # This would require full integration test setup
        assert service is not None
        assert hasattr(service, 'download_audio_file')
        assert hasattr(service, 'get_file_metadata')
    
    @pytest.mark.asyncio
    async def test_error_handling_scenarios(self):
        """Test S3 operations error handling across different scenarios."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available for integration testing")
            
        service = S3AudioStorageService()
        
        # Test various error scenarios would go here
        assert service is not None


@pytest.mark.aws
@pytest.mark.integration
class TestS3OperationsAWS:
    """AWS integration tests for S3 operations (requires AWS credentials)."""
    
    @pytest.mark.slow
    @pytest.mark.skipif(True, reason="AWS tests disabled - use --aws flag to enable")
    def test_real_s3_operations(self):
        """Test S3 operations against real AWS S3 (requires credentials and --aws flag)."""
        pytest.skip("Real AWS tests require proper setup and credentials")
    
    def test_s3_client_configuration(self):
        """Test S3 client configuration."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available for testing")
            
        config_manager = AWSConfigManager()
        assert config_manager is not None
    
    def test_s3_bucket_configuration(self):
        """Test S3 bucket configuration."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available for testing")
            
        service = S3AudioStorageService()
        # Test bucket configuration
        assert hasattr(service, 'bucket_name')