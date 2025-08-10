"""
Dependency Injection Configuration for Voice Authentication Processor.

Provides dependency injection setup for the Clean Architecture implementation,
managing the creation and configuration of all required components for
voice authentication processing.
"""
import os
import logging
from typing import Optional, Dict, Any

# Import from shared layer
from shared.core.ports.audio_processor import AudioProcessorPort
from shared.core.ports.storage_service import StorageServicePort
from shared.core.ports.user_repository import UserRepositoryPort
from shared.core.ports.voice_authentication import VoiceAuthenticationPort
from shared.core.ports.transcription_service import TranscriptionServicePort
from shared.core.usecases.authenticate_voice import AuthenticateVoiceUseCase
from shared.core.services import voice_authentication_service, get_transcription_service
from shared.adapters.audio_processors.resemblyzer_processor import get_audio_processor
from shared.adapters.storage.s3_audio_storage import S3AudioStorageService
from shared.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository
from shared.adapters.voice_authentication.voice_authentication_adapter import VoiceAuthenticationAdapter
from shared.adapters.transcription.openai_transcription_adapter import OpenAITranscriptionAdapter
from shared.infrastructure.aws.aws_config import AWSConfigManager

logger = logging.getLogger(__name__)


class VoiceAuthDependencyContainer:
    """
    Dependency injection container for the voice authentication processor.
    
    Manages the creation and lifecycle of all dependencies needed for
    voice authentication, following Clean Architecture principles.
    """
    
    def __init__(self):
        """Initialize the voice authentication dependency container."""
        self._aws_config_manager: Optional[AWSConfigManager] = None
        self._audio_processor: Optional[AudioProcessorPort] = None
        self._storage_service: Optional[StorageServicePort] = None
        self._user_repository: Optional[UserRepositoryPort] = None
        self._voice_authentication: Optional[VoiceAuthenticationPort] = None
        self._transcription_service: Optional[TranscriptionServicePort] = None
        self._authenticate_voice_use_case: Optional[AuthenticateVoiceUseCase] = None
        
        logger.info("Voice authentication dependency container initialized")
    
    def get_aws_config_manager(self) -> AWSConfigManager:
        """Get AWS configuration manager (singleton)."""
        if self._aws_config_manager is None:
            self._aws_config_manager = AWSConfigManager()
            logger.debug("AWS config manager created")
        return self._aws_config_manager
    
    def get_audio_processor(self) -> AudioProcessorPort:
        """Get audio processor implementation (singleton)."""
        if self._audio_processor is None:
            self._audio_processor = get_audio_processor()
            logger.debug("Audio processor created", extra={
                "processor_type": type(self._audio_processor).__name__
            })
        return self._audio_processor
    
    def get_storage_service(self) -> StorageServicePort:
        """Get storage service implementation (singleton)."""
        if self._storage_service is None:
            self._storage_service = S3AudioStorageService()
            logger.debug("Storage service created")
        return self._storage_service
    
    def get_user_repository(self) -> UserRepositoryPort:
        """Get user repository implementation (singleton)."""
        if self._user_repository is None:
            self._user_repository = DynamoDBUserRepository()
            logger.debug("User repository created")
        return self._user_repository
    
    def get_voice_authentication(self) -> VoiceAuthenticationPort:
        """Get voice authentication service (singleton)."""
        if self._voice_authentication is None:
            self._voice_authentication = VoiceAuthenticationAdapter(voice_authentication_service)
            logger.debug("Voice authentication adapter created")
        return self._voice_authentication
    
    def get_transcription_service(self) -> TranscriptionServicePort:
        """Get transcription service (singleton)."""
        if self._transcription_service is None:
            transcription_service = get_transcription_service()
            self._transcription_service = OpenAITranscriptionAdapter(transcription_service)
            logger.debug("Transcription service adapter created")
        return self._transcription_service
    
    def get_authenticate_voice_use_case(self) -> AuthenticateVoiceUseCase:
        """Get authenticate voice use case (singleton)."""
        if self._authenticate_voice_use_case is None:
            self._authenticate_voice_use_case = AuthenticateVoiceUseCase(
                audio_processor=self.get_audio_processor(),
                storage_service=self.get_storage_service(),
                user_repository=self.get_user_repository(),
                voice_authentication=self.get_voice_authentication()
            )
            logger.debug("Authenticate voice use case created")
        return self._authenticate_voice_use_case
    
    def get_all_dependencies(self) -> Dict[str, Any]:
        """
        Get all dependencies as a dictionary (useful for testing).
        
        Returns:
            Dictionary containing all configured dependencies
        """
        return {
            'aws_config_manager': self.get_aws_config_manager(),
            'audio_processor': self.get_audio_processor(),
            'storage_service': self.get_storage_service(),
            'user_repository': self.get_user_repository(),
            'voice_authentication': self.get_voice_authentication(),
            'transcription_service': self.get_transcription_service(),
            'authenticate_voice_use_case': self.get_authenticate_voice_use_case()
        }
    
    def reset(self):
        """Reset all singletons (useful for testing)."""
        self._aws_config_manager = None
        self._audio_processor = None
        self._storage_service = None
        self._user_repository = None
        self._voice_authentication = None
        self._transcription_service = None
        self._authenticate_voice_use_case = None
        logger.debug("Voice authentication dependency container reset")


# Global dependency container instance
_container = VoiceAuthDependencyContainer()


def get_container() -> VoiceAuthDependencyContainer:
    """Get the global voice authentication dependency container."""
    return _container


def get_aws_config_manager() -> AWSConfigManager:
    """Get AWS configuration manager."""
    return _container.get_aws_config_manager()


def get_audio_processor() -> AudioProcessorPort:
    """Get audio processor implementation."""
    return _container.get_audio_processor()


def get_storage_service() -> StorageServicePort:
    """Get storage service implementation."""
    return _container.get_storage_service()


def get_user_repository() -> UserRepositoryPort:
    """Get user repository implementation."""
    return _container.get_user_repository()


def get_voice_authentication() -> VoiceAuthenticationPort:
    """Get voice authentication service."""
    return _container.get_voice_authentication()


def get_transcription_service() -> TranscriptionServicePort:
    """Get transcription service."""
    return _container.get_transcription_service()


def get_authenticate_voice_use_case() -> AuthenticateVoiceUseCase:
    """Get authenticate voice use case."""
    return _container.get_authenticate_voice_use_case()


def setup_dependencies_for_testing() -> VoiceAuthDependencyContainer:
    """
    Setup dependencies for testing environment.
    
    Returns:
        Fresh dependency container for testing
    """
    test_container = VoiceAuthDependencyContainer()
    return test_container


def configure_dependencies(**overrides) -> VoiceAuthDependencyContainer:
    """
    Configure dependencies with custom implementations.
    
    Args:
        **overrides: Dependency overrides for testing
        
    Returns:
        Configured dependency container
    """
    container = VoiceAuthDependencyContainer()
    
    # Apply overrides
    for dependency_name, implementation in overrides.items():
        if hasattr(container, f'_{dependency_name}'):
            setattr(container, f'_{dependency_name}', implementation)
            logger.debug(f"Dependency override applied: {dependency_name}")
    
    return container
