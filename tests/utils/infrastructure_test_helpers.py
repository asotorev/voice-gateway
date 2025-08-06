#!/usr/bin/env python3
"""
Shared test helpers for infrastructure tests.
Contains common mock setup and utility functions for S3, DynamoDB, and other infrastructure services.
"""
import sys
import os
from pathlib import Path
from unittest.mock import Mock
from botocore.exceptions import ClientError

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.adapters.services.audio_storage_service import AudioStorageAdapter
from app.infrastructure.config.infrastructure_settings import infra_settings
from app.infrastructure.services.health_checks import health_check_service
from tests.utils.mock_helpers import MockHelpers


class InfrastructureTestHelpers:
    """Shared test helpers for infrastructure tests."""
    
    @staticmethod
    def create_mock_service() -> AudioStorageAdapter:
        """Create AudioStorageAdapter with mock S3 client for unit tests."""
        service = AudioStorageAdapter()
        service.s3_client = MockHelpers.create_mock_s3_client()
        service.bucket_name = infra_settings.s3_bucket_name or "test-bucket"
        return service
    
    @staticmethod
    def create_real_service() -> AudioStorageAdapter:
        """Create AudioStorageAdapter with real S3 client for integration tests."""
        return AudioStorageAdapter()
    
    @staticmethod
    def setup_mock_presigned_url(mock_client: Mock, return_url: str = None):
        """Setup mock S3 client to return a presigned POST response."""
        if return_url is None:
            bucket_name = infra_settings.s3_bucket_name or "test-bucket"
            return_url = f"https://{bucket_name}.s3.amazonaws.com"
        
        # Mock presigned POST response
        mock_response = {
            'url': return_url,
            'fields': {
                'key': 'user123/sample1.wav',
                'bucket': infra_settings.s3_bucket_name or 'test-bucket',
                'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
                'X-Amz-Credential': 'test-credential',
                'X-Amz-Date': '20240101T000000Z',
                'Policy': 'test-policy',
                'X-Amz-Signature': 'test-signature',
                'Content-Type': 'audio/wav'
            }
        }
        mock_client.generate_presigned_post.return_value = mock_response
    
    @staticmethod
    def setup_mock_head_object(mock_client: Mock, exists: bool = True):
        """Setup mock S3 client for head_object calls."""
        if exists:
            mock_client.head_object.return_value = {'ContentLength': 1024}
        else:
            error_response = {
                'Error': {
                    'Code': 'NoSuchKey',
                    'Message': 'The specified key does not exist'
                }
            }
            mock_client.head_object.side_effect = ClientError(error_response, 'head_object')
    
    @staticmethod
    def setup_mock_error(mock_client: Mock, error_code: str = 'AccessDenied', error_message: str = 'Access denied'):
        """Setup mock S3 client to simulate errors."""
        error_response = {
            'Error': {
                'Code': error_code,
                'Message': error_message
            }
        }
        mock_client.generate_presigned_post.side_effect = ClientError(error_response, 'post_object')
    
    @staticmethod
    def setup_mock_presigned_get_url(mock_client: Mock, return_url: str = None):
        """Setup mock S3 client to return a presigned GET URL for downloads."""
        if return_url is None:
            bucket_name = infra_settings.s3_bucket_name or "test-bucket"
            return_url = f"https://{bucket_name}.s3.amazonaws.com/signed-download-url"
        
        mock_client.generate_presigned_url.return_value = return_url
    
    @staticmethod
    def setup_mock_delete_object(mock_client: Mock, success: bool = True):
        """Setup mock S3 client for delete_object calls."""
        if success:
            mock_client.delete_object.return_value = {'DeleteMarker': True}
        else:
            error_response = {
                'Error': {
                    'Code': 'NoSuchKey',
                    'Message': 'The specified key does not exist'
                }
            }
            mock_client.delete_object.side_effect = ClientError(error_response, 'delete_object')
    
    @staticmethod
    def check_infrastructure() -> bool:
        """Check if infrastructure services (S3, DynamoDB, etc.) are available."""
        try:
            health = health_check_service.check_all_services()
            s3_health = health.get('s3', {})
            
            if s3_health.get('status') != 'healthy':
                print("ERROR: S3/MinIO infrastructure not available")
                print("Please ensure services are running: docker-compose up -d")
                print(f"S3 Status: {s3_health}")
                return False
            
            print("Infrastructure health check: PASSED")
            return True
            
        except Exception as e:
            print(f"ERROR: Cannot check infrastructure health: {e}")
            return False
    
    @staticmethod
    def create_test_audio_content(size_bytes: int = 1024) -> bytes:
        """Create fake audio content for testing."""
        # Basic WAV header structure for testing
        wav_header = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"fmt " + b"\x00" * 16
        remaining_size = max(0, size_bytes - len(wav_header))
        fake_audio_data = b"fake audio data " * (remaining_size // 16 + 1)
        return wav_header + fake_audio_data[:remaining_size]
    
    @staticmethod
    def get_test_file_path(user_id: str = None, sample_id: str = None) -> str:
        """Generate a test file path."""
        if user_id is None:
            user_id = f"test-user-{os.getpid()}"
        if sample_id is None:
            sample_id = f"sample-{os.getpid()}"
        return f"{user_id}/{sample_id}.wav"
