"""
Register user use case for Voice Gateway.
Handles user registration with automatic password generation and voice authentication setup.
"""
import hashlib
from datetime import datetime
from app.core.models.user import User
from app.core.ports.user_repository import UserRepositoryPort
from app.core.ports.password_service import PasswordServicePort


class RegisterUserUseCase:
    """
    Use case for registering new users with automatic password generation.
    
    Generates secure 2-word passwords and handles user persistence with
    voice authentication capabilities.
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
    
    async def execute(self, email: str, name: str) -> tuple[User, str]:
        """
        Register a new user with automatically generated password.
        
        Args:
            email: User email address
            name: User full name
            
        Returns:
            tuple[User, str]: (user, voice_password)
            
        Raises:
            ValueError: If user already exists or validation fails
            RuntimeError: If password generation or database operation fails
        """
        # Validate input
        if not email or not email.strip():
            raise ValueError("Email is required")
            
        if not name or not name.strip():
            raise ValueError("Name is required")
            
        # Check if user already exists
        existing_user = await self.user_repository.get_by_email(email.strip().lower())
        if existing_user:
            raise ValueError(f"User with email {email} already exists")
        
        # Generate secure voice password
        try:
            voice_password = self.password_service.generate_password()
        except Exception as e:
            raise RuntimeError(f"Failed to generate password: {e}")
        
        # Create password hash for storage
        password_hash = self.password_service.hash_password(voice_password)
        
        # Create user entity (NO password in plain text)
        user = User.create(
            email=email.strip().lower(),
            name=name.strip(),
            password_hash=password_hash
        )
        
        # Save user to repository
        try:
            saved_user = await self.user_repository.save(user)
            
            # Return user and password separately (password only for one-time display)
            return saved_user, voice_password
            
        except Exception as e:
            raise RuntimeError(f"Failed to save user: {e}")