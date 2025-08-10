"""
Voice Authentication Service.

Provides voice authentication capabilities through embedding comparison,
similarity scoring, and confidence analysis for voice-based user authentication.

This service is part of the shared layer and can be used by multiple
Lambda functions for consistent voice authentication processing.
"""
import os
import logging
import threading
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AuthenticationResult(Enum):
    """Authentication result status."""
    AUTHENTICATED = "authenticated"
    REJECTED = "rejected"
    INSUFFICIENT_DATA = "insufficient_data"
    INVALID_INPUT = "invalid_input"


@dataclass
class VoiceAuthenticationConfig:
    """Configuration for voice authentication service."""
    
    # Similarity thresholds
    minimum_similarity_threshold: float = 0.75  # Minimum similarity to consider match
    high_confidence_threshold: float = 0.85     # High confidence threshold
    authentication_threshold: float = 0.80      # Final authentication threshold
    
    # Multi-embedding analysis
    minimum_embeddings_required: int = 1        # Minimum stored embeddings needed
    use_average_scoring: bool = True             # Use average of all similarities
    use_max_scoring: bool = True                 # Consider maximum similarity
    confidence_weight_average: float = 0.6      # Weight for average score
    confidence_weight_max: float = 0.4          # Weight for max score
    
    # Quality requirements
    minimum_embedding_dimensions: int = 256     # Expected embedding dimensions
    quality_score_weight: float = 0.1           # Weight of quality in final score
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not (0.0 <= self.minimum_similarity_threshold <= 1.0):
            raise ValueError("minimum_similarity_threshold must be between 0.0 and 1.0")
        if not (0.0 <= self.high_confidence_threshold <= 1.0):
            raise ValueError("high_confidence_threshold must be between 0.0 and 1.0")
        if not (0.0 <= self.authentication_threshold <= 1.0):
            raise ValueError("authentication_threshold must be between 0.0 and 1.0")
        if self.minimum_embeddings_required < 1:
            raise ValueError("minimum_embeddings_required must be at least 1")
    
    @classmethod
    def from_environment(cls) -> "VoiceAuthenticationConfig":
        """Create configuration from environment variables."""
        return cls(
            minimum_similarity_threshold=float(os.getenv('VOICE_AUTH_MIN_SIMILARITY', '0.75')),
            high_confidence_threshold=float(os.getenv('VOICE_AUTH_HIGH_CONFIDENCE', '0.85')),
            authentication_threshold=float(os.getenv('VOICE_AUTH_THRESHOLD', '0.80')),
            minimum_embeddings_required=int(os.getenv('VOICE_AUTH_MIN_EMBEDDINGS', '1')),
            use_average_scoring=os.getenv('VOICE_AUTH_USE_AVERAGE', 'true').lower() == 'true',
            use_max_scoring=os.getenv('VOICE_AUTH_USE_MAX', 'true').lower() == 'true',
            confidence_weight_average=float(os.getenv('VOICE_AUTH_WEIGHT_AVG', '0.6')),
            confidence_weight_max=float(os.getenv('VOICE_AUTH_WEIGHT_MAX', '0.4')),
            quality_score_weight=float(os.getenv('VOICE_AUTH_QUALITY_WEIGHT', '0.1')),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'minimum_similarity_threshold': self.minimum_similarity_threshold,
            'high_confidence_threshold': self.high_confidence_threshold,
            'authentication_threshold': self.authentication_threshold,
            'minimum_embeddings_required': self.minimum_embeddings_required,
            'use_average_scoring': self.use_average_scoring,
            'use_max_scoring': self.use_max_scoring,
            'confidence_weight_average': self.confidence_weight_average,
            'confidence_weight_max': self.confidence_weight_max,
            'minimum_embedding_dimensions': self.minimum_embedding_dimensions,
            'quality_score_weight': self.quality_score_weight
        }


class VoiceAuthenticationService:
    """
    Voice authentication service for embedding comparison and similarity analysis.
    
    Provides comprehensive voice authentication capabilities including:
    - Cosine similarity calculation between voice embeddings
    - Multi-embedding scoring and confidence analysis  
    - Configurable authentication thresholds
    - Quality-weighted authentication decisions
    """
    
    def __init__(self, config: Optional[VoiceAuthenticationConfig] = None):
        """
        Initialize the voice authentication service.
        
        Args:
            config: Authentication configuration, defaults to environment-based config
        """
        self.config = config or VoiceAuthenticationConfig.from_environment()
        self._lock = threading.Lock()
        
        logger.info("Voice authentication service initialized", extra=self.config.to_dict())
    
    def calculate_cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two voice embeddings.
        
        Args:
            embedding1: First voice embedding vector
            embedding2: Second voice embedding vector
            
        Returns:
            Cosine similarity score between 0.0 and 1.0
            
        Raises:
            ValueError: If embeddings are invalid or incompatible
        """
        # Validate inputs
        if not embedding1 or not embedding2:
            raise ValueError("Embeddings cannot be empty")
        
        if len(embedding1) != len(embedding2):
            raise ValueError(f"Embedding dimensions mismatch: {len(embedding1)} vs {len(embedding2)}")
        
        if len(embedding1) != self.config.minimum_embedding_dimensions:
            logger.warning("Unexpected embedding dimensions", extra={
                "expected": self.config.minimum_embedding_dimensions,
                "actual": len(embedding1)
            })
        
        try:
            # Convert to numpy arrays for efficient computation
            vec1 = np.array(embedding1, dtype=np.float32)
            vec2 = np.array(embedding2, dtype=np.float32)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                logger.warning("Zero-norm embedding detected")
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # Ensure result is in valid range [0, 1]
            # Cosine similarity is in [-1, 1], but for voice embeddings we expect [0, 1]
            similarity = max(0.0, min(1.0, float(similarity)))
            
            logger.debug("Cosine similarity calculated", extra={
                "similarity": similarity,
                "dot_product": float(dot_product),
                "norm1": float(norm1),
                "norm2": float(norm2)
            })
            
            return similarity
            
        except Exception as e:
            logger.error("Failed to calculate cosine similarity", extra={
                "error": str(e),
                "embedding1_len": len(embedding1),
                "embedding2_len": len(embedding2)
            })
            raise ValueError(f"Similarity calculation failed: {e}")
    
    def compare_against_stored_embeddings(
        self, 
        input_embedding: List[float], 
        stored_embeddings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare input embedding against multiple stored embeddings.
        
        Args:
            input_embedding: The input voice embedding to authenticate
            stored_embeddings: List of stored embeddings with metadata
            
        Returns:
            Dictionary with similarity analysis results including:
            - similarities: List of individual similarity scores
            - average_similarity: Average similarity across all comparisons
            - max_similarity: Maximum similarity found
            - min_similarity: Minimum similarity found
            - total_comparisons: Number of embeddings compared
            - quality_weighted_average: Quality-weighted average similarity
            
        Raises:
            ValueError: If insufficient data or invalid inputs
        """
        with self._lock:
            if not input_embedding:
                raise ValueError("Input embedding cannot be empty")
            
            if not stored_embeddings:
                raise ValueError("No stored embeddings provided for comparison")
            
            if len(stored_embeddings) < self.config.minimum_embeddings_required:
                raise ValueError(f"Insufficient stored embeddings: {len(stored_embeddings)} < {self.config.minimum_embeddings_required}")
            
            logger.info("Starting embedding comparison", extra={
                "input_dimensions": len(input_embedding),
                "stored_count": len(stored_embeddings)
            })
            
            similarities = []
            quality_scores = []
            comparison_details = []
            
            for i, stored_data in enumerate(stored_embeddings):
                try:
                    stored_embedding = stored_data.get('embedding', [])
                    quality_score = stored_data.get('quality_score', 1.0)
                    
                    if not stored_embedding:
                        logger.warning(f"Empty stored embedding at index {i}")
                        continue
                    
                    similarity = self.calculate_cosine_similarity(input_embedding, stored_embedding)
                    similarities.append(similarity)
                    quality_scores.append(quality_score)
                    
                    comparison_details.append({
                        'index': i,
                        'similarity': similarity,
                        'quality_score': quality_score,
                        'created_at': stored_data.get('created_at'),
                        'audio_metadata': stored_data.get('audio_metadata', {})
                    })
                    
                    logger.debug(f"Embedding {i} similarity: {similarity:.4f}, quality: {quality_score:.4f}")
                    
                except Exception as e:
                    logger.warning(f"Failed to compare embedding {i}: {e}")
                    continue
            
            if not similarities:
                raise ValueError("No valid similarities could be calculated")
            
            # Calculate statistics
            average_similarity = float(np.mean(similarities))
            max_similarity = float(np.max(similarities))
            min_similarity = float(np.min(similarities))
            
            # Calculate quality-weighted average
            if quality_scores:
                weights = np.array(quality_scores)
                weighted_similarities = np.array(similarities) * weights
                quality_weighted_average = float(np.sum(weighted_similarities) / np.sum(weights))
            else:
                quality_weighted_average = average_similarity
            
            result = {
                'similarities': similarities,
                'average_similarity': average_similarity,
                'max_similarity': max_similarity,
                'min_similarity': min_similarity,
                'quality_weighted_average': quality_weighted_average,
                'total_comparisons': len(similarities),
                'comparison_details': comparison_details,
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info("Embedding comparison completed", extra={
                'total_comparisons': len(similarities),
                'average_similarity': average_similarity,
                'max_similarity': max_similarity,
                'quality_weighted_average': quality_weighted_average
            })
            
            return result
    
    def calculate_authentication_confidence(self, comparison_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate authentication confidence based on similarity comparison results.
        
        Args:
            comparison_result: Result from compare_against_stored_embeddings
            
        Returns:
            Dictionary with confidence analysis including:
            - confidence_score: Final confidence score [0.0, 1.0]
            - authentication_result: AuthenticationResult enum
            - decision_factors: Breakdown of decision components
            - meets_threshold: Boolean if authentication threshold is met
            
        """
        average_sim = comparison_result['average_similarity']
        max_sim = comparison_result['max_similarity']
        quality_weighted_avg = comparison_result['quality_weighted_average']
        total_comparisons = comparison_result['total_comparisons']
        
        # Calculate weighted confidence score
        confidence_components = {}
        
        if self.config.use_average_scoring:
            avg_component = average_sim * self.config.confidence_weight_average
            confidence_components['average_weighted'] = avg_component
        else:
            confidence_components['average_weighted'] = 0.0
        
        if self.config.use_max_scoring:
            max_component = max_sim * self.config.confidence_weight_max
            confidence_components['max_weighted'] = max_component
        else:
            confidence_components['max_weighted'] = 0.0
        
        # Base confidence from weighted scoring
        base_confidence = (
            confidence_components['average_weighted'] + 
            confidence_components['max_weighted']
        )
        
        # Quality adjustment
        quality_adjustment = (quality_weighted_avg - average_sim) * self.config.quality_score_weight
        confidence_components['quality_adjustment'] = quality_adjustment
        
        # Sample size confidence boost (more samples = higher confidence)
        sample_boost = min(0.05, (total_comparisons - 1) * 0.01)
        confidence_components['sample_size_boost'] = sample_boost
        
        # Final confidence score
        final_confidence = base_confidence + quality_adjustment + sample_boost
        final_confidence = max(0.0, min(1.0, final_confidence))
        
        # Determine authentication result
        if final_confidence >= self.config.authentication_threshold:
            if final_confidence >= self.config.high_confidence_threshold:
                auth_result = AuthenticationResult.AUTHENTICATED
            else:
                auth_result = AuthenticationResult.AUTHENTICATED  # Still authenticated, just lower confidence
        else:
            auth_result = AuthenticationResult.REJECTED
        
        # Check for insufficient data
        if total_comparisons < self.config.minimum_embeddings_required:
            auth_result = AuthenticationResult.INSUFFICIENT_DATA
        
        result = {
            'confidence_score': final_confidence,
            'authentication_result': auth_result.value,
            'meets_threshold': final_confidence >= self.config.authentication_threshold,
            'is_high_confidence': final_confidence >= self.config.high_confidence_threshold,
            'decision_factors': {
                'base_confidence': base_confidence,
                'components': confidence_components,
                'total_comparisons': total_comparisons,
                'thresholds': {
                    'authentication': self.config.authentication_threshold,
                    'high_confidence': self.config.high_confidence_threshold,
                    'minimum_similarity': self.config.minimum_similarity_threshold
                }
            },
            'calculated_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Authentication confidence calculated", extra={
            'confidence_score': final_confidence,
            'authentication_result': auth_result.value,
            'meets_threshold': result['meets_threshold'],
            'total_comparisons': total_comparisons
        })
        
        return result
    
    def authenticate_voice(
        self, 
        input_embedding: List[float], 
        stored_embeddings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Complete voice authentication workflow.
        
        Combines embedding comparison and confidence calculation into a single
        authentication decision with detailed analysis.
        
        Args:
            input_embedding: Voice embedding to authenticate
            stored_embeddings: User's stored voice embeddings
            
        Returns:
            Complete authentication result with similarity analysis and confidence
            
        Raises:
            ValueError: If inputs are invalid or insufficient
        """
        logger.info("Starting voice authentication", extra={
            "input_embedding_dims": len(input_embedding) if input_embedding else 0,
            "stored_embeddings_count": len(stored_embeddings) if stored_embeddings else 0
        })
        
        try:
            # Perform embedding comparison
            comparison_result = self.compare_against_stored_embeddings(input_embedding, stored_embeddings)
            
            # Calculate authentication confidence
            confidence_result = self.calculate_authentication_confidence(comparison_result)
            
            # Combine results
            authentication_result = {
                'authentication_successful': confidence_result['meets_threshold'],
                'confidence_score': confidence_result['confidence_score'],
                'authentication_result': confidence_result['authentication_result'],
                'is_high_confidence': confidence_result['is_high_confidence'],
                'similarity_analysis': comparison_result,
                'confidence_analysis': confidence_result,
                'configuration': self.config.to_dict(),
                'processed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info("Voice authentication completed", extra={
                'authentication_successful': authentication_result['authentication_successful'],
                'confidence_score': authentication_result['confidence_score'],
                'authentication_result': authentication_result['authentication_result']
            })
            
            return authentication_result
            
        except Exception as e:
            logger.error("Voice authentication failed", extra={
                "error": str(e),
                "input_embedding_dims": len(input_embedding) if input_embedding else 0,
                "stored_embeddings_count": len(stored_embeddings) if stored_embeddings else 0
            })
            raise


# Global instance for easy access
voice_authentication_service = VoiceAuthenticationService()


def authenticate_voice_sample(
    input_embedding: List[float], 
    stored_embeddings: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Convenience function for voice authentication.
    
    Args:
        input_embedding: Voice embedding to authenticate
        stored_embeddings: User's stored voice embeddings
        
    Returns:
        Authentication result dictionary
    """
    return voice_authentication_service.authenticate_voice(input_embedding, stored_embeddings)


def calculate_embedding_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Convenience function for similarity calculation.
    
    Args:
        embedding1: First voice embedding
        embedding2: Second voice embedding
        
    Returns:
        Cosine similarity score
    """
    return voice_authentication_service.calculate_cosine_similarity(embedding1, embedding2)
