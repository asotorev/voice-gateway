from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


class User:
    def __init__(
        self,
        id: UUID,
        email: str,
        name: str,
        password_hash: str,
        created_at: datetime,
    ):
        self.id = id
        self.email = email
        self.name = name
        self.password_hash = password_hash
        self.created_at = created_at

    @classmethod
    def create(cls, email: str, name: str, password_hash: str) -> "User":
        return cls(
            id=uuid4(),
            email=email,
            name=name,
            password_hash=password_hash,
            created_at=datetime.utcnow(),
        ) 