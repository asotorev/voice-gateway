"""
Register User Use Case.
Handles user registration with password hashing and email validation.
"""
import hashlib
from app.core.models.user import User
from app.core.ports.user_repository import UserRepositoryPort


class RegisterUserUseCase:
    """
    Use case for registering new users.
    
    Validates email uniqueness, hashes passwords, and persists user data.
    """
    
    def __init__(self, user_repository: UserRepositoryPort):
        self.user_repository = user_repository

    def _hash_password(self, password: str) -> str:
        """
        Hash password using SHA256.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()

    async def execute(self, email: str, name: str, password: str) -> User:
        """
        Execute user registration.
        
        Args:
            request: User registration request with name, email, password
            
        Returns:
            User: Created user entity
            
        Raises:
            ValueError: If user with email already exists
        """
        # Check if user already exists
        existing_user = await self.user_repository.get_by_email(email)
        if existing_user:
            raise ValueError("User with this email already exists")

        # Hash the password
        password_hash = self._hash_password(password)

        # Create new user using the create class method
        user = User.create(
            email=email,
            name=name,
            password_hash=password_hash
        )

        # Save user
        return await self.user_repository.save(user)