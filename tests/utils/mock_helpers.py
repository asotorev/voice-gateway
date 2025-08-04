#!/usr/bin/env python3
"""
Shared mock helpers for reducing duplication in test fixtures.
Contains common mock setup patterns and factory functions.
"""
from unittest.mock import Mock
from typing import Dict, Any


class MockHelpers:
    """Helper class for creating common mock objects with consistent configurations."""
    
    @staticmethod
    def create_mock_user_repository() -> Mock:
        """Create a mock user repository with standard return values."""
        mock_repo = Mock()
        mock_repo.save.return_value = None
        mock_repo.get_by_id.return_value = None
        mock_repo.get_by_email.return_value = None
        mock_repo.check_password_hash_exists.return_value = False
        return mock_repo
    
    @staticmethod
    def create_mock_password_service() -> Mock:
        """Create a mock password service with standard return values."""
        mock_service = Mock()
        mock_service.generate_password.return_value = "test password"
        mock_service.hash_password.return_value = "hashed_password"
        mock_service.validate_password_format.return_value = True
        return mock_service
    
    @staticmethod
    def create_mock_storage_service() -> Mock:
        """Create a mock storage service with standard return values."""
        mock_service = Mock()
        mock_service.generate_audio_upload_url.return_value = {
            'upload_url': 'https://test-bucket.s3.amazonaws.com',
            'file_path': 'test/path.wav',
            'upload_method': 'POST',
            'content_type': 'audio/wav',
            'upload_fields': {},
            'expires_at': '2024-01-01T12:00:00Z',
            'max_file_size_bytes': 10485760
        }
        mock_service.generate_audio_download_url.return_value = 'https://test-bucket.s3.amazonaws.com/download/path.wav'
        mock_service.audio_file_exists.return_value = True
        mock_service.delete_audio_file.return_value = True
        return mock_service
    
    @staticmethod
    def create_mock_s3_client() -> Mock:
        """Create a mock S3 client with standard configurations."""
        mock_client = Mock()
        
        # Mock presigned POST response
        mock_response = {
            'url': 'https://test-bucket.s3.amazonaws.com',
            'fields': {
                'key': 'user123/sample1.wav',
                'bucket': 'test-bucket',
                'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
                'X-Amz-Credential': 'test-credential',
                'X-Amz-Date': '20240101T000000Z',
                'Policy': 'test-policy',
                'X-Amz-Signature': 'test-signature',
                'Content-Type': 'audio/wav'
            }
        }
        mock_client.generate_presigned_post.return_value = mock_response
        mock_client.generate_presigned_url.return_value = 'https://test-bucket.s3.amazonaws.com/signed-download-url'
        mock_client.head_object.return_value = {'ContentLength': 1024}
        mock_client.delete_object.return_value = {'DeleteMarker': True}
        
        return mock_client
    
    @staticmethod
    def create_test_environment_config() -> Dict[str, str]:
        """Create standard test environment configuration."""
        return {
            'ENVIRONMENT': 'test',
            'AWS_REGION': 'us-east-1',
            'S3_BUCKET_NAME': 'test-bucket',
            'S3_ENDPOINT_URL': 'http://localhost:9000',
            'DYNAMODB_ENDPOINT_URL': 'http://localhost:8000',
            'USERS_TABLE_NAME': 'voice-gateway-users-test',
            'AUDIO_BASE_URL': 's3://test-bucket/',
            'MAX_AUDIO_FILE_SIZE_MB': '10'
        }
    
    @staticmethod
    def create_mock_health_check_response() -> Dict[str, Any]:
        """Create a mock health check response."""
        return {
            's3': {
                'status': 'healthy',
                'details': 'S3/MinIO connection successful'
            },
            'dynamodb': {
                'status': 'healthy',
                'details': 'DynamoDB connection successful'
            },
            'overall': 'healthy'
        }
    
    @staticmethod
    async def cleanup_test_files(service, files: list) -> list:
        """Clean up test files and return any cleanup errors."""
        cleanup_errors = []
        
        for file_path in files:
            try:
                result = await service.delete_audio_file(file_path)
                if not result:
                    cleanup_errors.append(f"Could not delete: {file_path}")
            except Exception as e:
                cleanup_errors.append(f"Error deleting {file_path}: {str(e)}")
        
        return cleanup_errors 