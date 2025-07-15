"""
Audio processing business rules and constraints.
Domain-level constants that define audio validation and processing rules.
"""


class AudioConstraints:
    """
    Business rules for audio processing in voice authentication.
    These are domain rules that remain constant across environments.
    """
    
    # Audio Quality Requirements
    SAMPLE_RATE = 16000  # Standard sample rate for voice processing
    MIN_DURATION_SECONDS = 2  # Minimum audio duration for processing
    MAX_DURATION_SECONDS = 30  # Maximum audio duration for processing
    
    # File Size Limits (Business Rules)
    MAX_AUDIO_FILE_SIZE_MB = 10  # Business rule for audio files
    MAX_GENERAL_FILE_SIZE_MB = 50  # Business rule for other files
    
    # Supported Formats (Domain Knowledge)
    ALLOWED_AUDIO_FORMATS = ["wav", "mp3", "m4a"]
    ALLOWED_AUDIO_MIME_TYPES = [
        "audio/wav",
        "audio/mpeg", 
        "audio/mp4",
        "audio/x-m4a"
    ]
    
    # Registration Requirements
    REQUIRED_AUDIO_SAMPLES_COUNT = 3  # Number of samples needed for registration
    
    @classmethod
    def get_max_audio_file_size_bytes(cls) -> int:
        """Get maximum audio file size in bytes."""
        return cls.MAX_AUDIO_FILE_SIZE_MB * 1024 * 1024
    
    @classmethod
    def get_max_general_file_size_bytes(cls) -> int:
        """Get maximum general file size in bytes."""
        return cls.MAX_GENERAL_FILE_SIZE_MB * 1024 * 1024
    
    @classmethod
    def is_valid_audio_format(cls, file_extension: str) -> bool:
        """Check if audio format is allowed."""
        return file_extension.lower() in cls.ALLOWED_AUDIO_FORMATS
    
    @classmethod
    def is_valid_mime_type(cls, mime_type: str) -> bool:
        """Check if MIME type is allowed."""
        return mime_type.lower() in cls.ALLOWED_AUDIO_MIME_TYPES 