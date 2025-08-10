"""
User schemas for Voice Gateway API.
Cleaned schemas focused on user operations.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from app.schemas.audio import AudioUploadResponse


class UserRegisterRequest(BaseModel):
    """
    Request schema for user registration.
    Simple registration with automatic password generation.
    """
    name: str = Field(..., min_length=1, max_length=100, description="User full name")
    email: EmailStr = Field(..., description="User email address")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate and clean user name."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class UserRegisterResponse(BaseModel):
    """
    Response schema for user registration.
    Includes generated voice password and upload URLs for audio setup.
    """
    id: UUID = Field(..., description="User unique identifier")
    name: str = Field(..., description="User full name")
    email: str = Field(..., description="User email address")
    created_at: datetime = Field(..., description="User creation timestamp")
    voice_password: str = Field(..., description="Generated voice password (one-time display)")
    message: str = Field(default="SAVE THESE WORDS - Upload 3 voice samples to complete setup", description="Important message")
    audio_upload_info: List[AudioUploadResponse] = Field(default=[], description="Audio sample upload information")
    registration_complete: bool = Field(default=False, description="Whether registration includes completed voice setup")
    next_steps: str = Field(
        default="Use the provided upload URLs to record and upload 3 voice samples saying your password",
        description="Instructions for next steps"
    )
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class UserResponse(BaseModel):
    """
    Standard user response schema (without sensitive information).
    Used for general user data retrieval and profile information.
    """
    id: UUID = Field(..., description="User unique identifier")
    name: str = Field(..., description="User full name")
    email: str = Field(..., description="User email address")
    created_at: datetime = Field(..., description="User creation timestamp")
    has_voice_password: bool = Field(default=True, description="Whether user has voice password")
    voice_setup_complete: bool = Field(default=False, description="Whether voice setup is complete")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class UserVoiceStatus(BaseModel):
    """
    User voice authentication status.
    Provides overview of voice setup progress without exposing sensitive data.
    """
    user_id: UUID = Field(..., description="User identifier")
    has_voice_password: bool = Field(..., description="Whether user has voice password")
    voice_samples_count: int = Field(..., description="Number of voice samples uploaded")
    voice_samples_required: int = Field(default=3, description="Required number of voice samples")
    voice_setup_complete: bool = Field(..., description="Whether voice setup is complete")
    setup_progress_percentage: float = Field(..., description="Setup completion percentage (0-100)")
    last_updated: Optional[datetime] = Field(None, description="Last voice data update")
    next_action: Optional[str] = Field(None, description="Suggested next action for user")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class VoiceAuthenticationRequest(BaseModel):
    """
    Request schema for voice authentication.
    User uploads audio directly to FastAPI for immediate processing.
    """
    user_id: UUID = Field(..., description="User identifier for authentication")
    audio_data: str = Field(..., description="Base64-encoded audio data (WAV format recommended)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional audio metadata")
    
    @field_validator('audio_data')
    @classmethod
    def validate_audio_data(cls, v):
        """Validate base64 audio data."""
        if not v or not v.strip():
            raise ValueError("Audio data cannot be empty")
        
        try:
            # Basic base64 validation
            import base64
            decoded = base64.b64decode(v)
            if len(decoded) < 1000:  # Minimum reasonable audio file size
                raise ValueError("Audio data seems too small to be valid")
            return v
        except Exception:
            raise ValueError("Invalid base64 audio data")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class VoiceAuthenticationResponse(BaseModel):
    """
    Response schema for voice authentication.
    Contains dual validation results (transcription + voice embedding).
    """
    user_id: UUID = Field(..., description="User identifier")
    authentication_successful: bool = Field(..., description="Overall authentication result")
    confidence_score: float = Field(..., description="Combined confidence score (0.0-1.0)")
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    request_id: str = Field(..., description="Unique request identifier for tracking")
    
    # Detailed validation results
    transcription_validation: Dict[str, Any] = Field(..., description="Whisper transcription and password validation results")
    voice_embedding_validation: Dict[str, Any] = Field(..., description="Voice biometric authentication results")
    
    # Authentication decision breakdown
    validation_summary: Dict[str, Any] = Field(..., description="Summary of both validation methods")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(), description="Authentication timestamp")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class VoiceAuthenticationError(BaseModel):
    """
    Error response schema for voice authentication failures.
    """
    error_type: str = Field(..., description="Type of authentication error")
    error_message: str = Field(..., description="Human-readable error message")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")
    user_id: Optional[UUID] = Field(None, description="User identifier if available")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(), description="Error timestamp")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }