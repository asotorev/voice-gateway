"""
Simple notification handler for voice registration completion.

This module provides basic logging and response formatting for registration
events, focused on completion detection and user feedback through Lambda responses.
"""
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class RegistrationEvent(Enum):
    """Types of registration events."""
    SAMPLE_RECORDED = "sample_recorded"
    QUALITY_WARNING = "quality_warning"
    REGISTRATION_COMPLETED = "registration_completed"
    REGISTRATION_FAILED = "registration_failed"


class SimpleNotificationHandler:
    """
    Simple handler for registration completion events.
    
    Provides logging and response formatting for voice registration events,
    focused on user feedback through Lambda responses and logging.
    """
    
    def __init__(self):
        """Initialize simple notification handler."""
        self.enabled = os.getenv('NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
        self.include_user_data = os.getenv('INCLUDE_USER_DATA_IN_NOTIFICATIONS', 'false').lower() == 'true'
        
        logger.info("Simple notification handler initialized", extra={
            "enabled": self.enabled
        })
    
    def create_event_response(self, event_type: RegistrationEvent, 
                            user_id: str,
                            event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create response data for registration event.
        
        This is used to enhance Lambda responses with user-friendly messages
        and next actions for the frontend.
        
        Args:
            event_type: Type of registration event
            user_id: User identifier
            event_data: Event-specific data
            
        Returns:
            Dict with response data for frontend
        """
        if not self.enabled:
            return {"notification": "disabled"}
        
        # Sanitize user data if needed
        safe_user_id = user_id if self.include_user_data else "***masked***"
        
        # Create base response
        response = {
            "event_type": event_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": safe_user_id
        }
        
        # Add event-specific response data
        if event_type == RegistrationEvent.SAMPLE_RECORDED:
            sample_count = event_data.get('total_samples', 0)
            required_count = event_data.get('required_samples', 3)
            remaining = required_count - sample_count
            
            response.update({
                "success": True,
                "message": f"Voice sample {sample_count} recorded successfully!",
                "progress": {
                    "current": sample_count,
                    "required": required_count,
                    "remaining": remaining,
                    "percentage": round((sample_count / required_count) * 100, 1)
                },
                "next_action": "record_next_sample" if remaining > 0 else "wait_for_completion",
                "next_message": f"Record your next voice sample ({remaining} remaining)" if remaining > 0 else "Processing completion..."
            })
            
        elif event_type == RegistrationEvent.QUALITY_WARNING:
            quality_score = event_data.get('quality_score', 0)
            
            response.update({
                "success": True,
                "warning": True,
                "message": f"Sample recorded but audio quality is low (score: {quality_score:.2f})",
                "recommendation": "Find a quieter environment and speak clearly for better results",
                "next_action": "improve_quality"
            })
            
        elif event_type == RegistrationEvent.REGISTRATION_COMPLETED:
            completion_confidence = event_data.get('completion_confidence', 1.0)
            
            response.update({
                "success": True,
                "completed": True,
                "message": "Voice registration completed successfully!",
                "details": {
                    "confidence": completion_confidence,
                    "total_samples": event_data.get('total_samples', 3),
                    "completion_time": response["timestamp"]
                },
                "next_action": "login_enabled",
                "next_message": "You can now use voice authentication to log in!"
            })
            
        elif event_type == RegistrationEvent.REGISTRATION_FAILED:
            failure_reason = event_data.get('failure_reason', 'unknown')
            
            response.update({
                "success": False,
                "failed": True,
                "message": f"Voice registration failed: {failure_reason}",
                "next_action": "contact_support",
                "next_message": "Please contact support or restart the registration process"
            })
        
        # Log the event
        self._log_event(event_type, user_id, response)
        
        return response
    
    def _log_event(self, event_type: RegistrationEvent, user_id: str, response_data: Dict[str, Any]) -> None:
        """Log registration event for monitoring."""
        log_level = logging.INFO
        
        # Use higher log level for important events
        if event_type == RegistrationEvent.REGISTRATION_COMPLETED:
            log_level = logging.INFO
        elif event_type == RegistrationEvent.REGISTRATION_FAILED:
            log_level = logging.ERROR
        elif event_type == RegistrationEvent.QUALITY_WARNING:
            log_level = logging.WARNING
        
        logger.log(log_level, f"Registration event: {event_type.value}", extra={
            "event_type": event_type.value,
            "user_id": user_id if self.include_user_data else "***masked***",
            "success": response_data.get("success", False),
            "completed": response_data.get("completed", False),
            "message": response_data.get("message", "")
        })
    
    def notify_sample_recorded(self, user_id: str, sample_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method for sample recorded events."""
        return self.create_event_response(
            RegistrationEvent.SAMPLE_RECORDED,
            user_id,
            sample_data
        )
    
    def notify_registration_completed(self, user_id: str, completion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method for registration completion events."""
        return self.create_event_response(
            RegistrationEvent.REGISTRATION_COMPLETED,
            user_id,
            completion_data
        )
    
    def notify_quality_warning(self, user_id: str, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method for quality warning events."""
        return self.create_event_response(
            RegistrationEvent.QUALITY_WARNING,
            user_id,
            quality_data
        )
    
    def notify_registration_failed(self, user_id: str, failure_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method for registration failure events."""
        return self.create_event_response(
            RegistrationEvent.REGISTRATION_FAILED,
            user_id,
            failure_data
        )
    
    def create_status_response(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create response for registration status endpoint (Option 2).
        
        This is used by GET /api/user/registration-status endpoint
        to provide current registration status to frontend.
        
        Args:
            user_data: Complete user record from DynamoDB
            
        Returns:
            Status response for frontend polling
        """
        user_id = user_data.get('user_id', 'unknown')
        registration_complete = user_data.get('registration_complete', False)
        voice_embeddings = user_data.get('voice_embeddings', [])
        
        response = {
            "user_id": user_id if self.include_user_data else "***masked***",
            "registration_complete": registration_complete,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if registration_complete:
            completion_time = user_data.get('registration_completed_at')
            response.update({
                "status": "completed",
                "message": "Voice registration is complete! You can now log in with voice authentication.",
                "completion_time": completion_time,
                "next_action": "login_enabled"
            })
        else:
            samples_count = len(voice_embeddings)
            required_samples = 3  # Could be from config
            
            response.update({
                "status": "in_progress",
                "message": f"Voice registration in progress ({samples_count}/{required_samples} samples)",
                "progress": {
                    "current": samples_count,
                    "required": required_samples,
                    "remaining": required_samples - samples_count,
                    "percentage": round((samples_count / required_samples) * 100, 1)
                },
                "next_action": "continue_recording" if samples_count > 0 else "start_recording"
            })
        
        return response


# Global simple notification handler instance
notification_handler = SimpleNotificationHandler()