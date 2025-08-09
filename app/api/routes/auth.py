"""
Authentication routes for Voice Gateway API.
Handles user registration and profile management.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.ports.user_repository import UserRepositoryPort
from app.core.models import UserProfile, UserList, UserAuthenticationStatus, UserRegistrationStatus
from app.core.usecases.register_user import RegisterUserUseCase
from app.api.dependencies import get_register_use_case, get_user_repository
from app.schemas.user import UserRegisterRequest, UserRegisterResponse
from app.adapters.mappers.user_mapper import UserMapper
from typing import Dict, Any

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