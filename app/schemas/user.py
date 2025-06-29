"""
User schemas for Voice Gateway API.
Defines request and response models for user-related operations.
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class UserRegisterRequest(BaseModel):
    """
    Request schema for user registration.
    Password is automatically generated, so only name and email are required.
    """
    name: str
    email: EmailStr


class UserRegisterResponse(BaseModel):
    """
    Response schema for user registration.
    Includes generated voice password for one-time display.
    """
    id: UUID
    name: str
    email: str
    created_at: datetime
    voice_password: str
    message: str = "SAVE THESE WORDS - No recovery available"
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class UserResponse(BaseModel):
    """
    Standard user response schema (without password).
    Used for general user data retrieval.
    """
    id: UUID
    name: str
    email: str
    created_at: datetime
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }