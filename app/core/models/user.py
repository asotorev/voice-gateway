"""
User domain entity.
Represents a user in the voice authentication system.
"""
from datetime import datetime, UTC
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from dataclasses import dataclass


@dataclass
class User:
    """
    User domain entity.
    
    Represents a user with voice authentication capabilities.
    """
    id: UUID
    name: str
    email: str
    password_hash: str
    created_at: datetime
    voice_setup_complete: bool = False

    def __init__(
        self,
        id: UUID,
        email: str,
        name: str,
        password_hash: str,
        created_at: datetime,
        voice_setup_complete: bool = False
    ):
        self.id = id
        self.email = email
        self.name = name
        self.password_hash = password_hash
        self.created_at = created_at
        self.voice_setup_complete = voice_setup_complete

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
            name=name,
            email=email,
            password_hash=password_hash,
            created_at=datetime.now(UTC),
            voice_setup_complete=False
        )


@dataclass
class UserProfile:
    """Domain model for user profile information."""
    id: str
    name: str
    email: str
    created_at: str
    has_voice_password: bool
    voice_setup_complete: bool


@dataclass
class UserList:
    """Domain model for user list response."""
    users: List[UserProfile]
    total: int
    limit: int
    offset: int
    message: str


@dataclass
class UserAuthenticationStatus:
    """Domain model for user authentication status and login capabilities."""
    user_id: str
    account_status: str
    last_login: Optional[str]
    authentication_methods: Dict[str, bool]  # password_based, voice_based
    can_login: bool
    login_blocked_reason: Optional[str]


@dataclass
class UserRegistrationStatus:
    """Domain model for user voice registration progress and status."""
    user_id: str
    status: str  # "not_started", "in_progress", "completed", "failed"
    message: str
    progress: Dict[str, Any]  # current, required, remaining, percentage
    registration_complete: bool
    next_action: str
    registration_started_at: Optional[str]
    registration_completed_at: Optional[str]
    last_updated: Optional[str]