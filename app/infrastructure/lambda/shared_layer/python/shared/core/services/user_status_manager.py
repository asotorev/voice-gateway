"""
User Registration Status Management Service.

Provides comprehensive analysis and tracking of user registration progress,
including status transitions, progress metrics, quality analysis, and
detailed reporting for voice authentication registration workflows.

This service is part of the shared layer and can be used by multiple
Lambda functions for consistent user status management.
"""
import os
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class RegistrationStatus(Enum):
    """Enumeration of registration status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class UserStatusManager:
    """
    Comprehensive user registration status management and analysis.
    
    Provides detailed progress tracking, quality analysis, and status
    management for voice authentication user registration workflows.
    """
    
    def __init__(self):
        """Initialize user status manager with configuration."""
        self.required_samples = int(os.getenv('REQUIRED_AUDIO_SAMPLES', '3'))
        self.min_quality_threshold = float(os.getenv('MIN_VOICE_QUALITY_SCORE', '0.7'))
        self.quality_consistency_threshold = float(os.getenv('QUALITY_CONSISTENCY_THRESHOLD', '0.15'))
        self.registration_timeout_hours = int(os.getenv('REGISTRATION_TIMEOUT_HOURS', '24'))
        
        logger.info("User status manager initialized", extra={
            "required_samples": self.required_samples,
            "min_quality_threshold": self.min_quality_threshold,
            "quality_consistency_threshold": self.quality_consistency_threshold,
            "registration_timeout_hours": self.registration_timeout_hours
        })
    
    def analyze_registration_progress(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of user registration progress.
        
        Args:
            user_data: Complete user record from repository
            
        Returns:
            Dict with detailed progress analysis including metrics, status, and recommendations
        """
        user_id = user_data.get('user_id', 'unknown')
        
        logger.debug("Analyzing registration progress", extra={"user_id": user_id})
        
        # Extract voice embeddings data
        voice_embeddings = user_data.get('voice_embeddings', [])
        
        # Calculate progress metrics
        progress_metrics = self._calculate_progress_metrics(voice_embeddings)
        
        # Analyze quality metrics
        quality_analysis = self._analyze_quality_metrics(voice_embeddings)
        
        # Determine current status
        current_status = self._determine_current_status(user_data, progress_metrics, quality_analysis)
        
        # Calculate completion estimates
        completion_estimates = self._calculate_completion_estimates(progress_metrics, quality_analysis)
        
        # Generate status recommendations
        recommendations = self._generate_status_recommendations(
            progress_metrics, quality_analysis, current_status
        )
        
        # Analyze temporal patterns
        temporal_analysis = self._analyze_temporal_patterns(voice_embeddings)
        
        analysis_result = {
            'user_id': user_id,
            'progress_metrics': progress_metrics,
            'quality_analysis': quality_analysis,
            'current_status': current_status,
            'completion_estimates': completion_estimates,
            'recommendations': recommendations,
            'temporal_analysis': temporal_analysis,
            'analyzed_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Registration progress analysis completed", extra={
            "user_id": user_id,
            "current_status": current_status,
            "completion_percentage": progress_metrics['completion_percentage'],
            "quality_score": quality_analysis['average_quality']
        })
        
        return analysis_result
    
    def update_user_status(self, user_id: str, new_status: Union[str, RegistrationStatus], 
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update user registration status with metadata tracking.
        
        Args:
            user_id: User identifier
            new_status: New registration status
            metadata: Additional status metadata
            
        Returns:
            Dict with status update details
        """
        if isinstance(new_status, str):
            try:
                status_enum = RegistrationStatus(new_status)
            except ValueError:
                logger.warning(f"Invalid status value: {new_status}", extra={"user_id": user_id})
                status_enum = RegistrationStatus.PENDING
        else:
            status_enum = new_status
        
        update_metadata = metadata or {}
        update_metadata.update({
            'status_updated_at': datetime.now(timezone.utc).isoformat(),
            'updated_by': 'user_status_manager'
        })
        
        logger.info("User status updated", extra={
            "user_id": user_id,
            "new_status": status_enum.value,
            "metadata": update_metadata
        })
        
        return {
            'user_id': user_id,
            'status': status_enum.value,
            'metadata': update_metadata,
            'update_successful': True
        }
    
    def _calculate_progress_metrics(self, voice_embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate detailed progress metrics."""
        samples_collected = len(voice_embeddings)
        completion_percentage = min(100.0, (samples_collected / self.required_samples) * 100)
        samples_remaining = max(0, self.required_samples - samples_collected)
        
        # Calculate quality-based progress
        quality_samples = sum(1 for emb in voice_embeddings 
                            if emb.get('quality_score', 0) >= self.min_quality_threshold)
        quality_completion_percentage = min(100.0, (quality_samples / self.required_samples) * 100)
        
        return {
            'samples_collected': samples_collected,
            'samples_required': self.required_samples,
            'samples_remaining': samples_remaining,
            'completion_percentage': round(completion_percentage, 1),
            'quality_samples_count': quality_samples,
            'quality_completion_percentage': round(quality_completion_percentage, 1),
            'is_minimum_met': samples_collected >= self.required_samples,
            'is_quality_minimum_met': quality_samples >= self.required_samples
        }
    
    def _analyze_quality_metrics(self, voice_embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze quality metrics across voice samples."""
        if not voice_embeddings:
            return {
                'average_quality': 0.0,
                'quality_variance': 0.0,
                'quality_trend': 'no_data',
                'quality_distribution': {},
                'consistency_score': 0.0
            }
        
        # Extract quality scores
        quality_scores = []
        for embedding in voice_embeddings:
            quality_score = embedding.get('quality_score', 0.0)
            if isinstance(quality_score, (int, float)):
                quality_scores.append(float(quality_score))
        
        if not quality_scores:
            return {
                'average_quality': 0.0,
                'quality_variance': 0.0,
                'quality_trend': 'no_quality_data',
                'quality_distribution': {},
                'consistency_score': 0.0
            }
        
        # Calculate quality statistics
        average_quality = sum(quality_scores) / len(quality_scores)
        
        # Calculate variance
        if len(quality_scores) > 1:
            variance = sum((score - average_quality) ** 2 for score in quality_scores) / len(quality_scores)
            quality_variance = variance ** 0.5  # Standard deviation
        else:
            quality_variance = 0.0
        
        # Calculate consistency score
        consistency_score = max(0.0, 1.0 - (quality_variance / self.quality_consistency_threshold))
        
        # Analyze quality trend
        quality_trend = self._analyze_quality_trend(quality_scores)
        
        # Quality distribution analysis
        quality_distribution = self._analyze_quality_distribution(quality_scores)
        
        return {
            'average_quality': round(average_quality, 3),
            'quality_variance': round(quality_variance, 3),
            'quality_trend': quality_trend,
            'quality_distribution': quality_distribution,
            'consistency_score': round(consistency_score, 3),
            'min_quality': min(quality_scores),
            'max_quality': max(quality_scores),
            'quality_range': max(quality_scores) - min(quality_scores)
        }
    
    def _determine_current_status(self, user_data: Dict[str, Any], 
                                progress_metrics: Dict[str, Any],
                                quality_analysis: Dict[str, Any]) -> str:
        """Determine current registration status based on analysis."""
        
        # Check if already completed
        if user_data.get('registration_complete', False):
            return RegistrationStatus.COMPLETED.value
        
        # Check for failure conditions
        if self._check_failure_conditions(user_data, progress_metrics, quality_analysis):
            return RegistrationStatus.FAILED.value
        
        # Check for expiration
        if self._check_expiration_conditions(user_data):
            return RegistrationStatus.EXPIRED.value
        
        # Check progress
        if progress_metrics['samples_collected'] == 0:
            return RegistrationStatus.PENDING.value
        elif progress_metrics['is_minimum_met'] and progress_metrics['is_quality_minimum_met']:
            return RegistrationStatus.COMPLETED.value
        else:
            return RegistrationStatus.IN_PROGRESS.value
    
    def _calculate_completion_estimates(self, progress_metrics: Dict[str, Any],
                                      quality_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate estimated completion metrics."""
        
        # Estimate samples needed based on quality trend
        samples_remaining = progress_metrics['samples_remaining']
        
        # Adjust estimate based on quality trend
        if quality_analysis['quality_trend'] == 'declining':
            # May need extra samples if quality is declining
            estimated_additional = samples_remaining + 1
        elif quality_analysis['quality_trend'] == 'improving':
            # May need fewer samples if quality is improving
            estimated_additional = max(0, samples_remaining - 1)
        else:
            estimated_additional = samples_remaining
        
        # Calculate confidence in estimates
        completion_confidence = self._calculate_completion_confidence(progress_metrics, quality_analysis)
        
        return {
            'samples_remaining_minimum': samples_remaining,
            'samples_estimated_total': estimated_additional,
            'completion_confidence': completion_confidence,
            'estimated_completion_status': 'on_track' if completion_confidence > 0.7 else 'at_risk'
        }
    
    def _generate_status_recommendations(self, progress_metrics: Dict[str, Any],
                                       quality_analysis: Dict[str, Any],
                                       current_status: str) -> List[str]:
        """Generate actionable recommendations for improving registration status."""
        recommendations = []
        
        # Progress-based recommendations
        if progress_metrics['samples_remaining'] > 0:
            recommendations.append(f"Record {progress_metrics['samples_remaining']} more voice sample(s)")
        
        # Quality-based recommendations
        if quality_analysis['average_quality'] < self.min_quality_threshold:
            recommendations.append(f"Improve audio quality: current {quality_analysis['average_quality']:.2f}, target {self.min_quality_threshold:.2f}")
        
        if quality_analysis['quality_variance'] > self.quality_consistency_threshold:
            recommendations.append("Improve consistency between voice samples")
        
        if quality_analysis['quality_trend'] == 'declining':
            recommendations.append("Recent samples show declining quality - check recording environment")
        
        # Status-specific recommendations
        if current_status == RegistrationStatus.PENDING.value:
            recommendations.append("Start voice registration by recording your first sample")
        elif current_status == RegistrationStatus.IN_PROGRESS.value:
            if progress_metrics['completion_percentage'] < 50:
                recommendations.append("Continue recording samples to reach 50% completion")
        
        return recommendations
    
    def _analyze_temporal_patterns(self, voice_embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal patterns in voice sample collection."""
        if len(voice_embeddings) < 2:
            return {'pattern': 'insufficient_data', 'analysis': 'Need more samples for temporal analysis'}
        
        # Extract timestamps
        timestamps = []
        for embedding in voice_embeddings:
            created_at = embedding.get('created_at')
            if created_at:
                timestamps.append(created_at)
        
        if len(timestamps) < 2:
            return {'pattern': 'no_timestamps', 'analysis': 'Timestamp data not available'}
        
        # Simple temporal analysis (could be enhanced with actual datetime parsing)
        return {
            'pattern': 'normal',
            'sample_count': len(timestamps),
            'analysis': f'Collected {len(timestamps)} samples over time'
        }
    
    def _analyze_quality_trend(self, quality_scores: List[float]) -> str:
        """Analyze quality trend across samples."""
        if len(quality_scores) < 2:
            return 'insufficient_data'
        
        # Simple trend analysis
        first_half = quality_scores[:len(quality_scores)//2]
        second_half = quality_scores[len(quality_scores)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if second_avg > first_avg + 0.05:
            return 'improving'
        elif first_avg > second_avg + 0.05:
            return 'declining'
        else:
            return 'stable'
    
    def _analyze_quality_distribution(self, quality_scores: List[float]) -> Dict[str, Any]:
        """Analyze distribution of quality scores."""
        if not quality_scores:
            return {}
        
        high_quality = sum(1 for score in quality_scores if score >= 0.8)
        medium_quality = sum(1 for score in quality_scores if 0.6 <= score < 0.8)
        low_quality = sum(1 for score in quality_scores if score < 0.6)
        
        return {
            'high_quality_count': high_quality,
            'medium_quality_count': medium_quality,
            'low_quality_count': low_quality,
            'above_threshold_count': sum(1 for score in quality_scores if score >= self.min_quality_threshold)
        }
    
    def _check_failure_conditions(self, user_data: Dict[str, Any],
                                progress_metrics: Dict[str, Any],
                                quality_analysis: Dict[str, Any]) -> bool:
        """Check if registration has failed based on various conditions."""
        # Could implement failure detection logic here
        return False
    
    def _check_expiration_conditions(self, user_data: Dict[str, Any]) -> bool:
        """Check if registration has expired."""
        # Could implement expiration logic here based on timestamps
        return False
    
    def _calculate_completion_confidence(self, progress_metrics: Dict[str, Any],
                                       quality_analysis: Dict[str, Any]) -> float:
        """Calculate confidence in completion estimates."""
        
        # Base confidence from progress
        progress_confidence = progress_metrics['completion_percentage'] / 100.0
        
        # Quality confidence
        quality_confidence = min(1.0, quality_analysis['average_quality'] / self.min_quality_threshold)
        
        # Consistency confidence
        consistency_confidence = quality_analysis['consistency_score']
        
        # Combined confidence (weighted average)
        overall_confidence = (
            progress_confidence * 0.4 +
            quality_confidence * 0.4 +
            consistency_confidence * 0.2
        )
        
        return round(min(1.0, overall_confidence), 3)


# Global instance for easy access
user_status_manager = UserStatusManager()


def analyze_user_registration_progress(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function for user registration progress analysis.
    
    Args:
        user_data: Complete user record from repository
        
    Returns:
        Progress analysis dictionary
    """
    return user_status_manager.analyze_registration_progress(user_data)


def update_registration_status(user_id: str, new_status: Union[str, RegistrationStatus],
                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function for updating user registration status.
    
    Args:
        user_id: User identifier
        new_status: New registration status
        metadata: Additional status metadata
        
    Returns:
        Status update result dictionary
    """
    return user_status_manager.update_user_status(user_id, new_status, metadata)
