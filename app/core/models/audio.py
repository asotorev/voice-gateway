"""
Audio domain models for Voice Gateway.
Pure domain entities without infrastructure dependencies.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional


class AudioFormat(Enum):
    """Supported audio formats."""
    WAV = "wav"
    MP3 = "mp3"
    M4A = "m4a"


@dataclass
class AudioUploadRequest:
    """Domain model for audio upload request."""
    user_id: str
    sample_number: int
    format: AudioFormat
    expiration_minutes: int = 15


@dataclass
class AudioUploadResponse:
    """Domain model for audio upload response."""
    upload_url: str
    upload_fields: Dict[str, str]
    file_path: str
    audio_id: str
    audio_number: int
    user_id: str
    expires_at: str
    max_file_size_bytes: int
    content_type: str
    format: str
    upload_method: str
    upload_instruction: str


@dataclass
class AudioDownloadResponse:
    """Domain model for audio download response."""
    download_url: str
    file_path: str
    expiration_minutes: int
    access_method: str = "GET"


@dataclass
class AudioDeleteResponse:
    """Domain model for audio file deletion response."""
    file_path: str
    deleted: bool
    message: str


class AudioStorageError(Exception):
    """Domain exception for audio storage errors."""
    def __init__(self, message: str, operation: str = "", file_path: str = ""):
        self.message = message
        self.operation = operation
        self.file_path = file_path
        super().__init__(self.message)


@dataclass
class AudioUploadData:
    """Domain model for S3 upload data."""
    upload_url: str
    upload_fields: Dict[str, str]
    file_path: str
    expires_at: str
    bucket_name: str
    content_type: str
    max_file_size_bytes: Optional[int]
    upload_method: str = "POST"


@dataclass
class AudioServiceInfo:
    """Domain model for audio service configuration."""
    service_type: str
    bucket_name: str
    region: str
    use_local_s3: bool
    endpoint_url: Optional[str]
    use_ssl: bool
    max_file_size_mb: int
    allowed_formats: List[str]
    upload_expiration_default: int
    download_expiration_default: int
    voice_sample_support: bool
    individual_upload_support: bool


@dataclass
class AudioFileInfo:
    """Domain model for audio file metadata."""
    key: str
    size: int
    last_modified: str
    etag: str


@dataclass
class AudioSampleDetail:
    """Domain model for individual audio sample details."""
    key: str
    size: int
    last_modified: str
    etag: str


@dataclass
class AudioStatusResponse:
    """Domain model for audio setup status response."""
    user_id: str
    total_samples: int
    completed_samples: int
    progress_percentage: float
    sample_details: List[AudioSampleDetail]


@dataclass
class AudioSetupProgress:
    """Domain model for voice setup progress."""
    samples_uploaded: int
    samples_required: int
    setup_complete: bool
    progress_percentage: float
    next_sample_number: Optional[int]


@dataclass
class AudioSampleRequirements:
    """Domain model for voice sample requirements."""
    required_samples: int
    supported_formats: List[str]
    max_file_size_mb: int
    min_duration_seconds: int
    max_duration_seconds: int
    sample_instruction_template: str
    validation_required: bool
    embedding_generation: bool 