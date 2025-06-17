import hashlib
from datetime import datetime
from uuid import UUID

from app.core.models.user import User
from app.core.ports.user_repository import UserRepositoryPort


class RegisterUserUseCase:
    def __init__(self, user_repository: UserRepositoryPort):
        self._user_repository = user_repository

    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()

    async def execute(self, email: str, name: str, password: str) -> User:
        # Check if user already exists
        existing_user = await self._user_repository.get_by_email(email)
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
        return await self._user_repository.save(user) 