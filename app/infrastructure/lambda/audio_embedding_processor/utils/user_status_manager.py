"""
User status management for voice registration tracking.

This module provides sophisticated user status tracking, managing the progression
from initial registration through voice sample collection to completion,
with support for state validation, progress tracking, and error recovery.
"""
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class RegistrationStatus(Enum):
    """User voice registration status states."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"


class SampleQuality(Enum):
    """Voice sample quality ratings."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    REJECTED = "rejected"


class UserStatusManager:
    """
    Manages user voice registration status and progression tracking.
    
    Provides comprehensive tracking of user registration progress,
    quality assessment, and state transitions with proper validation.
    """
    
    def __init__(self):
        """Initialize user status manager."""
        self.required_samples = int(os.getenv('REQUIRED_AUDIO_SAMPLES', '3'))
        self.min_quality_score = float(os.getenv('MIN_VOICE_QUALITY_SCORE', '0.7'))
        self.max_registration_minutes = int(os.getenv('MAX_REGISTRATION_MINUTES', '45'))  # 3 samples × 15 min each
        
        logger.info("User status manager initialized", extra={
            "required_samples": self.required_samples,
            "min_quality_score": self.min_quality_score,
            "max_registration_minutes": self.max_registration_minutes
        })
    
    def analyze_registration_progress(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze current registration progress for a user.
        
        Args:
            user_data: Complete user record from DynamoDB
            
        Returns:
            Dict with detailed progress analysis
        """
        user_id = user_data.get('user_id', 'unknown')
        
        logger.debug("Analyzing registration progress", extra={"user_id": user_id})
        
        # Extract voice embeddings
        voice_embeddings = user_data.get('voice_embeddings', [])
        
        # Basic progress metrics
        samples_collected = len(voice_embeddings)
        samples_remaining = max(0, self.required_samples - samples_collected)
        completion_percentage = min(100, (samples_collected / self.required_samples) * 100)
        
        # Quality analysis
        quality_analysis = self._analyze_sample_quality(voice_embeddings)
        
        # Time analysis
        time_analysis = self._analyze_registration_timeline(user_data, voice_embeddings)
        
        # Determine current status
        current_status = self._determine_registration_status(
            user_data, samples_collected, quality_analysis, time_analysis
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            current_status, samples_collected, quality_analysis, time_analysis
        )
        
        progress_analysis = {
            'user_id': user_id,
            'current_status': current_status.value,
            'progress_metrics': {
                'samples_collected': samples_collected,
                'samples_remaining': samples_remaining,
                'completion_percentage': completion_percentage,
                'required_samples': self.required_samples
            },
            'quality_analysis': quality_analysis,
            'time_analysis': time_analysis,
            'recommendations': recommendations,
            'next_actions': self._get_next_actions(current_status, recommendations),
            'analyzed_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Registration progress analyzed", extra={
            "user_id": user_id,
            "status": current_status.value,
            "samples_collected": samples_collected,
            "completion_percentage": completion_percentage
        })
        
        return progress_analysis
    
    def _analyze_sample_quality(self, voice_embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze quality of collected voice samples."""
        if not voice_embeddings:
            return {
                'average_quality': 0.0,
                'quality_distribution': {},
                'acceptable_samples': 0,
                'quality_trend': 'no_data'
            }
        
        # Extract quality scores
        quality_scores = []
        quality_ratings = []
        
        for embedding in voice_embeddings:
            audio_metadata = embedding.get('audio_metadata', {})
            quality_score = audio_metadata.get('quality_score', 0.0)
            quality_scores.append(quality_score)
            
            # Classify quality
            if quality_score >= 0.9:
                quality_ratings.append(SampleQuality.EXCELLENT)
            elif quality_score >= 0.8:
                quality_ratings.append(SampleQuality.GOOD)
            elif quality_score >= self.min_quality_score:
                quality_ratings.append(SampleQuality.ACCEPTABLE)
            elif quality_score >= 0.5:
                quality_ratings.append(SampleQuality.POOR)
            else:
                quality_ratings.append(SampleQuality.REJECTED)
        
        # Calculate metrics
        average_quality = sum(quality_scores) / len(quality_scores)
        acceptable_samples = sum(1 for rating in quality_ratings 
                               if rating in [SampleQuality.EXCELLENT, SampleQuality.GOOD, SampleQuality.ACCEPTABLE])
        
        # Quality distribution
        quality_distribution = {}
        for rating in SampleQuality:
            quality_distribution[rating.value] = sum(1 for r in quality_ratings if r == rating)
        
        # Quality trend (improving, declining, stable)
        quality_trend = 'stable'
        if len(quality_scores) >= 2:
            recent_avg = sum(quality_scores[-2:]) / 2
            earlier_avg = sum(quality_scores[:-2]) / max(1, len(quality_scores) - 2)
            
            if recent_avg > earlier_avg + 0.1:
                quality_trend = 'improving'
            elif recent_avg < earlier_avg - 0.1:
                quality_trend = 'declining'
        
        return {
            'average_quality': round(average_quality, 3),
            'quality_distribution': quality_distribution,
            'acceptable_samples': acceptable_samples,
            'quality_trend': quality_trend,
            'latest_quality': quality_scores[-1] if quality_scores else 0.0
        }
    
    def _analyze_registration_timeline(self, user_data: Dict[str, Any], 
                                     voice_embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze timeline aspects of registration."""
        created_at = user_data.get('created_at')
        if not created_at:
            return {'timeline_analysis': 'no_creation_date'}
        
        try:
            creation_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            minutes_since_creation = (now - creation_date).total_seconds() / 60
            
            # Analyze sample collection timeline
            sample_dates = []
            for embedding in voice_embeddings:
                created_at_str = embedding.get('created_at')
                if created_at_str:
                    sample_date = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    sample_dates.append(sample_date)
            
            timeline_analysis = {
                'minutes_since_creation': round(minutes_since_creation, 2),
                'max_registration_minutes': self.max_registration_minutes,
                'is_within_timeframe': minutes_since_creation <= self.max_registration_minutes,
                'urgency_level': self._calculate_urgency_level(minutes_since_creation),
                'sample_collection_pattern': self._analyze_collection_pattern(sample_dates),
                'time_remaining_minutes': max(0, self.max_registration_minutes - minutes_since_creation)
            }
            
            return timeline_analysis
            
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse registration timeline", extra={
                "error": str(e),
                "created_at": created_at
            })
            return {'timeline_analysis': 'parse_error'}
    
    def _calculate_urgency_level(self, minutes_since_creation: float) -> str:
        """Calculate urgency level based on time elapsed in minutes."""
        if minutes_since_creation >= self.max_registration_minutes:
            return 'expired'
        elif minutes_since_creation >= self.max_registration_minutes * 0.8:  # > 36 minutes
            return 'urgent'
        elif minutes_since_creation >= self.max_registration_minutes * 0.6:  # > 27 minutes
            return 'moderate'
        else:
            return 'low'
    
    def _analyze_collection_pattern(self, sample_dates: List[datetime]) -> Dict[str, Any]:
        """Analyze pattern of individual sample collection."""
        if len(sample_dates) < 2:
            return {'pattern': 'single_sample', 'details': 'Only one sample recorded so far'}
        
        # Sort dates
        sorted_dates = sorted(sample_dates)
        
        # Calculate intervals between individual samples (in minutes)
        intervals = []
        for i in range(1, len(sorted_dates)):
            interval = (sorted_dates[i] - sorted_dates[i-1]).total_seconds() / 60  # minutes
            intervals.append(interval)
        
        avg_interval_minutes = sum(intervals) / len(intervals)
        
        # Classify pattern based on individual upload behavior
        if avg_interval_minutes < 5:
            pattern = 'sequential'
            pattern_desc = 'User recording samples one after another'
        elif avg_interval_minutes < 15:
            pattern = 'steady_progress'  
            pattern_desc = 'User taking time between samples'
        else:
            pattern = 'deliberate_pacing'
            pattern_desc = 'User taking breaks between samples'
        
        total_time_minutes = (sorted_dates[-1] - sorted_dates[0]).total_seconds() / 60
        
        return {
            'pattern': pattern,
            'pattern_description': pattern_desc,
            'average_interval_minutes': round(avg_interval_minutes, 2),
            'total_collection_time_minutes': round(total_time_minutes, 2),
            'samples_count': len(sample_dates)
        }
    
    def _determine_registration_status(self, user_data: Dict[str, Any], 
                                     samples_collected: int,
                                     quality_analysis: Dict[str, Any],
                                     time_analysis: Dict[str, Any]) -> RegistrationStatus:
        """Determine current registration status."""
        # Check explicit completion flag
        if user_data.get('registration_complete', False):
            return RegistrationStatus.COMPLETED
        
        # Check if expired
        if time_analysis.get('urgency_level') == 'expired':
            return RegistrationStatus.FAILED
        
        # Check if suspended (manual flag)
        if user_data.get('registration_suspended', False):
            return RegistrationStatus.SUSPENDED
        
        # Check completion criteria
        acceptable_samples = quality_analysis.get('acceptable_samples', 0)
        if acceptable_samples >= self.required_samples:
            return RegistrationStatus.COMPLETED
        
        # Check if in progress
        if samples_collected > 0:
            return RegistrationStatus.IN_PROGRESS
        
        # Default to not started
        return RegistrationStatus.NOT_STARTED
    
    def _generate_recommendations(self, status: RegistrationStatus,
                                samples_collected: int,
                                quality_analysis: Dict[str, Any],
                                time_analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if status == RegistrationStatus.NOT_STARTED:
            recommendations.append("Begin voice registration by recording your first voice sample")
            
        elif status == RegistrationStatus.IN_PROGRESS:
            samples_remaining = self.required_samples - samples_collected
            if samples_remaining > 0:
                recommendations.append(f"Continue with your next voice sample ({samples_remaining} remaining)")
            
            # Quality recommendations
            avg_quality = quality_analysis.get('average_quality', 0)
            if avg_quality < self.min_quality_score:
                recommendations.append("Improve recording quality - find a quieter environment")
                
            if quality_analysis.get('quality_trend') == 'declining':
                recommendations.append("Recent sample quality declined - check your microphone setup")
                
            # Time recommendations  
            urgency = time_analysis.get('urgency_level', 'low')
            time_remaining = time_analysis.get('time_remaining_minutes', 0)
            if urgency == 'urgent':
                recommendations.append(f"Complete remaining samples within {int(time_remaining)} minutes")
            elif urgency == 'moderate':
                recommendations.append(f"Continue registration - {int(time_remaining)} minutes remaining")
                
        elif status == RegistrationStatus.FAILED:
            recommendations.append("Registration expired - contact support to restart process")
            
        elif status == RegistrationStatus.SUSPENDED:
            recommendations.append("Registration suspended - contact support for assistance")
            
        elif status == RegistrationStatus.COMPLETED:
            recommendations.append("Voice registration complete - you can now use voice authentication")
        
        return recommendations
    
    def _get_next_actions(self, status: RegistrationStatus, 
                         recommendations: List[str]) -> List[str]:
        """Get specific next actions for user."""
        actions = []
        
        if status == RegistrationStatus.NOT_STARTED:
            actions.append("access_voice_registration")
            
        elif status == RegistrationStatus.IN_PROGRESS:
            actions.append("record_voice_sample")
            actions.append("check_audio_quality")
            
        elif status == RegistrationStatus.COMPLETED:
            actions.append("test_voice_authentication")
            
        elif status == RegistrationStatus.FAILED:
            actions.append("contact_support")
            
        elif status == RegistrationStatus.SUSPENDED:
            actions.append("contact_support")
        
        return actions
    
    def calculate_registration_score(self, progress_analysis: Dict[str, Any]) -> float:
        """
        Calculate overall registration score (0-100).
        
        Args:
            progress_analysis: Result from analyze_registration_progress
            
        Returns:
            Registration score from 0 to 100
        """
        metrics = progress_analysis['progress_metrics']
        quality_analysis = progress_analysis['quality_analysis']
        time_analysis = progress_analysis['time_analysis']
        
        # Base score from completion percentage
        completion_score = metrics['completion_percentage']
        
        # Quality bonus/penalty
        avg_quality = quality_analysis.get('average_quality', 0)
        quality_bonus = (avg_quality - 0.5) * 20  # -10 to +10 range
        
        # Time penalty for delays
        urgency = time_analysis.get('urgency_level', 'low')
        time_penalty = {
            'low': 0,
            'moderate': -5,
            'urgent': -15,
            'expired': -50
        }.get(urgency, 0)
        
        # Calculate final score
        final_score = max(0, min(100, completion_score + quality_bonus + time_penalty))
        
        return round(final_score, 2)


# Global user status manager instance
user_status_manager = UserStatusManager()

