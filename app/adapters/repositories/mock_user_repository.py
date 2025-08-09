from typing import Dict, Optional

from app.core.models.user import User
from app.core.ports.user_repository import UserRepositoryPort


class MockUserRepository(UserRepositoryPort):
    def __init__(self):
        self._users: Dict[str, User] = {}

    async def save(self, user: User) -> User:
        self._users[user.id] = user
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def get_profile_by_id(self, user_id: str) -> Optional[User]:
        """Mock implementation - returns same as get_by_id for simplicity."""
        return await self.get_by_id(user_id)

    async def get_auth_status_by_id(self, user_id: str) -> Optional[User]:
        """Mock implementation - returns same as get_by_id for simplicity."""
        return await self.get_by_id(user_id)

    async def get_registration_status_by_id(self, user_id: str) -> Optional[User]:
        """Mock implementation - returns same as get_by_id for simplicity."""
        return await self.get_by_id(user_id)

    async def check_password_hash_exists(self, password_hash: str) -> bool:
        for user in self._users.values():
            if user.password_hash == password_hash:
                return True
        return False

    async def delete(self, user_id: str) -> None:
        if user_id in self._users:
            del self._users[user_id] 