"""
User mapper for converting between domain models and API schemas.
"""
from app.core.models import User, UserProfile, UserAuthenticationStatus, UserRegistrationStatus
from app.schemas.user import UserRegisterResponse


class UserMapper:
    """Mapper for user-related conversions."""
    
    @staticmethod
    def to_register_response(user: User, voice_password: str, registration_complete: bool = False) -> UserRegisterResponse:
        """
        Convert User domain model to UserRegisterResponse API schema.
        
        Args:
            user: User domain model
            voice_password: Generated voice password
            registration_complete: Whether the registration process is complete
            
        Returns:
            UserRegisterResponse: API response schema
        """
        if registration_complete:
            message = "SAVE THESE WORDS - Generate upload URLs through /audio endpoints"
            next_steps = "Use /audio/upload endpoint to generate upload URLs for voice samples"
        else:
            message = "SAVE THESE WORDS - Upload 3 voice samples to complete setup"
            next_steps = "Use the provided upload URLs to record and upload 3 voice samples saying your password"
        
        return UserRegisterResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            voice_password=voice_password,
            message=message,
            audio_upload_info=[],
            registration_complete=registration_complete,
            next_steps=next_steps
        )
    
    @staticmethod
    def to_profile_response(user: User) -> UserProfile:
        """
        Convert User domain model to UserProfile domain model.
        
        Args:
            user: User domain model
            
        Returns:
            UserProfile: Domain model for API response
        """
        return UserProfile(
            id=str(user.id),
            name=user.name,
            email=user.email,
            created_at=user.created_at.isoformat(),
            has_voice_password=True,  # Don't expose actual password
            voice_setup_complete=user.voice_setup_complete
        )
    
    @staticmethod
    def to_authentication_status_response(user: User) -> UserAuthenticationStatus:
        """
        Convert User domain model to UserAuthenticationStatus domain model.
        
        Focuses on authentication capabilities and login status.
        
        Args:
            user: User domain model
            
        Returns:
            UserAuthenticationStatus: Domain model for API response
        """
        # Determine authentication capabilities
        voice_setup_complete = getattr(user, 'voice_setup_complete', False)
        
        # Determine registration status based on calculated field
        voice_embeddings_count = getattr(user, 'voice_embeddings_count', 0)
        registration_complete = voice_embeddings_count >= 3
        
        # Determine authentication methods available
        password_based = True  # Always available after registration
        voice_based = voice_setup_complete
        
        # Determine if user can login
        can_login = registration_complete
        login_blocked_reason = None
        
        if not registration_complete:
            login_blocked_reason = "registration_incomplete"
        elif not voice_setup_complete:
            login_blocked_reason = "voice_setup_incomplete"
        
        # Determine account status
        account_status = "active"
        
        return UserAuthenticationStatus(
            user_id=str(user.id),
            account_status=account_status,
            last_login=None,  # Would track login history
            authentication_methods={
                "password_based": password_based,
                "voice_based": voice_based
            },
            can_login=can_login,
            login_blocked_reason=login_blocked_reason
        )
    
    @staticmethod
    def to_registration_status_response(user: User) -> UserRegistrationStatus:
        """
        Convert User domain model to UserRegistrationStatus domain model.
        
        Focuses on voice registration progress and setup status.
        
        Args:
            user: User domain model
            
        Returns:
            UserRegistrationStatus: Domain model for API response
        """
        # Get voice embeddings count from calculated field
        samples_count = getattr(user, 'voice_embeddings_count', 0)
        required_samples = 3
        
        # Calculate progress
        completion_percentage = min(100, (samples_count / required_samples) * 100)
        samples_remaining = max(0, required_samples - samples_count)
        
        # Determine registration status based on calculated field
        registration_complete = samples_count >= required_samples
        
        if registration_complete:
            status = "completed"
            message = "Voice registration is complete! You can now log in with voice authentication."
            next_action = "login_enabled"
        elif samples_count == 0:
            status = "not_started"
            message = "Start voice registration by recording your first voice sample"
            next_action = "start_recording"
        else:
            status = "in_progress"
            message = f"Voice registration in progress ({samples_count}/{required_samples} samples)"
            next_action = "continue_recording"
        
        # Determine registration timestamps
        # Note: These would need to be calculated by Lambda and stored as separate fields
        # For now, we'll use None since we don't have the embedding timestamps
        registration_started_at = None
        registration_completed_at = None
        
        return UserRegistrationStatus(
            user_id=str(user.id),
            status=status,
            message=message,
            progress={
                "current": samples_count,
                "required": required_samples,
                "remaining": samples_remaining,
                "percentage": round(completion_percentage, 1)
            },
            registration_complete=registration_complete,
            next_action=next_action,
            registration_started_at=registration_started_at,
            registration_completed_at=registration_completed_at,
            last_updated=getattr(user, 'updated_at', None)
        ) 