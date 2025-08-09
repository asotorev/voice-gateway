"""
Storage service port (interface) for audio file operations.

This module defines the contract for audio file storage operations,
following Clean Architecture principles by defining the interface
without implementation details.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class StorageServicePort(ABC):
    """
    Port (interface) for audio file storage operations.
    
    Defines the contract for audio file download, upload,
    and metadata retrieval from storage systems.
    """
    
    @abstractmethod
    async def download_audio_file(self, file_path: str) -> bytes:
        """
        Download audio file from storage.
        
        Args:
            file_path: Path to the audio file in storage
            
        Returns:
            Audio file content as bytes
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is invalid or too large
        """
        pass
    
    @abstractmethod
    async def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Get metadata for an audio file.
        
        Args:
            file_path: Path to the audio file in storage
            
        Returns:
            Dict with file metadata (size, format, etc.)
        """
        pass
    
    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """
        Check if audio file exists in storage.
        
        Args:
            file_path: Path to the audio file in storage
            
        Returns:
            True if file exists
        """
        pass
    
    @abstractmethod
    def extract_user_id_from_path(self, file_path: str) -> str:
        """
        Extract user ID from storage file path.
        
        Args:
            file_path: Storage file path
            
        Returns:
            User ID extracted from path
            
        Raises:
            ValueError: If path format is invalid
        """
        pass
