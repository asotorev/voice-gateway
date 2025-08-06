"""
Audio routes for Voice Gateway API.
Handles audio upload, download, and management operations.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import get_audio_management_use_case, get_audio_storage_service
from app.core.models import AudioServiceInfo
from app.core.usecases.audio_management import AudioManagementUseCase
from app.core.ports.audio_storage import AudioStorageServicePort
from app.adapters.mappers.audio_mapper import AudioResponseMapper
from app.schemas.audio import (
    AudioUploadRequest,
    AudioUploadResponse,
    AudioDownloadRequest,
    AudioDownloadResponse,
    AudioExistsResponse,
    AudioInfoResponse,
    AudioStatusResponse,
    AudioDeleteResponse
)

router = APIRouter(prefix="/audio", tags=["Audio"])


@router.post("/upload", response_model=AudioUploadResponse)
async def generate_audio_upload_url(
    request: AudioUploadRequest,
    audio_management: AudioManagementUseCase = Depends(get_audio_management_use_case)
) -> AudioUploadResponse:
    """
    Generate presigned URL for audio file upload.
    
    Creates upload URL with business validation and user authorization.
    """
    try:
        # Execute use case
        domain_result = await audio_management.generate_audio_upload_url(
            user_id=request.user_id,
            sample_number=request.sample_number,
            format=request.format,
            expiration_minutes=request.expiration_minutes
        )
        
        # Map to API response
        return AudioResponseMapper.to_upload_response(domain_result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/download-url", response_model=AudioDownloadResponse)
async def generate_audio_download_url(
    request: AudioDownloadRequest,
    audio_management: AudioManagementUseCase = Depends(get_audio_management_use_case)
) -> AudioDownloadResponse:
    """
    Generate presigned URL for audio file download.
    
    Creates download URL with user authorization and file validation.
    """
    try:
        # Execute use case
        domain_result = await audio_management.generate_audio_download_url(
            user_id=request.user_id,
            file_path=request.file_path,
            expiration_minutes=request.expiration_minutes
        )
        
        # Map to API response
        return AudioResponseMapper.to_download_response(domain_result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/file/{file_path:path}/exists", response_model=AudioExistsResponse)
async def check_audio_file_exists(
    file_path: str,
    audio_storage: AudioStorageServicePort = Depends(get_audio_storage_service)
) -> AudioExistsResponse:
    """
    Check if audio file exists in storage.
    """
    try:
        # Delegate directly to storage service (technical operation)
        exists = await audio_storage.audio_file_exists(file_path)

        return AudioExistsResponse(
            file_path=file_path,
            exists=exists,
            storage_service="s3"
        )

    except Exception as e:
        # Fallback response in case of unexpected errors
        return AudioExistsResponse(
            file_path=file_path,
            exists=False,
            storage_service="s3",
            error="Unable to verify file existence"
        )


@router.delete("/file/{file_path:path}", response_model=AudioDeleteResponse)
async def delete_audio_file(
    file_path: str,
    user_id: str,
    audio_management: AudioManagementUseCase = Depends(get_audio_management_use_case)
) -> AudioDeleteResponse:
    """
    Delete audio file with user authorization.
    """
    try:
        # Execute use case
        domain_result = await audio_management.delete_audio_file(user_id, file_path)
        
        # Map to API response
        return AudioResponseMapper.to_delete_response(domain_result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/user/{user_id}/setup-status", response_model=AudioStatusResponse)
async def get_user_audio_setup_status(
    user_id: str,
    audio_management: AudioManagementUseCase = Depends(get_audio_management_use_case)
) -> AudioStatusResponse:
    """
    Get user voice setup status and progress.
    """
    try:
        # Execute use case
        domain_result = await audio_management.get_user_audio_status(user_id)
        
        # Map to API response
        return AudioResponseMapper.to_status_response(domain_result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/info", response_model=AudioInfoResponse)
async def get_audio_storage_info(
    audio_storage: AudioStorageServicePort = Depends(get_audio_storage_service)
) -> AudioInfoResponse:
    """
    Get audio storage service information.
    """
    try:
        # Delegate directly to storage service (technical operation)
        service_info: AudioServiceInfo = audio_storage.get_audio_service_info()

        return AudioInfoResponse(
            service_type=service_info.service_type,
            bucket_name=service_info.bucket_name,
            region=service_info.region,
            use_local_s3=service_info.use_local_s3,
            endpoint_url=service_info.endpoint_url,
            max_file_size_mb=service_info.max_file_size_mb,
            allowed_formats=service_info.allowed_formats,
            upload_expiration_default=service_info.upload_expiration_default,
            download_expiration_default=service_info.download_expiration_default,
            api_version="1.0",
            supported_operations=[
                "upload", "download", "delete", "exists",
                "setup_status", "info"
            ],
            voice_sample_support=service_info.voice_sample_support,
            individual_upload_support=service_info.individual_upload_support
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")