from abc import ABC, abstractmethod
from typing import Optional

from app.core.models.user import User


class UserRepositoryPort(ABC):
    @abstractmethod
    async def save(self, user: User) -> User:
        """Save a user to the repository."""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        pass

    @abstractmethod
    async def check_password_hash_exists(self, password_hash: str) -> bool:
        """Check if a password hash exists."""
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> None:
        """Delete a user by ID."""
        pass 