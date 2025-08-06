"""
User mapper for converting between domain models and API schemas.
"""
from app.core.models import User, UserProfile, UserAuthenticationStatus
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
        
        Args:
            user: User domain model
            
        Returns:
            UserAuthenticationStatus: Domain model for API response
        """
        return UserAuthenticationStatus(
            user_id=str(user.id),
            name=user.name,
            email=user.email,
            registration_complete=True,
            voice_setup_complete=user.voice_setup_complete,
            voice_samples_uploaded=0,    # Would count from storage
            voice_samples_required=3,
            next_action="Upload voice samples",
            last_login=None,  # Would track login history
            account_status="active"
        ) 