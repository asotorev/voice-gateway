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