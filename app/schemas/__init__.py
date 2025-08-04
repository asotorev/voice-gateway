"""
Schemas module for Voice Gateway API.
Contains Pydantic models for request/response validation.
"""

from .user import UserRegisterRequest, UserRegisterResponse, UserResponse
from .audio import (
    UploadUrlRequest,
    UploadUrlResponse,
    DownloadUrlRequest,
    DownloadUrlResponse,
    FileExistsResponse,
    DeleteFileResponse,
    StorageInfoResponse
)

__all__ = [
    "UserRegisterRequest",
    "UserRegisterResponse", 
    "UserResponse",
    "UploadUrlRequest",
    "UploadUrlResponse",
    "DownloadUrlRequest",
    "DownloadUrlResponse",
    "FileExistsResponse",
    "DeleteFileResponse",
    "StorageInfoResponse"
]
