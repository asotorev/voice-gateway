"""
User repository port (interface) for user data operations.

This module defines the contract for user data access operations,
following Clean Architecture principles by defining the interface
without implementation details.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ..models.voice_embedding import VoiceEmbedding


class UserRepositoryPort(ABC):
    """
    Port (interface) for user data repository operations.
    
    Defines the contract for user data access including voice embeddings,
    registration status, and user profile management.
    """
    
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user record by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            User record dict or None if not found
        """
        pass
    
    @abstractmethod
    async def add_voice_embedding(
        self,
        user_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add a voice embedding to user record.
        
        Args:
            user_id: User identifier
            embedding: Voice embedding vector
            metadata: Embedding metadata
            
        Returns:
            Updated user record information
        """
        pass
    
    @abstractmethod
    async def get_user_embeddings(self, user_id: str) -> List[VoiceEmbedding]:
        """
        Get all voice embeddings for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of user's voice embeddings
        """
        pass
    
    @abstractmethod
    async def update_user_status(
        self,
        user_id: str,
        status_update: Dict[str, Any]
    ) -> bool:
        """
        Update user status information.
        
        Args:
            user_id: User identifier
            status_update: Status fields to update
            
        Returns:
            True if update was successful
        """
        pass
    
    @abstractmethod
    async def get_user_embedding_count(self, user_id: str) -> int:
        """
        Get count of voice embeddings for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of voice embeddings stored
        """
        pass
    
    @abstractmethod
    async def get_user_registration_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get user registration completion status.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with registration status information
        """
        pass
