"""
Core domain models for Voice Gateway.
"""
from .user import (
    User,
    UserProfile,
    UserList,
    UserAuthenticationStatus,
    UserRegistrationStatus
)

from .audio import (
    AudioFormat,
    AudioUploadRequest,
    AudioUploadResponse,
    AudioDownloadResponse,
    AudioDeleteResponse,
    AudioStatusResponse,
    AudioStorageError,
    AudioUploadData,
    AudioServiceInfo,
    AudioFileInfo,
    AudioSetupProgress,
    AudioSampleRequirements,
    AudioSampleDetail
)

__all__ = [
    "User",
    "UserProfile",
    "UserList",
    "UserAuthenticationStatus",
    "UserRegistrationStatus",
    "AudioFormat",
    "AudioUploadRequest",
    "AudioUploadResponse",
    "AudioDownloadResponse",
    "AudioDeleteResponse",
    "AudioStatusResponse",
    "AudioStorageError",
    "AudioUploadData",
    "AudioServiceInfo",
    "AudioFileInfo",
    "AudioSetupProgress",
    "AudioSampleRequirements",
    "AudioSampleDetail"
]
