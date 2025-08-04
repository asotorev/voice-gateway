"""
Audio API routes for S3 operations.
Handles audio file upload/download URL generation and file management.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any
from app.core.services.audio_storage_service import AudioStorageService
from app.core.ports.audio_storage_port import AudioStorageError
from app.schemas.audio import (
    UploadUrlRequest,
    UploadUrlResponse,
    DownloadUrlRequest,
    DownloadUrlResponse,
    FileExistsResponse,
    DeleteFileResponse,
    StorageInfoResponse
)

router = APIRouter(prefix="/audio", tags=["Audio"])


def get_storage_service() -> AudioStorageService:
    """Dependency to provide storage service."""
    return AudioStorageService()


@router.post("/upload-url", response_model=UploadUrlResponse)
async def generate_audio_upload_url(
    request: UploadUrlRequest,
    storage_service: AudioStorageService = Depends(get_storage_service)
) -> UploadUrlResponse:
    """
    Generate signed URL for audio file upload to S3.
    
    Returns a presigned POST URL with form fields that the client can use
    to upload audio files directly to S3 with size and type validation.
    
    Args:
        request: Upload URL request with file path, content type, and expiration
        storage_service: Storage service dependency
        
    Returns:
        UploadUrlResponse with upload URL and metadata
        
    Raises:
        HTTPException: 400 if validation fails, 500 for server errors
    """
    try:
        result = await storage_service.generate_audio_upload_url(
            file_path=request.file_path,
            content_type=request.content_type,
            expiration_minutes=request.expiration_minutes
        )
        return UploadUrlResponse(**result)
    except AudioStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/download-url", response_model=DownloadUrlResponse)
async def generate_audio_download_url(
    request: DownloadUrlRequest,
    storage_service: AudioStorageService = Depends(get_storage_service)
) -> DownloadUrlResponse:
    """
    Generate signed URL for audio file download from S3.
    
    Verifies audio file exists before generating download URL to prevent
    generation of URLs for non-existent files.
    
    Args:
        request: Download URL request with file path and expiration
        storage_service: Storage service dependency
        
    Returns:
        DownloadUrlResponse with download URL and metadata
        
    Raises:
        HTTPException: 400 if file doesn't exist, 500 for server errors
    """
    try:
        download_url = await storage_service.generate_audio_download_url(
            file_path=request.file_path,
            expiration_minutes=request.expiration_minutes
        )
        return DownloadUrlResponse(
            download_url=download_url,
            file_path=request.file_path,
            expiration_minutes=request.expiration_minutes,
            access_method="GET"
        )
    except AudioStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/file/{file_path:path}/exists", response_model=FileExistsResponse)
async def check_audio_file_exists(
    file_path: str,
    storage_service: AudioStorageService = Depends(get_storage_service)
) -> FileExistsResponse:
    """
    Check if an audio file exists in S3 storage.
    
    Useful for validation before attempting downloads or to verify
    successful uploads.
    
    Args:
        file_path: Relative path to the audio file (captured from URL path)
        
    Returns:
        FileExistsResponse containing file existence status and metadata
    """
    try:
        exists = await storage_service.audio_file_exists(file_path)
        return FileExistsResponse(
            file_path=file_path,
            exists=exists,
            storage_service="s3"
        )
    except Exception as e:
        # For file existence checks, we don't want to expose internal errors
        # Return false for any error (file doesn't exist or can't be checked)
        return FileExistsResponse(
            file_path=file_path,
            exists=False,
            error="Unable to verify file existence"
        )


@router.delete("/file/{file_path:path}", response_model=DeleteFileResponse)
async def delete_audio_file(
    file_path: str,
    storage_service: AudioStorageService = Depends(get_storage_service)
) -> DeleteFileResponse:
    """
    Delete an audio file from S3 storage.
    
    Performs actual deletion of the audio file. Use with caution as this
    operation cannot be undone.
    
    Args:
        file_path: Relative path to the audio file (captured from URL path)
        
    Returns:
        DeleteFileResponse containing deletion status and metadata
        
    Raises:
        HTTPException: 500 for server errors (404 not raised for idempotent deletes)
    """
    try:
        deleted = await storage_service.delete_audio_file(file_path)
        return DeleteFileResponse(
            file_path=file_path,
            deleted=deleted,
            message="File deleted successfully" if deleted else "File not found (already deleted)"
        )
    except AudioStorageError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/info", response_model=StorageInfoResponse)
async def get_audio_service_info(
    storage_service: AudioStorageService = Depends(get_storage_service)
) -> StorageInfoResponse:
    """
    Get audio service information and configuration.
    
    Provides information about audio storage service configuration,
    limits, capabilities, and supported audio formats.
    
    Returns:
        StorageInfoResponse containing audio service configuration and status
        
    Raises:
        HTTPException: 500 if unable to retrieve service information
    """
    try:
        info = storage_service.get_audio_service_info()
        return StorageInfoResponse(
            api_version="1.0",
            supported_operations=[
                "generate_upload_url",
                "generate_download_url", 
                "check_file_exists",
                "delete_file"
            ],
            storage_service="s3",
            bucket_name=info.get("bucket_name", ""),
            region=info.get("region", ""),
            max_file_size_mb=info.get("max_file_size_mb", 10),
            upload_expiration_minutes=info.get("upload_expiration_minutes", 15),
            download_expiration_minutes=info.get("download_expiration_minutes", 60)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to retrieve storage info: {str(e)}")