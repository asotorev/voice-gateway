"""
Notification Service for Voice Authentication System.

Provides comprehensive notification handling for user registration events,
status updates, completion notifications, and error reporting in the
voice authentication system.

This service is part of the shared layer and can be used by multiple
Lambda functions for consistent notification management.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications supported by the system."""
    REGISTRATION_STARTED = "registration_started"
    SAMPLE_RECORDED = "sample_recorded"
    SAMPLE_PROCESSED = "sample_processed"
    QUALITY_WARNING = "quality_warning"
    REGISTRATION_PROGRESS = "registration_progress"
    REGISTRATION_COMPLETED = "registration_completed"
    REGISTRATION_FAILED = "registration_failed"
    ERROR_OCCURRED = "error_occurred"
    STATUS_UPDATED = "status_updated"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationHandler:
    """
    Comprehensive notification handling service.
    
    Manages all types of notifications for the voice authentication system,
    including user progress updates, completion notifications, error alerts,
    and system status messages.
    """
    
    def __init__(self):
        """Initialize notification handler with configuration."""
        self.enable_notifications = os.getenv('ENABLE_NOTIFICATIONS', 'true').lower() == 'true'
        self.notification_topic_arn = os.getenv('NOTIFICATION_TOPIC_ARN', '')
        self.email_notifications = os.getenv('ENABLE_EMAIL_NOTIFICATIONS', 'false').lower() == 'true'
        self.sms_notifications = os.getenv('ENABLE_SMS_NOTIFICATIONS', 'false').lower() == 'true'
        self.webhook_url = os.getenv('NOTIFICATION_WEBHOOK_URL', '')
        
        logger.info("Notification handler initialized", extra={
            "notifications_enabled": self.enable_notifications,
            "has_topic_arn": bool(self.notification_topic_arn),
            "email_enabled": self.email_notifications,
            "sms_enabled": self.sms_notifications,
            "webhook_configured": bool(self.webhook_url)
        })
    
    def send_registration_started_notification(self, user_id: str, 
                                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send notification when user starts voice registration.
        
        Args:
            user_id: User identifier
            metadata: Additional notification metadata
            
        Returns:
            Notification result dictionary
        """
        notification_data = {
            'user_id': user_id,
            'event': 'registration_started',
            'message': 'Voice registration process has been initiated',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {}
        }
        
        return self._send_notification(
            NotificationType.REGISTRATION_STARTED,
            notification_data,
            NotificationPriority.NORMAL
        )
    
    def send_sample_recorded_notification(self, user_id: str, sample_info: Dict[str, Any],
                                        metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send notification when a voice sample is recorded.
        
        Args:
            user_id: User identifier
            sample_info: Information about the recorded sample
            metadata: Additional notification metadata
            
        Returns:
            Notification result dictionary
        """
        notification_data = {
            'user_id': user_id,
            'event': 'sample_recorded',
            'message': f'Voice sample {sample_info.get("sample_number", "N/A")} has been recorded',
            'sample_info': sample_info,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {}
        }
        
        return self._send_notification(
            NotificationType.SAMPLE_RECORDED,
            notification_data,
            NotificationPriority.NORMAL
        )
    
    def send_sample_processed_notification(self, user_id: str, processing_result: Dict[str, Any],
                                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send notification when a voice sample is processed.
        
        Args:
            user_id: User identifier
            processing_result: Result of sample processing
            metadata: Additional notification metadata
            
        Returns:
            Notification result dictionary
        """
        success = processing_result.get('success', False)
        quality_score = processing_result.get('quality_score', 0.0)
        
        message = f"Voice sample processed successfully (quality: {quality_score:.2f})" if success else "Voice sample processing failed"
        
        notification_data = {
            'user_id': user_id,
            'event': 'sample_processed',
            'message': message,
            'processing_result': processing_result,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {}
        }
        
        priority = NotificationPriority.NORMAL if success else NotificationPriority.HIGH
        
        return self._send_notification(
            NotificationType.SAMPLE_PROCESSED,
            notification_data,
            priority
        )
    
    def send_quality_warning_notification(self, user_id: str, quality_issues: List[str],
                                        quality_score: float,
                                        metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send notification for quality warnings.
        
        Args:
            user_id: User identifier
            quality_issues: List of identified quality issues
            quality_score: Current quality score
            metadata: Additional notification metadata
            
        Returns:
            Notification result dictionary
        """
        notification_data = {
            'user_id': user_id,
            'event': 'quality_warning',
            'message': f'Audio quality warning: score {quality_score:.2f}',
            'quality_issues': quality_issues,
            'quality_score': quality_score,
            'recommendations': self._generate_quality_recommendations(quality_issues),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {}
        }
        
        return self._send_notification(
            NotificationType.QUALITY_WARNING,
            notification_data,
            NotificationPriority.HIGH
        )
    
    def send_registration_progress_notification(self, user_id: str, progress_info: Dict[str, Any],
                                              metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send notification for registration progress updates.
        
        Args:
            user_id: User identifier
            progress_info: Progress information
            metadata: Additional notification metadata
            
        Returns:
            Notification result dictionary
        """
        completion_percentage = progress_info.get('completion_percentage', 0)
        samples_collected = progress_info.get('samples_collected', 0)
        samples_remaining = progress_info.get('samples_remaining', 0)
        
        message = f"Registration progress: {completion_percentage}% complete ({samples_collected} samples recorded, {samples_remaining} remaining)"
        
        notification_data = {
            'user_id': user_id,
            'event': 'registration_progress',
            'message': message,
            'progress_info': progress_info,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {}
        }
        
        return self._send_notification(
            NotificationType.REGISTRATION_PROGRESS,
            notification_data,
            NotificationPriority.NORMAL
        )
    
    def send_registration_completed_notification(self, user_id: str, completion_info: Dict[str, Any],
                                               metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send notification when registration is completed.
        
        Args:
            user_id: User identifier
            completion_info: Completion information
            metadata: Additional notification metadata
            
        Returns:
            Notification result dictionary
        """
        total_samples = completion_info.get('total_samples', 0)
        average_quality = completion_info.get('average_quality', 0.0)
        
        message = f"Voice registration completed successfully! {total_samples} samples recorded with average quality {average_quality:.2f}"
        
        notification_data = {
            'user_id': user_id,
            'event': 'registration_completed',
            'message': message,
            'completion_info': completion_info,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {}
        }
        
        return self._send_notification(
            NotificationType.REGISTRATION_COMPLETED,
            notification_data,
            NotificationPriority.HIGH
        )
    
    def send_registration_failed_notification(self, user_id: str, failure_info: Dict[str, Any],
                                            metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send notification when registration fails.
        
        Args:
            user_id: User identifier
            failure_info: Failure information
            metadata: Additional notification metadata
            
        Returns:
            Notification result dictionary
        """
        failure_reason = failure_info.get('reason', 'Unknown error')
        
        message = f"Voice registration failed: {failure_reason}"
        
        notification_data = {
            'user_id': user_id,
            'event': 'registration_failed',
            'message': message,
            'failure_info': failure_info,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {}
        }
        
        return self._send_notification(
            NotificationType.REGISTRATION_FAILED,
            notification_data,
            NotificationPriority.CRITICAL
        )
    
    def send_error_notification(self, error_info: Dict[str, Any],
                              metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send notification for system errors.
        
        Args:
            error_info: Error information
            metadata: Additional notification metadata
            
        Returns:
            Notification result dictionary
        """
        error_type = error_info.get('error_type', 'Unknown')
        error_message = error_info.get('error_message', 'An error occurred')
        
        notification_data = {
            'event': 'error_occurred',
            'message': f'System error: {error_type} - {error_message}',
            'error_info': error_info,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {}
        }
        
        return self._send_notification(
            NotificationType.ERROR_OCCURRED,
            notification_data,
            NotificationPriority.CRITICAL
        )
    
    def send_status_update_notification(self, user_id: str, status_info: Dict[str, Any],
                                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send notification for status updates.
        
        Args:
            user_id: User identifier
            status_info: Status update information
            metadata: Additional notification metadata
            
        Returns:
            Notification result dictionary
        """
        old_status = status_info.get('old_status', 'unknown')
        new_status = status_info.get('new_status', 'unknown')
        
        message = f"Status updated from {old_status} to {new_status}"
        
        notification_data = {
            'user_id': user_id,
            'event': 'status_updated',
            'message': message,
            'status_info': status_info,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {}
        }
        
        return self._send_notification(
            NotificationType.STATUS_UPDATED,
            notification_data,
            NotificationPriority.NORMAL
        )
    
    def _send_notification(self, notification_type: NotificationType,
                          notification_data: Dict[str, Any],
                          priority: NotificationPriority) -> Dict[str, Any]:
        """
        Internal method to send notifications through configured channels.
        
        Args:
            notification_type: Type of notification
            notification_data: Notification payload
            priority: Notification priority
            
        Returns:
            Notification delivery result
        """
        if not self.enable_notifications:
            logger.debug("Notifications disabled, skipping notification", extra={
                "notification_type": notification_type.value,
                "priority": priority.value
            })
            return {
                'sent': False,
                'reason': 'notifications_disabled',
                'notification_type': notification_type.value
            }
        
        logger.info("Sending notification", extra={
            "notification_type": notification_type.value,
            "priority": priority.value,
            "user_id": notification_data.get('user_id', 'system')
        })
        
        # Format notification message
        formatted_notification = self._format_notification(notification_type, notification_data, priority)
        
        # Send through available channels
        delivery_results = []
        
        # Log notification (always enabled)
        delivery_results.append(self._log_notification(formatted_notification))
        
        # SNS/SQS delivery (if configured)
        if self.notification_topic_arn:
            delivery_results.append(self._send_sns_notification(formatted_notification))
        
        # Webhook delivery (if configured)
        if self.webhook_url:
            delivery_results.append(self._send_webhook_notification(formatted_notification))
        
        # Determine overall delivery status
        successful_deliveries = sum(1 for result in delivery_results if result.get('success', False))
        
        return {
            'sent': successful_deliveries > 0,
            'notification_type': notification_type.value,
            'priority': priority.value,
            'delivery_results': delivery_results,
            'successful_deliveries': successful_deliveries,
            'total_channels': len(delivery_results)
        }
    
    def _format_notification(self, notification_type: NotificationType,
                           notification_data: Dict[str, Any],
                           priority: NotificationPriority) -> Dict[str, Any]:
        """Format notification for delivery."""
        return {
            'notification_type': notification_type.value,
            'priority': priority.value,
            'data': notification_data,
            'formatted_at': datetime.now(timezone.utc).isoformat()
        }
    
    def _log_notification(self, formatted_notification: Dict[str, Any]) -> Dict[str, Any]:
        """Log notification to system logs."""
        try:
            logger.info("Notification delivered via log", extra=formatted_notification)
            return {'channel': 'log', 'success': True}
        except Exception as e:
            logger.error(f"Failed to log notification: {e}")
            return {'channel': 'log', 'success': False, 'error': str(e)}
    
    def _send_sns_notification(self, formatted_notification: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification via SNS (placeholder - would integrate with actual SNS)."""
        try:
            # Placeholder for SNS integration
            logger.info("Would send SNS notification", extra=formatted_notification)
            return {'channel': 'sns', 'success': True, 'simulated': True}
        except Exception as e:
            logger.error(f"Failed to send SNS notification: {e}")
            return {'channel': 'sns', 'success': False, 'error': str(e)}
    
    def _send_webhook_notification(self, formatted_notification: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification via webhook (placeholder - would integrate with actual HTTP client)."""
        try:
            # Placeholder for webhook integration
            logger.info("Would send webhook notification", extra=formatted_notification)
            return {'channel': 'webhook', 'success': True, 'simulated': True}
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return {'channel': 'webhook', 'success': False, 'error': str(e)}
    
    def _generate_quality_recommendations(self, quality_issues: List[str]) -> List[str]:
        """Generate recommendations based on quality issues."""
        recommendations = []
        
        for issue in quality_issues:
            if 'noise' in issue.lower():
                recommendations.append("Record in a quiet environment")
            elif 'volume' in issue.lower() or 'amplitude' in issue.lower():
                recommendations.append("Adjust microphone distance and speak clearly")
            elif 'duration' in issue.lower():
                recommendations.append("Ensure recording meets minimum duration requirements")
            elif 'format' in issue.lower():
                recommendations.append("Check audio format and quality settings")
            else:
                recommendations.append("Review recording setup and environment")
        
        return recommendations


# Global instance for easy access
notification_handler = NotificationHandler()


def send_registration_notification(notification_type: str, user_id: str, 
                                 data: Dict[str, Any],
                                 metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function for sending registration-related notifications.
    
    Args:
        notification_type: Type of notification to send
        user_id: User identifier
        data: Notification data
        metadata: Additional metadata
        
    Returns:
        Notification delivery result
    """
    handler_methods = {
        'registration_started': notification_handler.send_registration_started_notification,
        'sample_recorded': notification_handler.send_sample_recorded_notification,
        'sample_processed': notification_handler.send_sample_processed_notification,
        'quality_warning': notification_handler.send_quality_warning_notification,
        'registration_progress': notification_handler.send_registration_progress_notification,
        'registration_completed': notification_handler.send_registration_completed_notification,
        'registration_failed': notification_handler.send_registration_failed_notification,
        'status_updated': notification_handler.send_status_update_notification
    }
    
    handler_method = handler_methods.get(notification_type)
    if not handler_method:
        logger.warning(f"Unknown notification type: {notification_type}")
        return {'sent': False, 'reason': 'unknown_notification_type'}
    
    return handler_method(user_id, data, metadata)


def send_system_notification(notification_type: str, data: Dict[str, Any],
                           metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function for sending system-level notifications.
    
    Args:
        notification_type: Type of notification to send
        data: Notification data
        metadata: Additional metadata
        
    Returns:
        Notification delivery result
    """
    if notification_type == 'error_occurred':
        return notification_handler.send_error_notification(data, metadata)
    else:
        logger.warning(f"Unknown system notification type: {notification_type}")
        return {'sent': False, 'reason': 'unknown_notification_type'}
