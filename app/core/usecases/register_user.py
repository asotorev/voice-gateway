"""
Register user use case for Voice Gateway.
Pure domain logic for user registration with clean separation of concerns.
"""
from typing import Tuple
from app.core.models.user import User
from app.core.ports.user_repository import UserRepositoryPort
from app.core.ports.password_service import PasswordServicePort
from app.core.services.unique_password_service import UniquePasswordService
from app.core.services.password_service import PasswordService


class RegisterUserUseCase:
    """
    Use case for registering new users.
    
    """
    
    def __init__(
        self, 
        user_repository: UserRepositoryPort,
        password_service: PasswordServicePort
    ):
        """
        Initialize register user use case.
        
        Args:
            user_repository: Repository for user persistence
            password_service: Service for generating secure passwords
        """
        self.user_repository = user_repository
        self.password_service = password_service
        self.unique_password_service = UniquePasswordService(password_service, user_repository)
    
    async def execute(self, email: str, name: str) -> Tuple[User, str]:
        """
        Register a new user with automatically generated unique password.
        
        
        Args:
            email: User email address
            name: User full name
            
        Returns:
            Tuple[User, str]: (created_user, voice_password)
            
        Raises:
            ValueError: If user already exists or validation fails
            RuntimeError: If password generation or database operation fails
        """
        # Domain validation
        if not email or not email.strip():
            raise ValueError("Email is required")
        if not name or not name.strip():
            raise ValueError("Name is required")
        
        # Business rule: Check if user already exists
        existing_user = await self.user_repository.get_by_email(email.strip().lower())
        if existing_user:
            raise ValueError(f"User with email {email} already exists")
        
        # Domain service: Generate unique voice password
        try:
            voice_password = await self.unique_password_service.generate_unique_password(
                max_attempts=PasswordService.MAX_GENERATION_ATTEMPTS
            )
        except Exception:
            # Fallback to basic generation if uniqueness service fails
            voice_password = self.password_service.generate_password()
        
        # Domain logic: Create password hash for storage
        password_hash = self.password_service.hash_password(voice_password)
        
        # Domain entity: Create user (NO plain text password stored)
        user = User.create(
            email=email.strip().lower(),
            name=name.strip(),
            password_hash=password_hash
        )
        
        # Repository: Save user to persistence
        try:
            saved_user = await self.user_repository.save(user)
            
            # Return domain result (password only for one-time display)
            return saved_user, voice_password
            
        except Exception as e:
            raise RuntimeError(f"Failed to save user: {e}")