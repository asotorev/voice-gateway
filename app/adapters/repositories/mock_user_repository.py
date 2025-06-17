from typing import Dict, Optional

from app.core.models.user import User
from app.core.ports.user_repository import UserRepositoryPort


class MockUserRepository(UserRepositoryPort):
    def __init__(self):
        self._users: Dict[str, User] = {}

    async def save(self, user: User) -> User:
        self._users[user.id] = user
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        for user in self._users.values():
            if user.email == email:
                return user
        return None 