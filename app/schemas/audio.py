"""
Storage schemas for Voice Gateway API.
Enhanced schemas for audio sample operations and progress tracking.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from uuid import UUID
from enum import Enum


class SampleFormat(str, Enum):
    """
    Supported audio sample formats.
    """
    WAV = "wav"
    MP3 = "mp3"
    M4A = "m4a"


class AudioUploadRequest(BaseModel):
    """
    Request model for audio sample upload URL generation.
    """
    user_id: str = Field(..., description="User ID for the audio sample")
    sample_number: int = Field(..., ge=1, le=3, description="Sample number (1, 2, or 3)")
    format: SampleFormat = Field(default=SampleFormat.WAV, description="Audio file format")
    expiration_minutes: int = Field(default=15, ge=1, le=60, description="URL expiration time in minutes")
    
    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        """
        Validate user_id format.
        """
        if not v or not v.strip():
            raise ValueError("User ID cannot be empty")
        # Basic UUID validation
        try:
            UUID(v)
        except ValueError:
            raise ValueError("User ID must be a valid UUID")
        return v.strip()


class AudioUploadResponse(BaseModel):
    """
    Response model for audio sample upload URL generation.
    """
    upload_url: str = Field(..., description="Presigned POST URL for upload")
    upload_fields: Dict[str, Any] = Field(..., description="Required form fields for upload")
    file_path: str = Field(..., description="File path in S3")
    sample_id: str = Field(..., description="Generated sample ID")
    sample_number: int = Field(..., description="Sample number (1-3)")
    user_id: str = Field(..., description="User identifier")
    expires_at: str = Field(..., description="URL expiration timestamp")
    max_file_size_bytes: int = Field(..., description="Maximum file size in bytes")
    content_type: str = Field(..., description="Expected content type")
    format: str = Field(..., description="Audio format")
    upload_method: str = Field(default="POST", description="HTTP method for upload")
    upload_instruction: str = Field(
        default="Mi nombre es [YOUR_NAME] y mi contraseña de voz es [YOUR_PASSWORD]",
        description="Instructions for what to say during recording"
    )


class AudioStatusResponse(BaseModel):
    """
    Response model for audio setup status and progress.
    """
    user_id: str = Field(..., description="User identifier")
    total_samples: int = Field(..., description="Total number of samples required")
    completed_samples: int = Field(..., description="Number of samples uploaded")
    progress_percentage: float = Field(..., description="Completion percentage (0-100)")
    sample_details: List[Dict[str, Any]] = Field(default=[], description="List of uploaded sample details")


class AudioSetupStatusResponse(BaseModel):
    """
    Response model for audio setup progress tracking.
    """
    user_id: str = Field(..., description="User identifier")
    samples_uploaded: int = Field(..., description="Number of samples uploaded")
    samples_required: int = Field(default=3, description="Required number of samples")
    setup_complete: bool = Field(..., description="Whether audio setup is complete")
    next_sample_number: Optional[int] = Field(None, description="Next sample number to upload (if not complete)")
    progress_percentage: float = Field(..., description="Completion percentage (0-100)")
    samples: List[Dict[str, Any]] = Field(default=[], description="List of uploaded samples")


class AudioSampleValidationResponse(BaseModel):
    """
    Response model for individual audio sample validation.
    """
    sample_id: str = Field(..., description="Sample identifier")
    sample_number: int = Field(..., description="Sample number")
    user_id: str = Field(..., description="User identifier")
    validation_status: str = Field(..., description="Validation result: success, failed, processing")
    message: str = Field(..., description="Validation message")
    file_path: str = Field(..., description="File path in storage")
    uploaded_at: str = Field(..., description="Upload timestamp")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    duration_seconds: Optional[float] = Field(None, description="Audio duration in seconds")
    transcription: Optional[str] = Field(None, description="Audio transcription (if available)")
    embedding_generated: bool = Field(default=False, description="Whether voice embedding was generated")


class AudioDownloadRequest(BaseModel):
    """
    Request model for audio file download URL generation.
    """
    user_id: str = Field(..., description="User ID for authorization")
    file_path: str = Field(..., description="Relative path to the audio file")
    expiration_minutes: int = Field(default=60, ge=1, le=1440, description="URL expiration time in minutes")
    
    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v):
        """
        Validate file path format.
        """
        if not v or not v.strip():
            raise ValueError("File path cannot be empty")
        return v.strip().lstrip('/')


class AudioDownloadResponse(BaseModel):
    """
    Response model for audio file download URL generation.
    """
    download_url: str = Field(..., description="Presigned GET URL for download")
    file_path: str = Field(..., description="File path in storage")
    expiration_minutes: int = Field(..., description="URL expiration time in minutes")
    access_method: str = Field(default="GET", description="HTTP method for download")


class AudioExistsResponse(BaseModel):
    """
    Response model for audio file existence check.
    """
    file_path: str = Field(..., description="File path that was checked")
    exists: bool = Field(..., description="Whether the file exists")
    storage_service: str = Field(default="s3", description="Storage service type")
    error: Optional[str] = Field(None, description="Error message if check failed")


class AudioDeleteResponse(BaseModel):
    """
    Response model for audio file deletion.
    """
    file_path: str = Field(..., description="File path that was deleted")
    deleted: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Result message")


class AudioInfoResponse(BaseModel):
    """
    Response model for audio storage service information.
    """
    service_type: str = Field(..., description="Storage service type")
    bucket_name: str = Field(..., description="S3 bucket name")
    region: str = Field(..., description="AWS region")
    use_local_s3: bool = Field(..., description="Whether using local S3 (MinIO)")
    endpoint_url: Optional[str] = Field(None, description="S3 endpoint URL")
    max_file_size_mb: int = Field(..., description="Maximum file size in MB")
    allowed_formats: List[str] = Field(..., description="Allowed audio formats")
    upload_expiration_default: int = Field(..., description="Default upload URL expiration in minutes")
    download_expiration_default: int = Field(..., description="Default download URL expiration in minutes")
    api_version: str = Field(..., description="API version")
    supported_operations: List[str] = Field(..., description="List of supported operations")
    voice_sample_support: bool = Field(default=True, description="Whether voice samples are supported")
    individual_upload_support: bool = Field(default=True, description="Whether individual uploads are supported")
    voice_sample_features: Optional[dict] = Field(None, description="Voice sample specific features") 