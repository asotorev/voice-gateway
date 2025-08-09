"""
Audio sample domain model.

This module defines the AudioSample entity representing a voice sample
in the domain layer, following Clean Architecture principles.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


@dataclass
class AudioSample:
    """
    Domain entity representing an audio sample.
    
    Contains the essential data and business rules for voice samples
    used in registration and authentication processes.
    """
    
    file_path: str
    file_size_bytes: int
    format: str
    user_id: str
    sample_metadata: Dict[str, Any]
    
    # Optional fields set during processing
    embedding: Optional[List[float]] = None
    quality_score: Optional[float] = None
    processing_timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate audio sample data after initialization."""
        if self.file_size_bytes <= 0:
            raise ValueError("File size must be positive")
        
        if not self.user_id:
            raise ValueError("User ID is required")
        
        if not self.file_path:
            raise ValueError("File path is required")
    
    @classmethod
    def create(
        cls,
        file_path: str,
        file_size_bytes: int,
        format: str,
        user_id: str,
        sample_metadata: Dict[str, Any]
    ) -> "AudioSample":
        """
        Create a new AudioSample instance.
        
        Args:
            file_path: S3 path to the audio file
            file_size_bytes: Size of the audio file in bytes
            format: Audio format (wav, mp3, etc.)
            user_id: User identifier
            sample_metadata: Additional metadata about the sample
            
        Returns:
            New AudioSample instance
        """
        return cls(
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            format=format,
            user_id=user_id,
            sample_metadata=sample_metadata
        )
    
    def set_processing_result(
        self,
        embedding: List[float],
        quality_score: float
    ) -> None:
        """
        Set the processing results for this audio sample.
        
        Args:
            embedding: Generated voice embedding
            quality_score: Quality assessment score (0.0 to 1.0)
        """
        if not isinstance(embedding, list) or len(embedding) == 0:
            raise ValueError("Embedding must be a non-empty list")
        
        if not (0.0 <= quality_score <= 1.0):
            raise ValueError("Quality score must be between 0.0 and 1.0")
        
        self.embedding = embedding
        self.quality_score = quality_score
        self.processing_timestamp = datetime.now(timezone.utc)
    
    def is_processed(self) -> bool:
        """
        Check if this audio sample has been processed.
        
        Returns:
            True if embedding and quality score are set
        """
        return self.embedding is not None and self.quality_score is not None
    
    def get_file_info(self) -> Dict[str, Any]:
        """
        Get file information as a dictionary.
        
        Returns:
            Dict with file information
        """
        return {
            'file_path': self.file_path,
            'file_size_bytes': self.file_size_bytes,
            'format': self.format,
            'sample_metadata': self.sample_metadata
        }
