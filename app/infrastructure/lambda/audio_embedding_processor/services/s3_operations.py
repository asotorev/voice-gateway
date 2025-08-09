"""
S3 operations for Lambda audio processing.

This module provides S3-specific operations for downloading audio files,
validating file properties, and managing audio file lifecycle in the
Lambda processing pipeline.
"""
import os
import logging
import tempfile
from typing import Optional, Dict, Any, BinaryIO
from botocore.exceptions import ClientError
from utils.aws_lambda_config import aws_lambda_config_manager

logger = logging.getLogger(__name__)


class S3AudioOperations:
    """
    S3 operations specifically designed for audio file processing in Lambda.
    
    Handles audio file downloads, validation, and cleanup with proper
    error handling and logging for the Lambda environment.
    """
    
    def __init__(self):
        """Initialize S3 audio operations."""
        self.s3_client = aws_lambda_config_manager.s3_client
        self.bucket_name = aws_lambda_config_manager.get_s3_bucket_name()
        self.max_file_size = int(os.getenv('MAX_AUDIO_FILE_SIZE_MB', '10')) * 1024 * 1024
        
        logger.info("S3 audio operations initialized", extra={
            "bucket": self.bucket_name,
            "max_file_size_mb": self.max_file_size // (1024 * 1024)
        })
    
    def download_audio_file(self, s3_key: str) -> bytes:
        """
        Download audio file from S3.
        
        Args:
            s3_key: S3 object key for the audio file
            
        Returns:
            Audio file content as bytes
            
        Raises:
            ValueError: If file is too large or invalid
            ClientError: If S3 operation fails
        """
        logger.info("Starting audio file download", extra={
            "bucket": self.bucket_name,
            "key": s3_key
        })
        
        try:
            # First, get object metadata to check size
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            file_size = response['ContentLength']
            
            # Validate file size
            if file_size > self.max_file_size:
                raise ValueError(f"File size {file_size} exceeds maximum {self.max_file_size} bytes")
            
            if file_size == 0:
                raise ValueError("Cannot process empty audio file")
            
            # Download the file
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            audio_data = response['Body'].read()
            
            logger.info("Audio file downloaded successfully", extra={
                "bucket": self.bucket_name,
                "key": s3_key,
                "size_bytes": len(audio_data),
                "content_type": response.get('ContentType', 'unknown')
            })
            
            return audio_data
            
        except ClientError as e:
            aws_lambda_config_manager.handle_aws_error(e, "download_audio_file", s3_key)
            raise
        except Exception as e:
            logger.error("Failed to download audio file", extra={
                "bucket": self.bucket_name,
                "key": s3_key,
                "error": str(e)
            })
            raise
    
    def download_to_temp_file(self, s3_key: str) -> str:
        """
        Download audio file to a temporary file for processing.
        
        Args:
            s3_key: S3 object key for the audio file
            
        Returns:
            Path to temporary file containing audio data
            
        Raises:
            ValueError: If file is invalid
            ClientError: If S3 operation fails
        """
        logger.info("Downloading audio to temporary file", extra={
            "bucket": self.bucket_name,
            "key": s3_key
        })
        
        try:
            # Download audio data
            audio_data = self.download_audio_file(s3_key)
            
            # Create temporary file with appropriate extension
            file_extension = self._get_file_extension(s3_key)
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
                "key": s3_key,
                "error": str(e)
            })
            raise
    
    def get_audio_metadata(self, s3_key: str) -> Dict[str, Any]:
        """
        Get metadata for audio file without downloading content.
        
        Args:
            s3_key: S3 object key for the audio file
            
        Returns:
            Dict with file metadata
            
        Raises:
            ClientError: If S3 operation fails
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            
            metadata = {
                'key': s3_key,
                'size': response['ContentLength'],
                'last_modified': response['LastModified'].isoformat(),
                'etag': response['ETag'].strip('"'),
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'metadata': response.get('Metadata', {})
            }
            
            logger.debug("Retrieved audio metadata", extra=metadata)
            return metadata
            
        except ClientError as e:
            aws_lambda_config_manager.handle_aws_error(e, "get_audio_metadata", s3_key)
            raise
    
    def validate_audio_file(self, s3_key: str) -> Dict[str, Any]:
        """
        Validate audio file properties.
        
        Args:
            s3_key: S3 object key for the audio file
            
        Returns:
            Dict with validation results
        """
        try:
            metadata = self.get_audio_metadata(s3_key)
            
            validation_result = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'metadata': metadata
            }
            
            # Check file size
            if metadata['size'] > self.max_file_size:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"File size {metadata['size']} exceeds maximum {self.max_file_size}")
            
            if metadata['size'] == 0:
                validation_result['is_valid'] = False
                validation_result['errors'].append("File is empty")
            
            # Check file extension
            file_extension = self._get_file_extension(s3_key)
            supported_formats = os.getenv('SUPPORTED_AUDIO_FORMATS', 'wav,mp3,m4a,flac').split(',')
            
            if file_extension.lower() not in [fmt.lower() for fmt in supported_formats]:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Unsupported format: {file_extension}")
            
            # Check content type (warning only)
            content_type = metadata.get('content_type', '')
            if not content_type.startswith('audio/') and content_type != 'application/octet-stream':
                validation_result['warnings'].append(f"Unexpected content type: {content_type}")
            
            logger.info("Audio file validation completed", extra={
                "key": s3_key,
                "is_valid": validation_result['is_valid'],
                "errors": len(validation_result['errors']),
                "warnings": len(validation_result['warnings'])
            })
            
            return validation_result
            
        except Exception as e:
            logger.error("Failed to validate audio file", extra={
                "key": s3_key,
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
    
    def _get_file_extension(self, s3_key: str) -> str:
        """
        Extract file extension from S3 key.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            File extension without dot
        """
        if '.' not in s3_key:
            return ''
        return s3_key.split('.')[-1]
    
    def extract_user_id_from_key(self, s3_key: str) -> str:
        """
        Extract user ID from S3 object key.
        
        Expected format: audio-uploads/{user_id}/sample_{n}.wav
        
        Args:
            s3_key: S3 object key
            
        Returns:
            User ID string
            
        Raises:
            ValueError: If key format is invalid
        """
        try:
            # Remove trigger prefix if present
            trigger_prefix = os.getenv('S3_TRIGGER_PREFIX', 'audio-uploads/')
            
            if not s3_key.startswith(trigger_prefix):
                raise ValueError("Key does not start with expected prefix")
            
            path_after_prefix = s3_key[len(trigger_prefix):]
            
            # Extract user_id (first path component)
            path_parts = path_after_prefix.split('/')
            if not path_parts or not path_parts[0]:
                raise ValueError("Could not extract user_id from key format")
            
            user_id = path_parts[0]
            
            logger.debug("Extracted user ID from S3 key", extra={
                "s3_key": s3_key,
                "user_id": user_id
            })
            
            return user_id
            
        except ValueError:
            # Re-raise ValueError exceptions as-is
            raise
        except Exception as e:
            logger.error("Failed to extract user_id from S3 key", extra={
                "s3_key": s3_key,
                "error": str(e)
            })
            raise ValueError(f"Invalid S3 key format: {s3_key}")
    
    def get_file_info_summary(self, s3_key: str) -> Dict[str, Any]:
        """
        Get comprehensive file information summary.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Dict with complete file information
        """
        try:
            metadata = self.get_audio_metadata(s3_key)
            validation = self.validate_audio_file(s3_key)
            user_id = self.extract_user_id_from_key(s3_key)
            
            summary = {
                'user_id': user_id,
                'file_name': os.path.basename(s3_key),
                'file_extension': self._get_file_extension(s3_key),
                'size_bytes': metadata['size'],
                'size_mb': round(metadata['size'] / (1024 * 1024), 2),
                'last_modified': metadata['last_modified'],
                'content_type': metadata['content_type'],
                'is_valid': validation['is_valid'],
                'validation_errors': validation['errors'],
                'validation_warnings': validation['warnings']
            }
            
            return summary
            
        except Exception as e:
            logger.error("Failed to get file info summary", extra={
                "s3_key": s3_key,
                "error": str(e)
            })
            raise


# Global S3 operations instance for Lambda function
s3_operations = S3AudioOperations()
