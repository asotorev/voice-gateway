"""
Authentication routes for Voice Gateway API.
Handles user registration and profile management.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.ports.user_repository import UserRepositoryPort
from app.core.ports.lambda_invocation import AuthenticationProcessingError, LambdaInvocationError
from app.core.models import UserProfile, UserList, UserAuthenticationStatus, UserRegistrationStatus
from app.core.usecases.register_user import RegisterUserUseCase
from app.core.usecases.voice_authentication import VoiceAuthenticationUseCase
from app.api.dependencies import get_register_use_case, get_user_repository, get_voice_authentication_use_case
from app.schemas.user import (
    UserRegisterRequest, UserRegisterResponse, 
    VoiceAuthenticationRequest, VoiceAuthenticationResponse, VoiceAuthenticationError
)
from app.adapters.mappers.user_mapper import UserMapper
from typing import Dict, Any
import base64
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRegisterResponse)
async def register_user(
    request: UserRegisterRequest,
    register_use_case: RegisterUserUseCase = Depends(get_register_use_case)
) -> UserRegisterResponse:
    """
    Register a new user with voice authentication capabilities.
    Creates user account and generates voice password.
        
    Args:
        request: User registration data (name, email)
        use_case: Register user use case instance
        
    Returns:
        UserRegisterResponse: Created user information with generated password (one-time display)
        
    Raises:
        HTTPException: 400 if user already exists or validation fails
        HTTPException: 500 if password generation or database operation fails
    """
    try:
        # Execute use case with individual parameters
        user, voice_password = await register_use_case.execute(
            email=request.email,
            name=request.name
        )
        
        # Use mapper for conversion
        return UserMapper.to_register_response(user, voice_password)
        
    except ValueError as e:
        # Business validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected errors
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/user/{user_id}/profile")
async def get_user_profile(
    user_id: str,
    user_repository: UserRepositoryPort = Depends(get_user_repository)
) -> UserProfile:
    """
    Get user profile information.
    
    Uses optimized projection for profile data only.
    """
    try:
        user = await user_repository.get_profile_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Use mapper for conversion
        return UserMapper.to_profile_response(user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users")
async def list_users(
    limit: int = 10,
    offset: int = 0,
    user_repository: UserRepositoryPort = Depends(get_user_repository)
) -> UserList:
    """
    List users (admin operation).
    
    Example of how to implement list operations with repository pattern.
    In real implementation, this would include proper authorization.
    """
    try:
        # Note: This would need to be implemented in the repository
        # For now, return a mock response
        return UserList(
            users=[],
            total=0,
            limit=limit,
            offset=offset,
            message="List operation not implemented in repository yet"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/user/{user_id}/status")
async def get_user_authentication_status(
    user_id: str,
    user_repository: UserRepositoryPort = Depends(get_user_repository)
) -> UserAuthenticationStatus:
    """
    Get user authentication status and login capabilities.
    
    Uses optimized projection for authentication data only.
    
    Returns authentication-related information including:
    - Account status (active, suspended, etc.)
    - Login capabilities (password-based, voice-based)
    - Last login information
    - Authentication method availability
    """
    try:
        # Get user from repository with optimized projection
        user = await user_repository.get_auth_status_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Use mapper for conversion
        return UserMapper.to_authentication_status_response(user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/user/{user_id}/registration-status")
async def get_user_registration_status(
    user_id: str,
    user_repository: UserRepositoryPort = Depends(get_user_repository)
) -> UserRegistrationStatus:
    """
    Get detailed user registration status including voice setup progress.
    
    Uses optimized projection for registration status data only.
    
    Returns comprehensive status including:
    - Registration completion status
    - Voice samples progress (X/3)
    - Progress percentage and remaining samples
    - Next actions for voice setup
    """
    try:
        user = await user_repository.get_registration_status_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Use mapper for conversion
        return UserMapper.to_registration_status_response(user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/voice-login", response_model=VoiceAuthenticationResponse)
async def authenticate_voice(
    request: VoiceAuthenticationRequest,
    voice_auth_use_case: VoiceAuthenticationUseCase = Depends(get_voice_authentication_use_case)
) -> VoiceAuthenticationResponse:
    """
    Authenticate user using voice biometrics and password transcription.
    
    Performs dual validation:
    1. Whisper transcription + password word validation
    2. Resemblyzer voice embedding comparison
    
    Args:
        request: Voice authentication request with audio data
        voice_auth_use_case: Voice authentication use case instance
        
    Returns:
        VoiceAuthenticationResponse: Detailed authentication results
        
    Raises:
        HTTPException: 400 for validation errors, 401 for authentication failures, 500 for processing errors
    """
    logger.info("Voice authentication request received", extra={
        "user_id": str(request.user_id),
        "audio_data_length": len(request.audio_data),
        "has_metadata": bool(request.metadata)
    })
    
    try:
        # Decode base64 audio data
        try:
            audio_data = base64.b64decode(request.audio_data)
        except Exception as e:
            logger.warning("Invalid base64 audio data", extra={
                "user_id": str(request.user_id),
                "error": str(e)
            })
            raise HTTPException(
                status_code=400, 
                detail="Invalid base64 audio data"
            )
        
        # Validate audio size
        if len(audio_data) < 1000:  # Minimum reasonable audio size
            raise HTTPException(
                status_code=400,
                detail="Audio data too small - minimum 1KB required"
            )
        
        if len(audio_data) > 10 * 1024 * 1024:  # Maximum 10MB
            raise HTTPException(
                status_code=400,
                detail="Audio data too large - maximum 10MB allowed"
            )
        
        # Execute voice authentication
        logger.debug("Executing voice authentication use case", extra={
            "user_id": str(request.user_id),
            "audio_size_bytes": len(audio_data)
        })
        
        auth_result = await voice_auth_use_case.authenticate_user_voice(
            user_id=request.user_id,
            audio_data=audio_data,
            metadata=request.metadata
        )
        
        # Map to response schema
        response = VoiceAuthenticationResponse(
            user_id=request.user_id,
            authentication_successful=auth_result.get('authentication_successful', False),
            confidence_score=auth_result.get('confidence_score', 0.0),
            processing_time_ms=auth_result.get('processing_time_ms', 0),
            request_id=auth_result.get('request_id', 'unknown'),
            transcription_validation=auth_result.get('transcription_validation', {}),
            voice_embedding_validation=auth_result.get('voice_embedding_validation', {}),
            validation_summary=auth_result.get('validation_summary', {})
        )
        
        # Log authentication result
        logger.info("Voice authentication completed", extra={
            "user_id": str(request.user_id),
            "request_id": response.request_id,
            "authentication_successful": response.authentication_successful,
            "confidence_score": response.confidence_score,
            "processing_time_ms": response.processing_time_ms
        })
        
        return response
        
    except ValueError as e:
        # User validation errors (user not found, not ready for auth, etc.)
        logger.warning("Voice authentication validation error", extra={
            "user_id": str(request.user_id),
            "error": str(e)
        })
        raise HTTPException(status_code=400, detail=str(e))
        
    except AuthenticationProcessingError as e:
        # Authentication processing failed (Lambda execution errors)
        logger.warning("Voice authentication processing failed", extra={
            "user_id": str(request.user_id),
            "error": str(e),
            "error_details": e.error_details
        })
        
        # Return 401 for authentication failures, 500 for processing errors
        if "authentication failed" in str(e).lower():
            raise HTTPException(status_code=401, detail="Authentication failed")
        else:
            raise HTTPException(status_code=500, detail="Authentication processing error")
            
    except LambdaInvocationError as e:
        # Lambda invocation errors (infrastructure issues)
        logger.error("Lambda invocation failed", extra={
            "user_id": str(request.user_id),
            "function_name": e.function_name,
            "error": str(e),
            "error_details": e.error_details
        })
        raise HTTPException(status_code=500, detail="Service temporarily unavailable")
        
    except Exception as e:
        # Unexpected errors
        logger.error("Unexpected error in voice authentication", extra={
            "user_id": str(request.user_id),
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/voice-login/status")
async def get_voice_authentication_status():
    """
    Get voice authentication service status.
    
    Returns current status of voice authentication components.
    """
    return {
        "service": "voice_authentication", 
        "status": "available",
        "features": [
            "whisper_transcription",
            "voice_embedding_biometric", 
            "dual_validation",
            "stream_processing"
        ],
        "supported_formats": ["wav", "mp3", "m4a"],
        "max_audio_size_mb": 10,
        "processing_type": "real_time_stream"
    }