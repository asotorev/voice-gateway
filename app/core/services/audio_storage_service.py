"""
Audio storage service implementation for Voice Gateway.
Focuses purely on business logic for signed URL operations.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError
from app.core.ports.storage_service import StorageServicePort, StorageError
from app.core.services.audio_constraints import AudioConstraints
from app.infrastructure.config.aws_config import aws_config
from app.infrastructure.config.infrastructure_settings import infra_settings

logger = logging.getLogger(__name__)


class AudioStorageService(StorageServicePort):
    """
    S3 implementation of StorageServicePort for audio files.
    
    Focuses on business logic for signed URL operations.
    Infrastructure concerns (bucket creation, configuration) are handled by S3Setup.
    """
    
    def __init__(self):
        """Initialize audio storage service with AWS configuration."""
        self.s3_client = aws_config.s3_client
        self.bucket_name = infra_settings.s3_bucket_name
        self._bucket_checked = False
        
        logger.info("AudioStorageService initialized", extra={
            "bucket_name": self.bucket_name,
            "use_local_s3": infra_settings.use_local_s3,
            "endpoint": infra_settings.s3_endpoint_url or "AWS Default"
        })
    
    def _ensure_bucket_exists(self):
        """Lazy bucket existence check and creation."""
        if self._bucket_checked:
            return
            
        try:
            from app.infrastructure.storage.s3_setup import S3Setup
            s3_setup = S3Setup()
            
            if not s3_setup.bucket_exists(self.bucket_name):
                logger.info("Creating missing bucket", extra={"bucket_name": self.bucket_name})
                s3_setup.setup_audio_bucket()
            
            self._bucket_checked = True
            
        except Exception as e:
            logger.warning("Bucket setup failed, continuing anyway", extra={
                "bucket_name": self.bucket_name,
                "error": str(e)
            })
            self._bucket_checked = True  # Don't retry
    
    async def generate_upload_url(
        self,
        file_path: str,
        content_type: str = "audio/wav",
        expiration_minutes: int = 15
    ) -> Dict[str, Any]:
        """
        Generate signed URL for file upload to S3 with REAL validation.
        
        Args:
            file_path: Relative path where file will be stored
            content_type: MIME type of the file being uploaded
            expiration_minutes: URL expiration time in minutes
            
        Returns:
            Dict containing upload URL, fields, and metadata
            
        Raises:
            StorageError: If URL generation fails
        """
        try:
            # Ensure bucket exists (lazy initialization)
            self._ensure_bucket_exists()
            
            # Validate inputs
            self._validate_file_path(file_path, "generate_upload_url")
            self._validate_expiration(expiration_minutes, 1, 60, "generate_upload_url")
            self._validate_content_type(content_type, "generate_upload_url")
            
            # Clean the file path
            clean_path = self._clean_path(file_path)
            
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(minutes=expiration_minutes)
            
            # Prepare conditions for file size validation
            conditions = []
            fields = {}
            
            # Add file size validation for audio files
            if content_type.startswith('audio/'):
                max_size = AudioConstraints.get_max_audio_file_size_bytes()
                # Log audio file size limit for debugging
                logger.debug("Audio file size validation", extra={
                    "content_type": content_type,
                    "max_size_bytes": max_size,
                    "max_size_mb": max_size // (1024 * 1024)
                })
                # This ACTUALLY gets enforced by S3
                conditions.extend([
                    ["content-length-range", 1, max_size],
                    ["starts-with", "$Content-Type", "audio/"]
                ])
            
            # Add content type validation
            conditions.append(["eq", "$Content-Type", content_type])
            fields['Content-Type'] = content_type
            
            # Generate presigned POST (better for file upload with validation)
            presigned_post = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=clean_path,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expiration_minutes * 60
            )
            
            result = {
                'upload_url': presigned_post['url'],
                'upload_fields': presigned_post['fields'],  # Required form fields
                'file_path': clean_path,
                'expires_at': expires_at.isoformat() + 'Z',
                'bucket_name': self.bucket_name,
                'content_type': content_type,
                'max_file_size_bytes': max_size if content_type.startswith('audio/') else None,
                'upload_method': 'POST'  # Important: POST, not PUT
            }
            
            logger.debug("Generated upload URL with size validation", extra={
                "operation": "generate_upload_url",
                "file_path": clean_path,
                "content_type": content_type,
                "max_size_bytes": max_size if content_type.startswith('audio/') else None,
                "expiration_minutes": expiration_minutes
            })
            
            return result
            
        except StorageError:
            raise
        except ClientError as e:
            raise self._handle_client_error(e, "generate_upload_url", file_path)
        except NoCredentialsError:
            raise StorageError("S3 credentials not configured", "generate_upload_url", file_path)
        except Exception as e:
            logger.error("Unexpected error generating upload URL", extra={
                "operation": "generate_upload_url",
                "error": str(e),
                "file_path": file_path
            })
            raise StorageError(f"Failed to generate upload URL: {str(e)}", "generate_upload_url", file_path)
    
    async def generate_download_url(
        self,
        file_path: str,
        expiration_minutes: int = 60
    ) -> str:
        """
        Generate signed URL for file download from S3.
        
        Args:
            file_path: Relative path to the file
            expiration_minutes: URL expiration time in minutes
            
        Returns:
            str: Signed URL for GET request
            
        Raises:
            StorageError: If file doesn't exist or URL generation fails
        """
        try:
            # Validate inputs
            self._validate_file_path(file_path, "generate_download_url")
            self._validate_expiration(expiration_minutes, 1, 1440, "generate_download_url")
            
            # Clean the file path
            clean_path = self._clean_path(file_path)
            
            # Check if file exists first
            if not await self.file_exists(clean_path):
                raise StorageError(f"File does not exist: {clean_path}", "generate_download_url", clean_path)
            
            # Generate presigned URL for GET
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': clean_path
                },
                ExpiresIn=expiration_minutes * 60,
                HttpMethod='GET'
            )
            
            logger.debug("Generated download URL", extra={
                "operation": "generate_download_url",
                "file_path": clean_path,
                "expiration_minutes": expiration_minutes
            })
            
            return presigned_url
            
        except StorageError:
            raise
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise StorageError(f"File not found: {file_path}", "generate_download_url", file_path)
            raise self._handle_client_error(e, "generate_download_url", file_path)
        except Exception as e:
            logger.error("Unexpected error generating download URL", extra={
                "operation": "generate_download_url",
                "error": str(e),
                "file_path": file_path
            })
            raise StorageError(f"Failed to generate download URL: {str(e)}", "generate_download_url", file_path)
    
    async def file_exists(self, file_path: str) -> bool:
        """
        Check if file exists in S3 bucket.
        
        Args:
            file_path: Relative path to check
            
        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            if not file_path or not file_path.strip():
                return False
            
            # Clean the file path
            clean_path = self._clean_path(file_path)
            
            # Use head_object to check existence (more efficient than list)
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=clean_path
            )
            
            logger.debug("File exists check: found", extra={
                "operation": "file_exists",
                "file_path": clean_path,
                "exists": True
            })
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code in ['NoSuchKey', '404']:
                logger.debug("File exists check: not found", extra={
                    "operation": "file_exists",
                    "file_path": file_path,
                    "exists": False
                })
                return False
            
            # Other errors should be logged but still return False
            logger.warning("Error checking file existence", extra={
                "operation": "file_exists",
                "error_code": error_code,
                "file_path": file_path
            })
            return False
            
        except Exception as e:
            # Log unexpected errors but don't raise - return False
            logger.warning("Unexpected error checking file existence", extra={
                "operation": "file_exists",
                "error": str(e),
                "file_path": file_path
            })
            return False
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from S3 storage.
        Args:
            file_path: Relative path to the file to delete
        Returns:
            bool: True if file was deleted, False if not found
        Raises:
            StorageError: If deletion fails
        """
        try:
            self._validate_file_path(file_path, "delete_file")
            clean_path = self._clean_path(file_path)
            response = self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=clean_path
            )
            # S3 delete_object is idempotent: no error if not found
            logger.info("Deleted file from S3", extra={
                "operation": "delete_file",
                "file_path": clean_path
            })
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.info("File not found for deletion", extra={
                    "operation": "delete_file",
                    "file_path": file_path
                })
                return False
            raise self._handle_client_error(e, "delete_file", file_path)
        except Exception as e:
            logger.error("Unexpected error deleting file", extra={
                "operation": "delete_file",
                "error": str(e),
                "file_path": file_path
            })
            raise StorageError(f"Failed to delete file: {str(e)}", "delete_file", file_path)
    
    # Helper methods for business logic
    
    def _validate_file_path(self, file_path: str, operation: str) -> None:
        """Validate file path format and raise StorageError if invalid."""
        if not file_path or not file_path.strip():
            raise StorageError("File path cannot be empty", operation)
        
        clean_path = file_path.strip()
        
        # Basic validations
        if clean_path in ['/', '.', '..']:
            raise StorageError(f"Invalid file path: {file_path}", operation)
        
        # Check for invalid characters
        invalid_chars = ['\\', '<', '>', ':', '"', '|', '?', '*']
        if any(char in clean_path for char in invalid_chars):
            raise StorageError(f"File path contains invalid characters: {file_path}", operation)
        
        # Check for reasonable length (S3 key limit is 1024 bytes)
        if len(clean_path) > 1024:
            raise StorageError(f"File path too long (max 1024 characters): {file_path}", operation)
    
    def _validate_expiration(self, minutes: int, min_val: int, max_val: int, operation: str) -> None:
        """Validate expiration time."""
        if not isinstance(minutes, int) or minutes < min_val or minutes > max_val:
            raise StorageError(
                f"Invalid expiration: {minutes} minutes (must be {min_val}-{max_val})",
                operation, ""
            )
    
    def _validate_content_type(self, content_type: str, operation: str) -> None:
        """Validate content type against allowed MIME types."""
        if not content_type:
            raise StorageError("Content type is required", operation, "")
        
        allowed_types = AudioConstraints.ALLOWED_AUDIO_MIME_TYPES
        if content_type.lower() not in allowed_types:
            raise StorageError(
                f"Invalid content type: {content_type}. Allowed: {', '.join(allowed_types)}",
                operation, ""
            )
    
    def _validate_audio_file_size(self, file_size_bytes: int, operation: str) -> None:
        """Validate audio file size against configured limits."""
        if file_size_bytes <= 0:
            raise StorageError("Audio file size must be positive", operation, "")
        
        max_size = AudioConstraints.get_max_audio_file_size_bytes()
        if file_size_bytes > max_size:
            raise StorageError(
                f"Audio file size {file_size_bytes} bytes exceeds maximum {max_size} bytes",
                operation, ""
            )
    
    def _clean_path(self, file_path: str) -> str:
        """Clean and normalize file path."""
        return file_path.strip().lstrip('/')
    
    def _handle_client_error(self, error: ClientError, operation: str, file_path: str) -> StorageError:
        """Handle S3 client errors and convert to StorageError."""
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        
        logger.error("S3 client error", extra={
            "operation": operation,
            "error_code": error_code,
            "file_path": file_path
        })
        
        return StorageError(f"S3 error {error_code}: {error_message}", operation, file_path)
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get storage service information and configuration.
        
        Returns:
            Dict with service configuration and status
        """
        return {
            'service_type': 's3',
            'bucket_name': self.bucket_name,
            'region': infra_settings.aws_region,
            'use_local_s3': infra_settings.use_local_s3,
            'endpoint_url': infra_settings.s3_endpoint_url,
            'use_ssl': infra_settings.s3_use_ssl,
            'max_file_size_mb': AudioConstraints.MAX_AUDIO_FILE_SIZE_MB,
            'allowed_formats': AudioConstraints.ALLOWED_AUDIO_FORMATS,
            'upload_expiration_default': infra_settings.audio_upload_expiration_minutes,
            'download_expiration_default': infra_settings.audio_download_expiration_minutes
        } 