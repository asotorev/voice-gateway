"""
S3 Audio Storage Adapter for Voice Gateway.
Pure infrastructure implementation - only S3 operations.
"""
from datetime import datetime, timedelta, timezone
from typing import List
from botocore.exceptions import ClientError, NoCredentialsError
from app.core.ports.audio_storage import AudioStorageServicePort, AudioStorageError
from app.core.models import AudioFormat, AudioUploadData, AudioServiceInfo, AudioFileInfo
from app.core.services.audio_constraints import AudioConstraints
from app.infrastructure.config.aws_config import aws_config
from app.infrastructure.config.infrastructure_settings import infra_settings


class AudioStorageAdapter(AudioStorageServicePort):
    """
    S3 implementation of AudioStorageServicePort.
    
    ONLY handles technical storage operations.
    """
    
    def __init__(self):
        """Initialize storage adapter with AWS configuration."""
        self.s3_client = aws_config.s3_client
        self.bucket_name = infra_settings.s3_bucket_name
        self._bucket_checked = False
    
    def _ensure_bucket_exists(self):
        """Lazy bucket existence check and creation."""
        if self._bucket_checked:
            return
            
        try:
            from app.infrastructure.storage.s3_setup import S3Setup
            s3_setup = S3Setup()
            
            if not s3_setup.bucket_exists(self.bucket_name):
                s3_setup.setup_audio_bucket()
            
            self._bucket_checked = True
            
        except Exception:
            # Don't retry on failure
            self._bucket_checked = True

    
    async def generate_presigned_upload_url(
        self,
        file_path: str,
        content_type: str,
        expiration_minutes: int,
        max_file_size_bytes: int = None
    ) -> AudioUploadData:
        """
        Generate S3 presigned upload URL.
        
        Args:
            file_path: S3 key path
            content_type: MIME type
            expiration_minutes: URL expiration
            max_file_size_bytes: Size limit for S3 conditions
            
        Returns:
            AudioUploadData with S3 presigned POST data
            
        Raises:
            AudioStorageError: If S3 operation fails
        """
        try:
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
            # Calculate expiration
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)
            
            # Prepare S3 conditions
            conditions = []
            fields = {'Content-Type': content_type}
            
            # Add file size validation if specified
            if max_file_size_bytes:
                conditions.extend([
                    ["content-length-range", 1, max_file_size_bytes],
                    ["starts-with", "$Content-Type", content_type.split('/')[0]]
                ])
            
            # Add content type validation
            conditions.append(["eq", "$Content-Type", content_type])
            
            # Generate S3 presigned POST
            presigned_post = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=file_path,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expiration_minutes * 60
            )
            
            return AudioUploadData(
                upload_url=presigned_post['url'],
                upload_fields=presigned_post['fields'],
                file_path=file_path,
                expires_at=expires_at.isoformat() + 'Z',
                bucket_name=self.bucket_name,
                content_type=content_type,
                max_file_size_bytes=max_file_size_bytes,
                upload_method='POST'
            )
            
        except ClientError as e:
            raise self._handle_client_error(e, "generate_presigned_upload_url", file_path)
        except NoCredentialsError:
            raise AudioStorageError("S3 credentials not configured", "generate_presigned_upload_url", file_path)
        except Exception as e:
            raise AudioStorageError(f"Failed to generate upload URL: {str(e)}", "generate_presigned_upload_url", file_path)
    
    async def generate_presigned_download_url(
        self,
        file_path: str,
        expiration_minutes: int
    ) -> str:
        """
        Generate S3 presigned download URL.
        
        Args:
            file_path: S3 key path
            expiration_minutes: URL expiration
            
        Returns:
            Presigned GET URL
            
        Raises:
            AudioStorageError: If S3 operation fails
        """
        try:
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
            # Generate S3 presigned GET URL
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_path
                },
                ExpiresIn=expiration_minutes * 60
            )
            
            return presigned_url
            
        except ClientError as e:
            raise self._handle_client_error(e, "generate_presigned_download_url", file_path)
        except NoCredentialsError:
            raise AudioStorageError("S3 credentials not configured", "generate_presigned_download_url", file_path)
        except Exception as e:
            raise AudioStorageError(f"Failed to generate download URL: {str(e)}", "generate_presigned_download_url", file_path)
    
    async def audio_file_exists(self, file_path: str) -> bool:
        """
        Check if file exists in S3.
        
        Args:
            file_path: S3 key path
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            if not file_path:
                return False
            
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
            # S3 head_object operation
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] in ['NoSuchKey', '404']:
                return False
            else:
                # Log other errors but don't raise
                return False
        except Exception:
            # For any other error, return False
            return False
    
    async def delete_audio_file(self, file_path: str) -> bool:
        """
        Delete file from S3.
        
        Args:
            file_path: S3 key path
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            AudioStorageError: If S3 operation fails
        """
        try:
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
            # S3 delete operation
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return False
            else:
                raise self._handle_client_error(e, "delete_file", file_path)
        except NoCredentialsError:
            raise AudioStorageError("S3 credentials not configured", "delete_file", file_path)
        except Exception as e:
            raise AudioStorageError(f"Failed to delete file: {str(e)}", "delete_file", file_path)
    
    async def list_files_by_prefix(self, prefix: str) -> List[AudioFileInfo]:
        """
        List files in S3 by prefix.
        
        Args:
            prefix: S3 key prefix to filter
            
        Returns:
            List of AudioFileInfo objects
            
        Raises:
            AudioStorageError: If S3 operation fails
        """
        try:
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
            # S3 list objects operation
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append(AudioFileInfo(
                    key=obj['Key'],
                    size=obj['Size'],
                    last_modified=obj['LastModified'].isoformat(),
                    etag=obj['ETag'].strip('"')
                ))
            
            return files
            
        except ClientError as e:
            raise self._handle_client_error(e, "list_files_by_prefix", prefix)
        except NoCredentialsError:
            raise AudioStorageError("S3 credentials not configured", "list_files_by_prefix", prefix)
        except Exception as e:
            raise AudioStorageError(f"Failed to list files: {str(e)}", "list_files_by_prefix", prefix)

    # ERROR HANDLING
    
    def _handle_client_error(self, error: ClientError, operation: str, file_path: str) -> AudioStorageError:
        """Handle AWS client errors and convert to AudioStorageError."""
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        
        if error_code == 'NoSuchBucket':
            return AudioStorageError(f"S3 bucket not found: {self.bucket_name}", operation, file_path)
        elif error_code == 'NoSuchKey':
            return AudioStorageError(f"File not found: {file_path}", operation, file_path)
        elif error_code == 'AccessDenied':
            return AudioStorageError("Access denied to S3 bucket", operation, file_path)
        else:
            return AudioStorageError(f"AWS error ({error_code}): {error_message}", operation, file_path)

    # SERVICE INFORMATION
    
    def get_audio_service_info(self) -> AudioServiceInfo:
        """
        Get storage service technical information.
        
        Returns:
            AudioServiceInfo with S3 technical configuration
        """
        return AudioServiceInfo(
            service_type="s3",
            bucket_name=self.bucket_name,
            region=infra_settings.aws_region,
            use_local_s3=infra_settings.use_local_s3,
            endpoint_url=infra_settings.s3_endpoint_url,
            use_ssl=infra_settings.s3_use_ssl,
            max_file_size_mb=AudioConstraints.MAX_GENERAL_FILE_SIZE_MB,
            allowed_formats=AudioConstraints.ALLOWED_AUDIO_FORMATS,
            upload_expiration_default=15,
            download_expiration_default=5,
            voice_sample_support=True,
            individual_upload_support=True
        )
    
    def get_supported_audio_formats(self) -> list[AudioFormat]:
        """
        Get list of supported audio formats.
        
        Returns:
            List of AudioFormat enum values
        """
        return list(AudioFormat) 