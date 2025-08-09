"""
Audio Management Use Case for Voice Gateway.
Orchestrates audio operations with business logic and validation.
"""
import uuid
from typing import List
from app.core.models import (
    AudioUploadRequest, 
    AudioUploadResponse, 
    AudioStatusResponse,
    AudioDownloadResponse,
    AudioDeleteResponse,
    AudioFormat,
    AudioUploadData,
    AudioSetupProgress,
    AudioSampleRequirements,
    AudioSampleDetail
)
from app.core.ports.audio_storage import AudioStorageServicePort
from app.core.ports.user_repository import UserRepositoryPort
from app.core.services.audio_constraints import AudioConstraints


class AudioManagementUseCase:
    """
    Use case for managing audio operations.
    
    Contains ALL business logic, validation, and orchestration.
    Delegates ONLY technical operations to adapters.
    """
    
    def __init__(
        self, 
        audio_storage: AudioStorageServicePort,
        user_repository: UserRepositoryPort
    ):
        """
        Initialize audio management use case.
        
        Args:
            audio_storage: Storage adapter for technical operations
            user_repository: User repository for data operations
        """
        self.audio_storage = audio_storage
        self.user_repository = user_repository

    # BUSINESS VALIDATION METHODS
    
    def _validate_sample_number(self, sample_number: int) -> bool:
        """
        BUSINESS RULE: Only samples 1, 2, 3 are allowed.
        
        Args:
            sample_number: Sample number to validate
            
        Returns:
            True if valid sample number
        """
        return sample_number in [1, 2, 3]
    
    def _validate_user_permissions(self, user_id: str, file_path: str) -> bool:
        """
        BUSINESS RULE: Users can only access their own files.
        
        Args:
            user_id: User identifier
            file_path: File path to check
            
        Returns:
            True if user can access file
        """
        return file_path.startswith(f"{user_id}/")
    
    def _validate_expiration_minutes(self, minutes: int, min_val: int, max_val: int) -> None:
        """
        BUSINESS RULE: Validate expiration time limits.
        
        Args:
            minutes: Expiration in minutes
            min_val: Minimum allowed
            max_val: Maximum allowed
            
        Raises:
            ValueError: If expiration is invalid
        """
        if not isinstance(minutes, int) or minutes < min_val or minutes > max_val:
            raise ValueError(f"Expiration must be between {min_val} and {max_val} minutes")
    
    def _validate_audio_format(self, format_value: str) -> AudioFormat:
        """
        BUSINESS RULE: Only specific audio formats are allowed.
        
        Args:
            format_value: Format string to validate
            
        Returns:
            AudioFormat enum
            
        Raises:
            ValueError: If format is invalid
        """
        try:
            return AudioFormat(format_value.lower())
        except ValueError:
            supported_formats = ", ".join([f.value for f in AudioFormat])
            raise ValueError(f"Invalid audio format: {format_value}. Supported: {supported_formats}")

    # DOMAIN LOGIC METHODS
    
    def _generate_audio_path(self, user_id: str, audio_id: str, format: AudioFormat) -> str:
        """
        DOMAIN LOGIC: Generate file path following naming convention.
        
        Args:
            user_id: User identifier
            audio_id: Audio identifier  
            format: Audio format
            
        Returns:
            File path: {user_id}/{audio_id}.{format}
        """
        return f"{user_id.strip()}/{audio_id.strip()}.{format.value}"
    
    def _get_content_type_for_format(self, format: AudioFormat) -> str:
        """
        DOMAIN KNOWLEDGE: Map audio format to MIME type.
        
        Args:
            format: Audio format enum
            
        Returns:
            MIME content type
        """
        content_types = {
            AudioFormat.WAV: "audio/wav",
            AudioFormat.MP3: "audio/mpeg", 
            AudioFormat.M4A: "audio/mp4"
        }
        
        return content_types[format]
    
    def _calculate_setup_progress(self, samples_uploaded: int) -> AudioSetupProgress:
        """
        BUSINESS LOGIC: Calculate voice setup progress.
        
        Args:
            samples_uploaded: Number of samples uploaded
            
        Returns:
            AudioSetupProgress with progress calculations
        """
        samples_required = AudioConstraints.REQUIRED_AUDIO_SAMPLES_COUNT
        setup_complete = samples_uploaded >= samples_required
        progress_percentage = (samples_uploaded / samples_required) * 100
        next_sample_number = samples_uploaded + 1 if not setup_complete else None
        
        return AudioSetupProgress(
            samples_uploaded=samples_uploaded,
            samples_required=samples_required,
            setup_complete=setup_complete,
            progress_percentage=progress_percentage,
            next_sample_number=next_sample_number
        )

    # PUBLIC USE CASE METHODS
    
    async def generate_audio_upload_url(
        self, 
        user_id: str, 
        sample_number: int, 
        format: str, 
        expiration_minutes: int = 15
    ) -> AudioUploadResponse:
        """
        Generate upload URL for voice sample with business validation.
        
        Args:
            user_id: User identifier
            sample_number: Sample number (1, 2, or 3)
            format: Audio format string
            expiration_minutes: URL expiration time
            
        Returns:
            AudioUploadResponse with upload information
            
        Raises:
            ValueError: If validation fails
        """
        # BUSINESS VALIDATION
        if not user_id or not user_id.strip():
            raise ValueError("User ID cannot be empty")
        
        if not self._validate_sample_number(sample_number):
            raise ValueError(f"Invalid sample number: {sample_number}. Must be 1, 2, or 3")
        
        self._validate_expiration_minutes(expiration_minutes, 1, 60)
        audio_format = self._validate_audio_format(format)
        
        # VERIFY USER EXISTS (business rule)
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # DOMAIN LOGIC
        audio_id = str(uuid.uuid4())
        file_path = self._generate_audio_path(user_id, audio_id, audio_format)
        content_type = self._get_content_type_for_format(audio_format)
        max_file_size = AudioConstraints.get_max_audio_file_size_bytes()
        
        # DELEGATE to infrastructure
        upload_data: AudioUploadData = await self.audio_storage.generate_presigned_upload_url(
            file_path=file_path,
            content_type=content_type,
            expiration_minutes=expiration_minutes,
            max_file_size_bytes=max_file_size
        )
        
        # RETURN DOMAIN RESULT
        return AudioUploadResponse(
            upload_url=upload_data.upload_url,
            upload_fields=upload_data.upload_fields,
            file_path=upload_data.file_path,
            audio_id=audio_id,
            audio_number=sample_number,
            user_id=user_id,
            expires_at=upload_data.expires_at,
            max_file_size_bytes=upload_data.max_file_size_bytes or 0,
            content_type=upload_data.content_type,
            format=audio_format.value,
            upload_method=upload_data.upload_method,
            upload_instruction="Mi nombre es [YOUR_NAME] y mi contraseña de voz es [YOUR_PASSWORD]"
        )
    
    async def get_user_audio_status(self, user_id: str) -> AudioStatusResponse:
        """
        Get user voice setup status with business calculations.
        
        Args:
            user_id: User identifier
            
        Returns:
            AudioStatusResponse with setup status and file details
            
        Raises:
            ValueError: If validation fails
        """
        # BUSINESS VALIDATION
        if not user_id or not user_id.strip():
            raise ValueError("User ID cannot be empty")
        
        # VERIFY USER EXISTS
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # DELEGATE to infrastructure
        files = await self.audio_storage.list_files_by_prefix(f"{user_id}/")
        
        # BUSINESS LOGIC
        completed_count = len(files)
        progress_data = self._calculate_setup_progress(completed_count)
        
        sample_details = [
            AudioSampleDetail(
                key=file.key,
                size=file.size,
                last_modified=file.last_modified,
                etag=file.etag
            )
            for file in files
        ]
        
        # RETURN DOMAIN RESULT
        return AudioStatusResponse(
            user_id=user_id,
            total_samples=progress_data.samples_required,
            completed_samples=completed_count,
            progress_percentage=progress_data.progress_percentage,
            sample_details=sample_details
        )
    
    async def generate_audio_download_url(
        self, 
        user_id: str, 
        file_path: str, 
        expiration_minutes: int = 60
    ) -> AudioDownloadResponse:
        """
        Generate download URL for audio file with authorization.
        
        Args:
            user_id: User identifier
            file_path: File path to download
            expiration_minutes: URL expiration time
            
        Returns:
            AudioDownloadResponse with download information
            
        Raises:
            ValueError: If validation fails
        """
        # BUSINESS VALIDATION
        if not user_id or not user_id.strip():
            raise ValueError("User ID cannot be empty")
        
        if not file_path or not file_path.strip():
            raise ValueError("File path cannot be empty")
        
        self._validate_expiration_minutes(expiration_minutes, 1, 1440)  # 24 hours max
        
        # VERIFY USER EXISTS
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # AUTHORIZATION (business rule)
        if not self._validate_user_permissions(user_id, file_path):
            raise ValueError("Access denied: Cannot access other user's files")
        
        # VERIFY FILE EXISTS
        file_exists = await self.audio_storage.audio_file_exists(file_path)
        if not file_exists:
            raise ValueError(f"File not found: {file_path}")
        
        # DELEGATE to infrastructure
        download_url = await self.audio_storage.generate_presigned_download_url(
            file_path, expiration_minutes
        )
        
        # RETURN DOMAIN RESULT
        return AudioDownloadResponse(
            download_url=download_url,
            file_path=file_path,
            expiration_minutes=expiration_minutes,
            access_method="GET"
        )
    
    async def delete_audio_file(self, user_id: str, file_path: str) -> AudioDeleteResponse:
        """
        Delete audio file with authorization and business validation.
        
        Also removes corresponding voice embedding from user record if file was deleted.
        
        Args:
            user_id: User identifier
            file_path: File path to delete
            
        Returns:
            AudioDeleteResponse with deletion status and embedding update info
            
        Raises:
            ValueError: If validation fails
        """
        # BUSINESS VALIDATION
        if not user_id or not user_id.strip():
            raise ValueError("User ID cannot be empty")
        
        if not file_path or not file_path.strip():
            raise ValueError("File path cannot be empty")
        
        # VERIFY USER EXISTS
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # AUTHORIZATION (business rule)
        if not self._validate_user_permissions(user_id, file_path):
            raise ValueError("Access denied: Cannot access other user's files")
        
        # DELEGATE to infrastructure - delete file from S3
        deleted = await self.audio_storage.delete_audio_file(file_path)
        
        # BUSINESS LOGIC: Update embeddings if file was deleted
        embedding_removed = False
        if deleted and hasattr(user, 'voice_embeddings') and user.voice_embeddings:
            # Find and remove embedding that corresponds to this file
            original_count = len(user.voice_embeddings)
            user.voice_embeddings = [
                emb for emb in user.voice_embeddings 
                if emb.get('audio_metadata', {}).get('file_name', '') not in file_path
            ]
            
            # If embedding was removed, update user record
            if len(user.voice_embeddings) < original_count:
                embedding_removed = True
                await self.user_repository.save(user)
        
        # RETURN DOMAIN RESULT
        message = "File deleted successfully"
        if embedding_removed:
            message += " and corresponding voice embedding removed"
        
        return AudioDeleteResponse(
            file_path=file_path,
            deleted=deleted,
            message=message,
            embedding_removed=embedding_removed,
            remaining_embeddings=len(user.voice_embeddings) if hasattr(user, 'voice_embeddings') else 0
        )
    
    async def complete_voice_setup(self, user_id: str) -> bool:
        """
        Complete voice setup process with business validation.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if setup completed successfully
            
        Raises:
            ValueError: If validation fails
        """
        # CHECK setup status
        status = await self.get_user_audio_status(user_id)
        
        # BUSINESS RULE: Must have required samples
        if not status.setup_complete:
            raise ValueError(f"Voice setup incomplete: {status.completed_samples}/{status.total_samples} samples")
        
        # UPDATE user in repository (business logic)
        user = await self.user_repository.get_by_id(user_id)
        user.voice_setup_complete = True
        await self.user_repository.save(user)
        
        return True

    # DOMAIN INFORMATION METHODS
    
    def get_voice_sample_requirements(self) -> AudioSampleRequirements:
        """
        Get voice sample business requirements.
        
        Returns:
            AudioSampleRequirements with business requirements
        """
        return AudioSampleRequirements(
            required_samples=AudioConstraints.REQUIRED_AUDIO_SAMPLES_COUNT,
            supported_formats=[f.value for f in AudioFormat],
            max_file_size_mb=AudioConstraints.MAX_AUDIO_FILE_SIZE_MB,
            min_duration_seconds=AudioConstraints.MIN_DURATION_SECONDS,
            max_duration_seconds=AudioConstraints.MAX_DURATION_SECONDS,
            sample_instruction_template="Mi nombre es {name} y mi contraseña de voz es {password}",
            validation_required=True,
            embedding_generation=True
        )
    
    def get_supported_audio_formats(self) -> List[AudioFormat]:
        """
        Get supported audio formats (domain knowledge).
        
        Returns:
            List of AudioFormat enum values
        """
        return list(AudioFormat) 