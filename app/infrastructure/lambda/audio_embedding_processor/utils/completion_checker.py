"""
Registration completion checker for voice authentication.

This module provides intelligent completion detection that goes beyond simple
counting, including quality validation, consistency checks, and smart
completion criteria with support for edge cases and error recovery.
"""
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from .user_status_manager import RegistrationStatus, user_status_manager

logger = logging.getLogger(__name__)


class CompletionCriteria:
    """Criteria configuration for registration completion."""
    
    def __init__(self):
        """Initialize completion criteria from environment."""
        self.required_samples = int(os.getenv('REQUIRED_AUDIO_SAMPLES', '3'))
        self.min_quality_score = float(os.getenv('MIN_VOICE_QUALITY_SCORE', '0.7'))
        self.min_acceptable_samples = int(os.getenv('MIN_ACCEPTABLE_SAMPLES', '3'))
        self.allow_quality_override = os.getenv('ALLOW_QUALITY_OVERRIDE', 'false').lower() == 'true'
        self.max_total_samples = int(os.getenv('MAX_TOTAL_SAMPLES', '10'))
        
        logger.info("Completion criteria initialized", extra={
            "required_samples": self.required_samples,
            "min_quality_score": self.min_quality_score,
            "min_acceptable_samples": self.min_acceptable_samples,
            "allow_quality_override": self.allow_quality_override
        })


class RegistrationCompletionChecker:
    """
    Intelligent registration completion detection system.
    
    Provides sophisticated completion checking that considers multiple factors
    beyond simple sample counting, including quality thresholds, consistency
    validation, and configurable completion criteria.
    """
    
    def __init__(self):
        """Initialize completion checker."""
        self.criteria = CompletionCriteria()
        
    def check_completion_status(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive completion check for user registration.
        
        Args:
            user_data: Complete user record from DynamoDB
            
        Returns:
            Dict with detailed completion analysis and recommendations
        """
        user_id = user_data.get('user_id', 'unknown')
        
        logger.info("Checking registration completion", extra={"user_id": user_id})
        
        # Get current progress analysis
        progress_analysis = user_status_manager.analyze_registration_progress(user_data)
        
        # Perform completion checks
        basic_completion = self._check_basic_completion(user_data)
        quality_completion = self._check_quality_completion(user_data)
        consistency_completion = self._check_consistency_completion(user_data)
        
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
            'completion_confidence': completion_result['confidence'],
            'completion_checks': {
                'basic_completion': basic_completion,
                'quality_completion': quality_completion,
                'consistency_completion': consistency_completion
            },
            'final_decision': completion_result,
            'recommendations': recommendations,
            'registration_score': user_status_manager.calculate_registration_score(progress_analysis),
            'checked_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Completion check completed", extra={
            "user_id": user_id,
            "is_complete": completion_result['is_complete'],
            "confidence": completion_result['confidence'],
            "score": completion_analysis['registration_score']
        })
        
        return completion_analysis
    
    def _check_basic_completion(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check basic completion criteria (sample count)."""
        voice_embeddings = user_data.get('voice_embeddings', [])
        sample_count = len(voice_embeddings)
        
        # Check explicit completion flag
        explicit_complete = user_data.get('registration_complete', False)
        
        basic_result = {
            'passed': False,
            'sample_count': sample_count,
            'required_count': self.criteria.required_samples,
            'explicit_flag': explicit_complete,
            'criteria_met': sample_count >= self.criteria.required_samples,
            'details': []
        }
        
        if explicit_complete:
            basic_result['passed'] = True
            basic_result['details'].append("Explicit completion flag is set")
        elif sample_count >= self.criteria.required_samples:
            basic_result['passed'] = True
            basic_result['details'].append(f"Required sample count met: {sample_count}/{self.criteria.required_samples}")
        else:
            basic_result['details'].append(f"Insufficient samples: {sample_count}/{self.criteria.required_samples}")
        
        return basic_result
    
    def _check_quality_completion(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check quality-based completion criteria."""
        voice_embeddings = user_data.get('voice_embeddings', [])
        
        if not voice_embeddings:
            return {
                'passed': False,
                'acceptable_samples': 0,
                'average_quality': 0.0,
                'quality_distribution': {},
                'details': ["No voice samples to evaluate"]
            }
        
        # Analyze quality of each sample
        quality_scores = []
        acceptable_count = 0
        
        for embedding in voice_embeddings:
            audio_metadata = embedding.get('audio_metadata', {})
            quality_score = audio_metadata.get('quality_score', 0.0)
            quality_scores.append(quality_score)
            
            if quality_score >= self.criteria.min_quality_score:
                acceptable_count += 1
        
        average_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # Quality distribution analysis
        quality_ranges = {
            'excellent': sum(1 for q in quality_scores if q >= 0.9),
            'good': sum(1 for q in quality_scores if 0.8 <= q < 0.9),
            'acceptable': sum(1 for q in quality_scores if self.criteria.min_quality_score <= q < 0.8),
            'poor': sum(1 for q in quality_scores if q < self.criteria.min_quality_score)
        }
        
        quality_result = {
            'passed': acceptable_count >= self.criteria.min_acceptable_samples,
            'acceptable_samples': acceptable_count,
            'required_acceptable': self.criteria.min_acceptable_samples,
            'average_quality': round(average_quality, 3),
            'quality_distribution': quality_ranges,
            'details': []
        }
        
        if quality_result['passed']:
            quality_result['details'].append(f"Quality criteria met: {acceptable_count} acceptable samples")
        else:
            quality_result['details'].append(f"Insufficient quality samples: {acceptable_count}/{self.criteria.min_acceptable_samples}")
        
        # Add quality insights
        if average_quality < self.criteria.min_quality_score:
            quality_result['details'].append(f"Average quality below threshold: {average_quality:.3f}")
        
        if quality_ranges['poor'] > 0:
            quality_result['details'].append(f"{quality_ranges['poor']} samples below quality threshold")
        
        return quality_result
    
    def _check_consistency_completion(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check consistency and validation of voice samples."""
        voice_embeddings = user_data.get('voice_embeddings', [])
        
        if len(voice_embeddings) < 2:
            return {
                'passed': True,  # Can't check consistency with < 2 samples
                'consistency_score': 1.0,
                'embedding_similarity': None,
                'temporal_consistency': True,
                'details': ["Insufficient samples for consistency check"]
            }
        
        # Check temporal consistency (reasonable timing between samples)
        temporal_consistency = self._check_temporal_consistency(voice_embeddings)
        
        # Check embedding similarity (basic validation)
        embedding_similarity = self._check_embedding_similarity(voice_embeddings)
        
        # Calculate overall consistency score
        consistency_score = self._calculate_consistency_score(
            temporal_consistency, embedding_similarity
        )
        
        consistency_result = {
            'passed': consistency_score >= 0.7,  # 70% consistency threshold
            'consistency_score': round(consistency_score, 3),
            'temporal_consistency': temporal_consistency,
            'embedding_similarity': embedding_similarity,
            'details': []
        }
        
        # Add details based on analysis
        if temporal_consistency['is_consistent']:
            consistency_result['details'].append("Temporal pattern is consistent")
        else:
            consistency_result['details'].append("Irregular timing between samples")
        
        if embedding_similarity and embedding_similarity['is_similar']:
            consistency_result['details'].append("Voice embeddings show good similarity")
        else:
            consistency_result['details'].append("Voice embeddings may be inconsistent")
        
        return consistency_result
    
    def _check_temporal_consistency(self, voice_embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if samples were recorded with reasonable timing."""
        try:
            timestamps = []
            for embedding in voice_embeddings:
                created_at = embedding.get('created_at')
                if created_at:
                    timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    timestamps.append(timestamp)
            
            if len(timestamps) < 2:
                return {'is_consistent': True, 'reason': 'insufficient_data'}
            
            # Check for reasonable intervals for individual sample uploads
            timestamps.sort()
            intervals = []
            
            for i in range(1, len(timestamps)):
                interval_seconds = (timestamps[i] - timestamps[i-1]).total_seconds()
                intervals.append(interval_seconds)
            
            # Consider consistent if intervals are between 10 seconds and 45 minutes
            min_interval = 10  # 10 seconds minimum between individual samples
            max_interval = 45 * 60  # 45 minutes maximum (total registration window)
            
            consistent_intervals = [
                min_interval <= interval <= max_interval for interval in intervals
            ]
            
            is_consistent = sum(consistent_intervals) / len(consistent_intervals) >= 0.8
            
            return {
                'is_consistent': is_consistent,
                'average_interval_minutes': sum(intervals) / len(intervals) / 60,
                'consistent_intervals_ratio': sum(consistent_intervals) / len(consistent_intervals)
            }
            
        except Exception as e:
            logger.warning("Failed temporal consistency check", extra={"error": str(e)})
            return {'is_consistent': True, 'reason': 'check_failed'}
    
    def _check_embedding_similarity(self, voice_embeddings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Basic check of embedding similarity (without complex ML)."""
        try:
            embeddings = []
            for embedding_data in voice_embeddings:
                embedding = embedding_data.get('embedding', [])
                if embedding and len(embedding) > 0:
                    embeddings.append(embedding)
            
            if len(embeddings) < 2:
                return None
            
            # Simple similarity check - compare embedding norms and basic statistics
            embedding_norms = []
            embedding_means = []
            
            for embedding in embeddings:
                if isinstance(embedding, list) and len(embedding) > 0:
                    # Calculate L2 norm
                    norm = sum(x**2 for x in embedding) ** 0.5
                    embedding_norms.append(norm)
                    
                    # Calculate mean
                    mean = sum(embedding) / len(embedding)
                    embedding_means.append(mean)
            
            if len(embedding_norms) < 2:
                return None
            
            # Check if norms are similar (within reasonable range)
            norm_std = (sum((x - sum(embedding_norms)/len(embedding_norms))**2 for x in embedding_norms) / len(embedding_norms))**0.5
            norm_similarity = norm_std < 0.5  # Arbitrary threshold
            
            # Check if means are similar
            mean_std = (sum((x - sum(embedding_means)/len(embedding_means))**2 for x in embedding_means) / len(embedding_means))**0.5
            mean_similarity = mean_std < 0.5  # Arbitrary threshold
            
            is_similar = norm_similarity and mean_similarity
            
            return {
                'is_similar': is_similar,
                'norm_consistency': norm_similarity,
                'mean_consistency': mean_similarity,
                'norm_std': round(norm_std, 4),
                'mean_std': round(mean_std, 4)
            }
            
        except Exception as e:
            logger.warning("Failed embedding similarity check", extra={"error": str(e)})
            return None
    
    def _calculate_consistency_score(self, temporal_consistency: Dict[str, Any], 
                                   embedding_similarity: Optional[Dict[str, Any]]) -> float:
        """Calculate overall consistency score."""
        score = 0.0
        
        # Temporal consistency (50% weight)
        if temporal_consistency.get('is_consistent', False):
            score += 0.5
        
        # Embedding similarity (50% weight)
        if embedding_similarity:
            if embedding_similarity.get('is_similar', False):
                score += 0.5
        else:
            # If we can't check similarity, give benefit of the doubt
            score += 0.3
        
        return score
    
    def _determine_final_completion(self, basic_completion: Dict[str, Any],
                                  quality_completion: Dict[str, Any],
                                  consistency_completion: Dict[str, Any],
                                  user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine final completion status based on all checks."""
        # Check if all criteria pass
        all_passed = (
            basic_completion['passed'] and
            quality_completion['passed'] and
            consistency_completion['passed']
        )
        
        # Calculate confidence score
        confidence_factors = []
        
        if basic_completion['passed']:
            confidence_factors.append(0.4)  # 40% for basic completion
        
        if quality_completion['passed']:
            confidence_factors.append(0.4)  # 40% for quality
        
        if consistency_completion['passed']:
            confidence_factors.append(0.2)  # 20% for consistency
        
        confidence = sum(confidence_factors)
        
        # Special cases and overrides
        decision_reason = []
        
        if all_passed:
            decision_reason.append("All completion criteria met")
        else:
            # Check for acceptable partial completion
            if basic_completion['passed'] and quality_completion['passed']:
                # Basic + quality is acceptable even without perfect consistency
                all_passed = True
                confidence = max(confidence, 0.85)
                decision_reason.append("Basic and quality criteria met (consistency acceptable)")
            
            # Check for quality override
            if (self.criteria.allow_quality_override and 
                quality_completion['average_quality'] >= 0.9 and
                quality_completion['acceptable_samples'] >= self.criteria.required_samples):
                all_passed = True
                confidence = max(confidence, 0.9)
                decision_reason.append("High quality override applied")
        
        return {
            'is_complete': all_passed,
            'confidence': round(confidence, 3),
            'decision_reasons': decision_reason,
            'recommendation': 'complete' if all_passed else 'continue_registration'
        }
    
    def _generate_completion_recommendations(self, completion_result: Dict[str, Any],
                                           basic_completion: Dict[str, Any],
                                           quality_completion: Dict[str, Any],
                                           consistency_completion: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on completion analysis."""
        recommendations = []
        
        if completion_result['is_complete']:
            recommendations.append("Registration complete - user can proceed to voice authentication")
            return recommendations
        
        # Recommendations for incomplete registration
        if not basic_completion['passed']:
            needed = basic_completion['required_count'] - basic_completion['sample_count']
            recommendations.append(f"Record {needed} more voice sample(s)")
        
        if not quality_completion['passed']:
            acceptable_needed = self.criteria.min_acceptable_samples - quality_completion['acceptable_samples']
            recommendations.append(f"Improve audio quality - need {acceptable_needed} more acceptable samples")
            
            if quality_completion['average_quality'] < self.criteria.min_quality_score:
                recommendations.append("Find quieter environment for better recording quality")
        
        if not consistency_completion['passed']:
            if consistency_completion['consistency_score'] < 0.5:
                recommendations.append("Ensure consistent recording conditions and timing")
        
        return recommendations
    
    def should_trigger_completion_update(self, completion_analysis: Dict[str, Any], 
                                       current_user_status: Dict[str, Any]) -> bool:
        """
        Determine if completion status should trigger a DynamoDB update.
        
        Args:
            completion_analysis: Result from check_completion_status
            current_user_status: Current user record from DynamoDB
            
        Returns:
            True if user record should be updated
        """
        current_complete = current_user_status.get('registration_complete', False)
        new_complete = completion_analysis['is_complete']
        
        # Update if completion status changed
        if current_complete != new_complete:
            return True
        
        # Update if confidence is very high and not yet marked complete
        if (not current_complete and 
            completion_analysis['completion_confidence'] >= 0.95):
            return True
        
        return False


# Global completion checker instance
completion_checker = RegistrationCompletionChecker()

