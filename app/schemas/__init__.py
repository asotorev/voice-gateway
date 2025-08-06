"""
Schemas module for Voice Gateway API.
Contains Pydantic models for request/response validation.
"""

from .user import UserRegisterRequest, UserRegisterResponse, UserResponse, UserVoiceStatus
from .audio import (
    # Audio Upload Schemas
    AudioUploadRequest,
    AudioUploadResponse,
    AudioSetupStatusResponse,
    AudioSampleValidationResponse,
    
    # Audio Storage Operations Schemas
    AudioDownloadRequest,
    AudioDownloadResponse,
    AudioExistsResponse,
    AudioDeleteResponse,
    AudioInfoResponse,
    
    # Enums
    SampleFormat
)

__all__ = [
    # User Schemas
    "UserRegisterRequest",
    "UserRegisterResponse", 
    "UserResponse",
    "UserVoiceStatus",
    
    # Audio Upload Schemas
    "AudioUploadRequest",
    "AudioUploadResponse",
    "AudioSetupStatusResponse",
    "AudioSampleValidationResponse",
    
    # Audio Storage Operations Schemas
    "AudioDownloadRequest",
    "AudioDownloadResponse",
    "AudioExistsResponse",
    "AudioDeleteResponse",
    "AudioInfoResponse",
    
    # Enums
    "SampleFormat"
]
