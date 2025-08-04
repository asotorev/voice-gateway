"""
Audio storage service port for Voice Gateway.
Defines interface for audio file storage operations with signed URLs.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class AudioStorageServicePort(ABC):
    """
    Abstract interface for audio storage operations.
    
    Focused on core audio storage operations needed for voice authentication:
    secure upload/download with signed URLs and basic file operations.
    """
    
    @abstractmethod
    async def generate_audio_upload_url(
        self,
        file_path: str,
        content_type: str = "audio/wav",
        expiration_minutes: int = 15
    ) -> Dict[str, Any]:
        """
        Generate signed URL for audio file upload.
        
        Args:
            file_path: Relative path where audio file will be stored (e.g., 'user123/sample1.wav')
            content_type: MIME type of the audio file being uploaded
            expiration_minutes: URL expiration time in minutes
            
        Returns:
            Dict containing:
            - upload_url: Signed URL for POST request
            - file_path: Relative path for future reference
            - expires_at: ISO timestamp when URL expires
            - upload_fields: Required form fields for upload request
            
        Raises:
            AudioStorageError: If URL generation fails
        """
        pass
    
    @abstractmethod
    async def generate_audio_download_url(
        self,
        file_path: str,
        expiration_minutes: int = 60
    ) -> str:
        """
        Generate signed URL for audio file download.
        
        Args:
            file_path: Relative path to the audio file
            expiration_minutes: URL expiration time in minutes
            
        Returns:
            str: Signed URL for GET request
            
        Raises:
            AudioStorageError: If file doesn't exist or URL generation fails
        """
        pass
    
    @abstractmethod
    async def audio_file_exists(self, file_path: str) -> bool:
        """
        Check if audio file exists in storage.
        
        Args:
            file_path: Relative path to check
            
        Returns:
            bool: True if audio file exists, False otherwise
        """
        pass

    @abstractmethod
    async def delete_audio_file(self, file_path: str) -> bool:
        """
        Delete an audio file from storage.
        
        Args:
            file_path: Relative path to the audio file to delete
        
        Returns:
            bool: True if audio file was deleted, False if not found
        
        Raises:
            AudioStorageError: If deletion fails
        """
        pass

    @abstractmethod
    def get_audio_service_info(self) -> Dict[str, Any]:
        """
        Get audio storage service information and configuration.
        
        Returns:
            Dict with audio service configuration and status
        """
        pass


class AudioStorageError(Exception):
    """Exception raised for audio storage operation errors."""
    
    def __init__(self, message: str, operation: str = None, file_path: str = None):
        """
        Initialize audio storage error.
        
        Args:
            message: Error description
            operation: Audio storage operation that failed (upload, download, delete, etc.)
            file_path: Audio file path involved in the operation
        """
        super().__init__(message)
        self.operation = operation
        self.file_path = file_path
        
    def __str__(self):
        parts = [super().__str__()]
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        if self.file_path:
            parts.append(f"Audio File: {self.file_path}")
        return " | ".join(parts)