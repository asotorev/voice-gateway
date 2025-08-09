"""
S3 audio storage service implementation.

This module provides the S3-based implementation of the StorageServicePort
interface, following Clean Architecture principles with dependency inversion.
"""
import os
import logging
import tempfile
from typing import Dict, Any
from botocore.exceptions import ClientError

from ...core.ports.storage_service import StorageServicePort
from ...infrastructure.aws.aws_config import aws_config_manager

logger = logging.getLogger(__name__)


class S3AudioStorageService(StorageServicePort):
    """
    S3 implementation of the storage service for audio files.
    
    Handles audio file downloads, validation, and metadata retrieval
    with proper error handling and logging for Lambda environment.
    """
    
    def __init__(self):
        """Initialize S3 audio storage service."""
        self.s3_client = aws_config_manager.s3_client
        self.bucket_name = aws_config_manager.get_s3_bucket_name()
        self.max_file_size = int(os.getenv('MAX_AUDIO_FILE_SIZE_MB', '10')) * 1024 * 1024
        self.trigger_prefix = os.getenv('S3_TRIGGER_PREFIX', 'audio-uploads/')
        
        logger.info("S3 audio storage service initialized", extra={
            "bucket": self.bucket_name,
            "max_file_size_mb": self.max_file_size // (1024 * 1024),
            "trigger_prefix": self.trigger_prefix
        })
    
    async def download_audio_file(self, file_path: str) -> bytes:
        """
        Download audio file from S3.
        
        Args:
            file_path: S3 object key for the audio file
            
        Returns:
            Audio file content as bytes
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is invalid or too large
        """
        logger.info("Starting audio file download", extra={
            "bucket": self.bucket_name,
            "key": file_path
        })
        
        try:
            # First, get object metadata to check size
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            file_size = response['ContentLength']
            
            # Validate file size
            if file_size > self.max_file_size:
                raise ValueError(f"File size {file_size} exceeds maximum {self.max_file_size} bytes")
            
            if file_size == 0:
                raise ValueError("Cannot process empty audio file")
            
            # Download the file
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_path)
            audio_data = response['Body'].read()
            
            logger.info("Audio file downloaded successfully", extra={
                "bucket": self.bucket_name,
                "key": file_path,
                "size_bytes": len(audio_data),
                "content_type": response.get('ContentType', 'unknown')
            })
            
            return audio_data
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            elif error_code == 'NoSuchBucket':
                raise FileNotFoundError(f"S3 bucket not found: {self.bucket_name}")
            else:
                aws_config_manager.handle_aws_error(e, "download_audio_file", file_path)
                raise
        except Exception as e:
            logger.error("Failed to download audio file", extra={
                "bucket": self.bucket_name,
                "key": file_path,
                "error": str(e)
            })
            raise
    
    async def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Get metadata for an audio file.
        
        Args:
            file_path: S3 object key for the audio file
            
        Returns:
            Dict with file metadata (size, format, etc.)
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            
            metadata = {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'file_extension': self._get_file_extension(file_path),
                'size_bytes': response['ContentLength'],
                'size_mb': round(response['ContentLength'] / (1024 * 1024), 2),
                'last_modified': response['LastModified'].isoformat(),
                'etag': response['ETag'].strip('"'),
                'content_type': response.get('ContentType', 'application/octet-stream'),
                's3_metadata': response.get('Metadata', {})
            }
            
            logger.debug("Retrieved audio file metadata", extra=metadata)
            return metadata
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            else:
                aws_config_manager.handle_aws_error(e, "get_file_metadata", file_path)
                raise
    
    async def file_exists(self, file_path: str) -> bool:
        """
        Check if audio file exists in S3.
        
        Args:
            file_path: S3 object key for the audio file
            
        Returns:
            True if file exists
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return False
            else:
                # For other errors, log and re-raise
                logger.warning("Error checking file existence", extra={
                    "file_path": file_path,
                    "error_code": error_code
                })
                raise
    
    def extract_user_id_from_path(self, file_path: str) -> str:
        """
        Extract user ID from S3 object key.
        
        Expected format: audio-uploads/{user_id}/sample_{n}.wav
        
        Args:
            file_path: S3 object key
            
        Returns:
            User ID extracted from path
            
        Raises:
            ValueError: If path format is invalid
        """
        try:
            if not file_path.startswith(self.trigger_prefix):
                # If key doesn't even look like a path, classify as invalid format
                if '/' not in file_path:
                    raise ValueError(f"Invalid S3 key format: {file_path}")
                raise ValueError(f"Key does not start with expected prefix: {self.trigger_prefix}")
            
            # Extract path after prefix: audio-uploads/{user_id}/filename.wav
            path_after_prefix = file_path[len(self.trigger_prefix):]
            path_parts = path_after_prefix.split('/')
            
            if not path_parts or not path_parts[0]:
                raise ValueError("Could not extract user_id from key format")
            
            user_id = path_parts[0]
            
            logger.debug("Extracted user ID from S3 key", extra={
                "file_path": file_path,
                "user_id": user_id
            })
            
            return user_id
            
        except ValueError:
            # Re-raise ValueError exceptions as-is
            raise
        except Exception as e:
            logger.error("Failed to extract user_id from S3 key", extra={
                "file_path": file_path,
                "error": str(e)
            })
            raise ValueError(f"Invalid S3 key format: {file_path}")
    
    def download_to_temp_file(self, file_path: str) -> str:
        """
        Download audio file to a temporary file for processing.
        
        Args:
            file_path: S3 object key for the audio file
            
        Returns:
            Path to temporary file containing audio data
        """
        logger.info("Downloading audio to temporary file", extra={
            "bucket": self.bucket_name,
            "key": file_path
        })
        
        try:
            # Download audio data synchronously for temp file
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_path)
            audio_data = response['Body'].read()
            
            # Create temporary file with appropriate extension
            file_extension = self._get_file_extension(file_path)
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=f'.{file_extension}' if file_extension else '.tmp'
            )
            
            # Write audio data to temp file
            temp_file.write(audio_data)
            temp_file.flush()
            temp_file.close()
            
            logger.info("Audio downloaded to temporary file", extra={
                "temp_file": temp_file.name,
                "size_bytes": len(audio_data)
            })
            
            return temp_file.name
            
        except Exception as e:
            logger.error("Failed to download audio to temp file", extra={
                "bucket": self.bucket_name,
                "key": file_path,
                "error": str(e)
            })
            raise
    
    def cleanup_temp_file(self, temp_file_path: str) -> None:
        """
        Clean up temporary file after processing.
        
        Args:
            temp_file_path: Path to temporary file to delete
        """
        try:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                logger.debug("Temporary file cleaned up", extra={
                    "temp_file": temp_file_path
                })
        except Exception as e:
            logger.warning("Failed to cleanup temporary file", extra={
                "temp_file": temp_file_path,
                "error": str(e)
            })
    
    def validate_audio_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validate audio file properties.
        
        Args:
            file_path: S3 object key for the audio file
            
        Returns:
            Dict with validation results
        """
        try:
            # Get metadata first
            metadata = self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            
            validation_result = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'metadata': {
                    'size_bytes': metadata['ContentLength'],
                    'content_type': metadata.get('ContentType', ''),
                    'last_modified': metadata['LastModified'].isoformat()
                }
            }
            
            # Check file size
            file_size = metadata['ContentLength']
            if file_size > self.max_file_size:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"File size {file_size} exceeds maximum {self.max_file_size}")
            
            if file_size == 0:
                validation_result['is_valid'] = False
                validation_result['errors'].append("File is empty")
            
            # Check file extension
            file_extension = self._get_file_extension(file_path)
            supported_formats = os.getenv('SUPPORTED_AUDIO_FORMATS', 'wav,mp3,m4a,flac').split(',')
            
            if file_extension.lower() not in [fmt.lower() for fmt in supported_formats]:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Unsupported format: {file_extension}")
            
            # Check content type (warning only)
            content_type = metadata.get('ContentType', '')
            if not content_type.startswith('audio/') and content_type != 'application/octet-stream':
                validation_result['warnings'].append(f"Unexpected content type: {content_type}")
            
            logger.info("Audio file validation completed", extra={
                "key": file_path,
                "is_valid": validation_result['is_valid'],
                "errors": len(validation_result['errors']),
                "warnings": len(validation_result['warnings'])
            })
            
            return validation_result
            
        except Exception as e:
            logger.error("Failed to validate audio file", extra={
                "key": file_path,
                "error": str(e)
            })
            raise
    
    def _get_file_extension(self, file_path: str) -> str:
        """
        Extract file extension from file path.
        
        Args:
            file_path: File path
            
        Returns:
            File extension without dot
        """
        if '.' not in file_path:
            return ''
        return file_path.split('.')[-1]
