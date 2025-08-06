"""
Audio storage port for Voice Gateway.
Defines the interface for audio storage operations.
"""
from abc import ABC, abstractmethod
from typing import List

from app.core.models import (
    AudioStorageError,
    AudioUploadData,
    AudioServiceInfo,
    AudioFileInfo
)


class AudioStorageServicePort(ABC):
    """
    Port for audio storage operations.
    Defines the contract for audio storage implementations.
    """
    
    @abstractmethod
    async def generate_presigned_upload_url(
        self, 
        file_path: str, 
        content_type: str, 
        expiration_minutes: int = 15,
        max_file_size_bytes: int = None
    ) -> AudioUploadData:
        """
        Generate presigned URL for file upload.
        
        Args:
            file_path: Path where file will be stored
            content_type: MIME type of the file
            expiration_minutes: URL expiration time
            max_file_size_bytes: Maximum file size allowed
            
        Returns:
            AudioUploadData with upload URL and metadata
        """
        pass
    
    @abstractmethod
    async def generate_presigned_download_url(
        self, 
        file_path: str, 
        expiration_minutes: int = 60
    ) -> str:
        """
        Generate presigned URL for file download.
        
        Args:
            file_path: Path of the file to download
            expiration_minutes: URL expiration time
            
        Returns:
            Presigned download URL
        """
        pass
    
    @abstractmethod
    async def delete_audio_file(self, file_path: str) -> bool:
        """
        Delete audio file from storage.
        
        Args:
            file_path: Path of the file to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_files_by_prefix(self, prefix: str) -> List[AudioFileInfo]:
        """
        List files with given prefix.
        
        Args:
            prefix: File path prefix to search
            
        Returns:
            List of AudioFileInfo objects
        """
        pass
    
    @abstractmethod
    async def audio_file_exists(self, file_path: str) -> bool:
        """
        Check if audio file exists in storage.
        
        Args:
            file_path: Path of the file to check
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_audio_service_info(self) -> AudioServiceInfo:
        """
        Get audio storage service information.
        
        Returns:
            AudioServiceInfo with service configuration and capabilities
        """
        pass