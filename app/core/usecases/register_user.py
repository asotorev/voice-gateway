from datetime import datetime
from uuid import UUID

from app.core.models.user import User
from app.core.ports.user_repository import UserRepositoryPort


class RegisterUserUseCase:
    def __init__(self, user_repository: UserRepositoryPort):
        self._user_repository = user_repository

    async def execute(self, email: str, name: str) -> User:
        # Check if user already exists
        existing_user = await self._user_repository.get_by_email(email)
        if existing_user:
            raise ValueError("User with this email already exists")

        # Create new user using the create class method
        user = User.create(email=email, name=name)

        # Save user
        return await self._user_repository.save(user) 