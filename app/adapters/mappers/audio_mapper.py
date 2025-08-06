"""
Audio response mappers for Voice Gateway.
Maps between domain models and API responses.
"""
from app.schemas.audio import (
    AudioUploadResponse,
    AudioDownloadResponse,
    AudioDeleteResponse,
    AudioStatusResponse
)


class AudioResponseMapper:
    """Maps between domain models and API responses."""
    
    @staticmethod
    def to_upload_response(domain_result) -> AudioUploadResponse:
        """Map domain AudioUploadResponse to API response."""
        return AudioUploadResponse(
            upload_url=domain_result.upload_url,
            upload_fields=domain_result.upload_fields,
            file_path=domain_result.file_path,
            sample_id=domain_result.audio_id,
            sample_number=domain_result.audio_number,
            user_id=domain_result.user_id,
            expires_at=domain_result.expires_at,
            max_file_size_bytes=domain_result.max_file_size_bytes,
            content_type=domain_result.content_type,
            format=domain_result.format,
            upload_method=domain_result.upload_method,
            upload_instruction=domain_result.upload_instruction
        )
    
    @staticmethod
    def to_download_response(domain_result) -> AudioDownloadResponse:
        """Map domain AudioDownloadResponse to API response."""
        return AudioDownloadResponse(
            download_url=domain_result.download_url,
            file_path=domain_result.file_path,
            expiration_minutes=domain_result.expiration_minutes,
            access_method=domain_result.access_method
        )
    
    @staticmethod
    def to_delete_response(domain_result) -> AudioDeleteResponse:
        """Map domain AudioDeleteResponse to API response."""
        return AudioDeleteResponse(
            file_path=domain_result.file_path,
            deleted=domain_result.deleted,
            message=domain_result.message
        )
    
    @staticmethod
    def to_status_response(domain_result) -> AudioStatusResponse:
        """Map domain AudioStatusResponse to API response."""
        # Convert AudioSampleDetail to dict for API response
        sample_details = [
            {
                'key': detail.key,
                'size': detail.size,
                'last_modified': detail.last_modified,
                'etag': detail.etag
            }
            for detail in domain_result.sample_details
        ]
        
        return AudioStatusResponse(
            user_id=domain_result.user_id,
            total_samples=domain_result.total_samples,
            completed_samples=domain_result.completed_samples,
            progress_percentage=domain_result.progress_percentage,
            sample_details=sample_details
        ) 