"""
Storage service port for Voice Gateway.
Defines interface for audio file storage operations with signed URLs.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class StorageServicePort(ABC):
    """
    Abstract interface for storage operations.
    
    Focused on core audio storage operations needed for voice authentication:
    secure upload/download with signed URLs and basic file operations.
    """
    
    @abstractmethod
    async def generate_upload_url(
        self,
        file_path: str,
        content_type: str = "audio/wav",
        expiration_minutes: int = 15
    ) -> Dict[str, Any]:
        """
        Generate signed URL for file upload.
        
        Args:
            file_path: Relative path where file will be stored (e.g., 'user123/sample1.wav')
            content_type: MIME type of the file being uploaded
            expiration_minutes: URL expiration time in minutes
            
        Returns:
            Dict containing:
            - upload_url: Signed URL for PUT request
            - file_path: Relative path for future reference
            - expires_at: ISO timestamp when URL expires
            - upload_headers: Required headers for upload request
            
        Raises:
            StorageError: If URL generation fails
        """
        pass
    
    @abstractmethod
    async def generate_download_url(
        self,
        file_path: str,
        expiration_minutes: int = 60
    ) -> str:
        """
        Generate signed URL for file download.
        
        Args:
            file_path: Relative path to the file
            expiration_minutes: URL expiration time in minutes
            
        Returns:
            str: Signed URL for GET request
            
        Raises:
            StorageError: If file doesn't exist or URL generation fails
        """
        pass
    
    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """
        Check if file exists in storage.
        
        Args:
            file_path: Relative path to check
            
        Returns:
            bool: True if file exists, False otherwise
        """
        pass


class StorageError(Exception):
    """Exception raised for storage operation errors."""
    
    def __init__(self, message: str, operation: str = None, file_path: str = None):
        """
        Initialize storage error.
        
        Args:
            message: Error description
            operation: Storage operation that failed (upload, download, delete, etc.)
            file_path: File path involved in the operation
        """
        super().__init__(message)
        self.operation = operation
        self.file_path = file_path
        
    def __str__(self):
        parts = [super().__str__()]
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        if self.file_path:
            parts.append(f"File: {self.file_path}")
        return " | ".join(parts)