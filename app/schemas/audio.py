"""
Storage schemas for Voice Gateway API.
Defines request and response models for storage operations.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime


class UploadUrlRequest(BaseModel):
    """
    Request schema for generating upload URL.
    """
    file_path: str = Field(..., description="Relative path where file will be stored")
    content_type: str = Field(default="audio/wav", description="MIME type of the file")
    expiration_minutes: int = Field(default=15, ge=1, le=60, description="URL expiration time in minutes")


class UploadUrlResponse(BaseModel):
    """
    Response schema for upload URL generation.
    """
    upload_url: str
    upload_fields: Dict[str, Any]
    file_path: str
    expires_at: str
    max_file_size_bytes: int
    upload_method: str = "POST"
    content_type: str


class DownloadUrlRequest(BaseModel):
    """
    Request schema for generating download URL.
    """
    file_path: str = Field(..., description="Relative path to the file")
    expiration_minutes: int = Field(default=60, ge=1, le=1440, description="URL expiration time in minutes")


class DownloadUrlResponse(BaseModel):
    """
    Response schema for download URL generation.
    """
    download_url: str
    file_path: str
    expiration_minutes: int
    access_method: str = "GET"


class FileExistsResponse(BaseModel):
    """
    Response schema for file existence check.
    """
    file_path: str
    exists: bool
    storage_service: str = "s3"
    error: Optional[str] = None


class DeleteFileResponse(BaseModel):
    """
    Response schema for file deletion.
    """
    file_path: str
    deleted: bool
    message: str


class StorageInfoResponse(BaseModel):
    """
    Response schema for storage service information.
    """
    api_version: str = "1.0"
    supported_operations: list[str]
    storage_service: str = "s3"
    bucket_name: str
    region: str
    max_file_size_mb: int
    upload_expiration_minutes: int
    download_expiration_minutes: int 