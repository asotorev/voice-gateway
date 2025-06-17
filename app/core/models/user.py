from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


class User:
    def __init__(
        self,
        id: UUID,
        email: str,
        name: str,
        created_at: datetime,
    ):
        self.id = id
        self.email = email
        self.name = name
        self.created_at = created_at

    @classmethod
    def create(cls, email: str, name: str) -> "User":
        return cls(
            id=uuid4(),
            email=email,
            name=name,
            created_at=datetime.utcnow(),
        ) 