from abc import ABC, abstractmethod
from typing import Optional, List

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
    async def get_all_password_hashes(self) -> List[str]:
        """Get only password hashes for uniqueness validation."""
        pass 