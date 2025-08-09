"""
Voice embedding domain model.

This module defines the VoiceEmbedding entity representing processed
voice data in the domain layer, following Clean Architecture principles.
"""
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime, timezone


@dataclass
class VoiceEmbedding:
    """
    Domain entity representing a processed voice embedding.
    
    Contains the voice embedding vector and associated metadata
    for user voice authentication and recognition.
    """
    
    embedding: List[float]
    quality_score: float
    user_id: str
    sample_metadata: Dict[str, Any]
    created_at: datetime
    processor_info: Dict[str, Any]
    
    def __post_init__(self):
        """Validate voice embedding data after initialization."""
        if not isinstance(self.embedding, list) or len(self.embedding) == 0:
            raise ValueError("Embedding must be a non-empty list")
        
        if not (0.0 <= self.quality_score <= 1.0):
            raise ValueError("Quality score must be between 0.0 and 1.0")
        
        if not self.user_id:
            raise ValueError("User ID is required")
    
    @classmethod
    def create(
        cls,
        embedding: List[float],
        quality_score: float,
        user_id: str,
        sample_metadata: Dict[str, Any],
        processor_info: Dict[str, Any]
    ) -> "VoiceEmbedding":
        """
        Create a new VoiceEmbedding instance.
        
        Args:
            embedding: Voice embedding vector
            quality_score: Quality assessment score (0.0 to 1.0)
            user_id: User identifier
            sample_metadata: Metadata about the audio sample
            processor_info: Information about the processor used
            
        Returns:
            New VoiceEmbedding instance
        """
        return cls(
            embedding=embedding,
            quality_score=quality_score,
            user_id=user_id,
            sample_metadata=sample_metadata,
            created_at=datetime.now(timezone.utc),
            processor_info=processor_info
        )
    
    def get_embedding_dimensions(self) -> int:
        """
        Get the number of dimensions in the embedding vector.
        
        Returns:
            Number of embedding dimensions
        """
        return len(self.embedding)
    
    def is_high_quality(self, threshold: float = 0.7) -> bool:
        """
        Check if this embedding meets quality standards.
        
        Args:
            threshold: Minimum quality score threshold
            
        Returns:
            True if quality score is above threshold
        """
        return self.quality_score >= threshold
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of this voice embedding.
        
        Returns:
            Dict with embedding summary information
        """
        return {
            'user_id': self.user_id,
            'dimensions': self.get_embedding_dimensions(),
            'quality_score': self.quality_score,
            'is_high_quality': self.is_high_quality(),
            'created_at': self.created_at.isoformat(),
            'processor_type': self.processor_info.get('processor_type', 'unknown')
        }
