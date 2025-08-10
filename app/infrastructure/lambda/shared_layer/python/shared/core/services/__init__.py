"""
Core Services for Voice Authentication System.

This package contains shared business logic services that can be used
across multiple Lambda functions in the voice authentication system.

Services:
- audio_quality_validator: Audio file validation and quality assessment
- completion_checker: Registration completion detection and analysis
- user_status_manager: User registration status management and progress tracking
- notification_handler: Event notifications and user communication
- voice_authentication_service: Voice authentication through embedding comparison

All services are designed to be stateless and can be safely used in
serverless Lambda environments.
"""

from .audio_quality_validator import (
    AudioQualityValidator,
    AudioQualityValidationConfig,
    audio_quality_validator,
    validate_audio_quality
)

from .completion_checker import (
    RegistrationCompletionChecker,
    CompletionCriteria,
    completion_checker,
    check_registration_completion,
    should_update_completion_status
)

from .user_status_manager import (
    UserStatusManager,
    RegistrationStatus,
    user_status_manager,
    analyze_user_registration_progress,
    update_registration_status
)

from .notification_handler import (
    NotificationHandler,
    NotificationType,
    NotificationPriority,
    notification_handler,
    send_registration_notification,
    send_system_notification
)

from .voice_authentication_service import (
    VoiceAuthenticationService,
    VoiceAuthenticationConfig,
    AuthenticationResult,
    voice_authentication_service,
    authenticate_voice_sample,
    calculate_embedding_similarity
)

__all__ = [
    # Audio Quality Validator
    'AudioQualityValidator',
    'AudioQualityValidationConfig', 
    'audio_quality_validator',
    'validate_audio_quality',
    
    # Completion Checker
    'RegistrationCompletionChecker',
    'CompletionCriteria',
    'completion_checker',
    'check_registration_completion',
    'should_update_completion_status',
    
    # User Status Manager
    'UserStatusManager',
    'RegistrationStatus',
    'user_status_manager',
    'analyze_user_registration_progress',
    'update_registration_status',
    
    # Notification Handler
    'NotificationHandler',
    'NotificationType',
    'NotificationPriority',
    'notification_handler',
    'send_registration_notification',
    'send_system_notification',
    
    # Voice Authentication Service
    'VoiceAuthenticationService',
    'VoiceAuthenticationConfig',
    'AuthenticationResult',
    'voice_authentication_service',
    'authenticate_voice_sample',
    'calculate_embedding_similarity'
]
