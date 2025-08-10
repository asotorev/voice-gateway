"""
Registration Completion Detection Service.

Provides intelligent registration completion detection that considers multiple factors
beyond simple sample counting, including quality thresholds, consistency validation,
and configurable completion criteria for voice authentication registration.

This service is part of the shared layer and can be used by multiple Lambda functions
for consistent completion detection logic.
"""
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CompletionCriteria:
    """Configuration criteria for registration completion detection."""
    
    def __init__(self):
        """Initialize completion criteria from environment variables."""
        self.required_samples = int(os.getenv('REQUIRED_AUDIO_SAMPLES', '3'))
        self.min_quality_score = float(os.getenv('MIN_COMPLETION_QUALITY_SCORE', '0.7'))
        self.min_average_quality = float(os.getenv('MIN_AVERAGE_QUALITY_SCORE', '0.75'))
        self.quality_consistency_threshold = float(os.getenv('QUALITY_CONSISTENCY_THRESHOLD', '0.15'))
        self.allow_quality_override = os.getenv('ALLOW_QUALITY_OVERRIDE', 'false').lower() == 'true'
        self.completion_confidence_threshold = float(os.getenv('COMPLETION_CONFIDENCE_THRESHOLD', '0.85'))
        
        logger.info("Completion criteria initialized", extra={
            "required_samples": self.required_samples,
            "min_quality_score": self.min_quality_score,
            "min_average_quality": self.min_average_quality,
            "quality_consistency_threshold": self.quality_consistency_threshold,
            "allow_quality_override": self.allow_quality_override
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert criteria to dictionary for logging/analysis."""
        return {
            "required_samples": self.required_samples,
            "min_quality_score": self.min_quality_score,
            "min_average_quality": self.min_average_quality,
            "quality_consistency_threshold": self.quality_consistency_threshold,
            "allow_quality_override": self.allow_quality_override,
            "completion_confidence_threshold": self.completion_confidence_threshold
        }


class RegistrationCompletionChecker:
    """
    Intelligent registration completion detection system.
    
    Provides sophisticated completion checking that considers multiple factors
    beyond simple sample counting, including quality thresholds, consistency
    validation, and configurable completion criteria.
    """
    
    def __init__(self, criteria: Optional[CompletionCriteria] = None):
        """Initialize completion checker."""
        self.criteria = criteria or CompletionCriteria()
        
    def check_completion_status(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive completion check for user registration.
        
        Args:
            user_data: Complete user record from repository
            
        Returns:
            Dict with detailed completion analysis and recommendations
        """
        user_id = user_data.get('user_id', 'unknown')
        
        logger.info("Checking registration completion", extra={"user_id": user_id})
        
        # Get voice embeddings data
        voice_embeddings = user_data.get('voice_embeddings', [])
        
        # Perform completion checks
        basic_completion = self._check_basic_completion(voice_embeddings)
        quality_completion = self._check_quality_completion(voice_embeddings)
        consistency_completion = self._check_consistency_completion(voice_embeddings)
        
        # Determine final completion status
        completion_result = self._determine_final_completion(
            basic_completion, quality_completion, consistency_completion, user_data
        )
        
        # Generate completion recommendations
        recommendations = self._generate_completion_recommendations(
            completion_result, basic_completion, quality_completion, consistency_completion
        )
        
        completion_analysis = {
            'user_id': user_id,
            'is_complete': completion_result['is_complete'],
            'completion_confidence': completion_result['completion_confidence'],
            'registration_score': completion_result['registration_score'],
            'basic_completion': basic_completion,
            'quality_completion': quality_completion,
            'consistency_completion': consistency_completion,
            'recommendations': recommendations,
            'criteria_used': self.criteria.to_dict(),
            'checked_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Registration completion check completed", extra={
            "user_id": user_id,
            "is_complete": completion_result['is_complete'],
            "completion_confidence": completion_result['completion_confidence'],
            "registration_score": completion_result['registration_score']
        })
        
        return completion_analysis
    
    def should_trigger_completion_update(self, completion_analysis: Dict[str, Any], user_data: Dict[str, Any]) -> bool:
        """
        Determine if completion status should trigger a user record update.
        
        Args:
            completion_analysis: Result from check_completion_status
            user_data: Current user data
            
        Returns:
            True if user record should be updated with completion status
        """
        current_status = user_data.get('registration_complete', False)
        new_status = completion_analysis['is_complete']
        
        # Always update if status changed
        if current_status != new_status:
            logger.info("Completion status change detected", extra={
                "user_id": user_data.get('user_id'),
                "old_status": current_status,
                "new_status": new_status
            })
            return True
        
        # Update if confidence is high enough and not previously set
        if (new_status and 
            completion_analysis['completion_confidence'] >= self.criteria.completion_confidence_threshold and
            not user_data.get('completion_confirmed', False)):
            return True
        
        return False
    
    def _check_basic_completion(self, voice_embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check basic sample count completion criteria."""
        sample_count = len(voice_embeddings)
        
        basic_result = {
            'samples_collected': sample_count,
            'samples_required': self.criteria.required_samples,
            'has_minimum_samples': sample_count >= self.criteria.required_samples,
            'completion_percentage': min(100.0, (sample_count / self.criteria.required_samples) * 100),
            'samples_remaining': max(0, self.criteria.required_samples - sample_count)
        }
        
        return basic_result
    
    def _check_quality_completion(self, voice_embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check quality-based completion criteria."""
        if not voice_embeddings:
            return {
                'has_quality_samples': False,
                'quality_samples_count': 0,
                'average_quality': 0.0,
                'min_quality_met': False,
                'quality_scores': []
            }
        
        # Extract quality scores
        quality_scores = []
        for embedding in voice_embeddings:
            quality_score = embedding.get('quality_score', 0.0)
            if isinstance(quality_score, (int, float)):
                quality_scores.append(float(quality_score))
        
        if not quality_scores:
            return {
                'has_quality_samples': False,
                'quality_samples_count': 0,
                'average_quality': 0.0,
                'min_quality_met': False,
                'quality_scores': []
            }
        
        # Calculate quality metrics
        average_quality = sum(quality_scores) / len(quality_scores)
        quality_samples_count = sum(1 for score in quality_scores if score >= self.criteria.min_quality_score)
        
        quality_result = {
            'has_quality_samples': quality_samples_count >= self.criteria.required_samples,
            'quality_samples_count': quality_samples_count,
            'average_quality': round(average_quality, 3),
            'min_quality_met': average_quality >= self.criteria.min_average_quality,
            'quality_scores': quality_scores,
            'quality_distribution': self._analyze_quality_distribution(quality_scores)
        }
        
        return quality_result
    
    def _check_consistency_completion(self, voice_embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check consistency and reliability of voice samples."""
        if len(voice_embeddings) < 2:
            return {
                'is_consistent': False,
                'consistency_score': 0.0,
                'quality_variance': 0.0,
                'temporal_distribution': 'insufficient_data'
            }
        
        # Extract quality scores and timestamps
        quality_scores = []
        timestamps = []
        
        for embedding in voice_embeddings:
            quality_score = embedding.get('quality_score', 0.0)
            if isinstance(quality_score, (int, float)):
                quality_scores.append(float(quality_score))
            
            created_at = embedding.get('created_at')
            if created_at:
                timestamps.append(created_at)
        
        # Calculate quality variance
        if len(quality_scores) >= 2:
            mean_quality = sum(quality_scores) / len(quality_scores)
            variance = sum((score - mean_quality) ** 2 for score in quality_scores) / len(quality_scores)
            quality_variance = variance ** 0.5  # Standard deviation
        else:
            quality_variance = 0.0
        
        # Determine consistency
        is_consistent = quality_variance <= self.criteria.quality_consistency_threshold
        consistency_score = max(0.0, 1.0 - (quality_variance / self.criteria.quality_consistency_threshold))
        
        # Analyze temporal distribution
        temporal_analysis = self._analyze_temporal_distribution(timestamps)
        
        consistency_result = {
            'is_consistent': is_consistent,
            'consistency_score': round(consistency_score, 3),
            'quality_variance': round(quality_variance, 3),
            'temporal_distribution': temporal_analysis,
            'quality_trend': self._analyze_quality_trend(quality_scores)
        }
        
        return consistency_result
    
    def _determine_final_completion(self, basic_completion: Dict[str, Any], 
                                  quality_completion: Dict[str, Any],
                                  consistency_completion: Dict[str, Any],
                                  user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine final completion status based on all criteria."""
        
        # Basic completion check
        has_minimum_samples = basic_completion['has_minimum_samples']
        
        # Quality checks
        has_quality_samples = quality_completion['has_quality_samples']
        min_quality_met = quality_completion['min_quality_met']
        
        # Consistency checks
        is_consistent = consistency_completion['is_consistent']
        
        # Determine completion status
        is_complete = False
        completion_confidence = 0.0
        
        if has_minimum_samples:
            # Base completion score
            completion_score = 0.4  # 40% for having minimum samples
            
            # Quality contribution (40%)
            if has_quality_samples and min_quality_met:
                completion_score += 0.4
            elif has_quality_samples or min_quality_met:
                completion_score += 0.2
            
            # Consistency contribution (20%)
            if is_consistent:
                completion_score += 0.2
            else:
                completion_score += consistency_completion['consistency_score'] * 0.2
            
            completion_confidence = min(1.0, completion_score)
            
            # Determine final completion
            if self.criteria.allow_quality_override:
                is_complete = has_minimum_samples  # Basic completion sufficient
            else:
                is_complete = (has_minimum_samples and 
                             has_quality_samples and 
                             min_quality_met and 
                             completion_confidence >= self.criteria.completion_confidence_threshold)
        
        # Calculate registration score
        registration_score = self._calculate_registration_score(
            basic_completion, quality_completion, consistency_completion
        )
        
        return {
            'is_complete': is_complete,
            'completion_confidence': round(completion_confidence, 3),
            'registration_score': round(registration_score, 3)
        }
    
    def _generate_completion_recommendations(self, completion_result: Dict[str, Any],
                                           basic_completion: Dict[str, Any],
                                           quality_completion: Dict[str, Any],
                                           consistency_completion: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations for improving completion status."""
        recommendations = []
        
        # Basic sample recommendations
        if not basic_completion['has_minimum_samples']:
            samples_needed = basic_completion['samples_remaining']
            recommendations.append(f"Record {samples_needed} more voice sample(s) to meet minimum requirement")
        
        # Quality recommendations
        if not quality_completion['min_quality_met']:
            avg_quality = quality_completion['average_quality']
            target_quality = self.criteria.min_average_quality
            recommendations.append(f"Improve audio quality: current {avg_quality:.2f}, target {target_quality:.2f}")
        
        if quality_completion['quality_samples_count'] < self.criteria.required_samples:
            low_quality_count = self.criteria.required_samples - quality_completion['quality_samples_count']
            recommendations.append(f"Re-record {low_quality_count} sample(s) with better audio quality")
        
        # Consistency recommendations
        if not consistency_completion['is_consistent']:
            variance = consistency_completion['quality_variance']
            recommendations.append(f"Improve consistency: quality variance {variance:.3f} exceeds threshold")
        
        # Overall recommendations
        if completion_result['completion_confidence'] < self.criteria.completion_confidence_threshold:
            recommendations.append("Overall completion confidence needs improvement - consider re-recording samples")
        
        return recommendations
    
    def _analyze_quality_distribution(self, quality_scores: List[float]) -> Dict[str, Any]:
        """Analyze the distribution of quality scores."""
        if not quality_scores:
            return {'distribution': 'no_data'}
        
        sorted_scores = sorted(quality_scores)
        
        return {
            'min_score': min(quality_scores),
            'max_score': max(quality_scores),
            'median_score': sorted_scores[len(sorted_scores) // 2],
            'score_range': max(quality_scores) - min(quality_scores),
            'above_threshold_count': sum(1 for score in quality_scores if score >= self.criteria.min_quality_score)
        }
    
    def _analyze_temporal_distribution(self, timestamps: List[str]) -> str:
        """Analyze temporal distribution of samples."""
        if len(timestamps) < 2:
            return 'insufficient_data'
        
        # This is a simplified analysis - could be enhanced with actual timestamp parsing
        return 'normal_distribution' if len(timestamps) >= self.criteria.required_samples else 'sparse_distribution'
    
    def _analyze_quality_trend(self, quality_scores: List[float]) -> str:
        """Analyze quality trend across samples."""
        if len(quality_scores) < 2:
            return 'insufficient_data'
        
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
    
    def _calculate_registration_score(self, basic_completion: Dict[str, Any],
                                    quality_completion: Dict[str, Any],
                                    consistency_completion: Dict[str, Any]) -> float:
        """Calculate overall registration quality score."""
        
        # Sample completeness (25%)
        sample_score = min(1.0, basic_completion['completion_percentage'] / 100.0) * 0.25
        
        # Quality score (50%)
        quality_score = quality_completion['average_quality'] * 0.5
        
        # Consistency score (25%)
        consistency_score = consistency_completion['consistency_score'] * 0.25
        
        final_score = sample_score + quality_score + consistency_score
        
        return min(1.0, final_score)


# Global instance for easy access
completion_checker = RegistrationCompletionChecker()


def check_registration_completion(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function for registration completion checking.
    
    Args:
        user_data: Complete user record from repository
        
    Returns:
        Completion analysis dictionary
    """
    return completion_checker.check_completion_status(user_data)


def should_update_completion_status(completion_analysis: Dict[str, Any], user_data: Dict[str, Any]) -> bool:
    """
    Convenience function to determine if completion status should be updated.
    
    Args:
        completion_analysis: Result from check_registration_completion
        user_data: Current user data
        
    Returns:
        True if user record should be updated
    """
    return completion_checker.should_trigger_completion_update(completion_analysis, user_data)
