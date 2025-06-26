"""
User domain entity.
Represents a user in the voice authentication system.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4


class User:
    """
    User domain entity.
    
    Represents a user with voice authentication capabilities.
    """
    
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
        self.voice_embeddings: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def create(cls, email: str, name: str, password_hash: str) -> 'User':
        """
        Create a new user instance.
        
        Args:
            email: User email address
            name: User full name
            password_hash: Hashed password
            
        Returns:
            User: New user instance with generated ID and timestamp
        """
        return cls(
            id=uuid4(),
            email=email,
            name=name,
            password_hash=password_hash,
            created_at=datetime.utcnow(),
        ) 