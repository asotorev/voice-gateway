"""
Dependency Injection Configuration for Audio Embedding Processor.

Provides dependency injection setup for the Clean Architecture implementation,
managing the creation and configuration of all required components including
shared layer services, adapters, and use cases.
"""
import os
import logging
from typing import Optional, Dict, Any

# Import from shared layer
from shared.core.ports.audio_processor import AudioProcessorPort
from shared.core.ports.storage_service import StorageServicePort
from shared.core.ports.user_repository import UserRepositoryPort
from shared.core.usecases.process_voice_sample import ProcessVoiceSampleUseCase
from shared.core.services import (
    audio_quality_validator,
    completion_checker,
    user_status_manager,
    notification_handler
)
from shared.adapters.audio_processors.resemblyzer_processor import get_audio_processor
from shared.adapters.storage.s3_audio_storage import S3AudioStorageService
from shared.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository
from shared.infrastructure.aws.aws_config import AWSConfigManager

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Dependency injection container for the audio embedding processor.
    
    Manages the creation and lifecycle of all dependencies needed by the
    application, following Clean Architecture principles.
    """
    
    def __init__(self):
        """Initialize the dependency container."""
        self._aws_config_manager: Optional[AWSConfigManager] = None
        self._audio_processor: Optional[AudioProcessorPort] = None
        self._storage_service: Optional[StorageServicePort] = None
        self._user_repository: Optional[UserRepositoryPort] = None
        self._process_voice_sample_use_case: Optional[ProcessVoiceSampleUseCase] = None
        
        logger.info("Dependency container initialized")
    
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
    
    def get_process_voice_sample_use_case(self) -> ProcessVoiceSampleUseCase:
        """Get process voice sample use case (singleton)."""
        if self._process_voice_sample_use_case is None:
            audio_processor = self.get_audio_processor()
            storage_service = self.get_storage_service()
            user_repository = self.get_user_repository()
            
            self._process_voice_sample_use_case = ProcessVoiceSampleUseCase(
                audio_processor=audio_processor,
                storage_service=storage_service,
                user_repository=user_repository
            )
            logger.debug("Process voice sample use case created")
        return self._process_voice_sample_use_case
    
    def get_audio_quality_validator(self):
        """Get audio quality validator service."""
        return audio_quality_validator
    
    def get_completion_checker(self):
        """Get completion checker service."""
        return completion_checker
    
    def get_user_status_manager(self):
        """Get user status manager service."""
        return user_status_manager
    
    def get_notification_handler(self):
        """Get notification handler service."""
        return notification_handler
    
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
            'process_voice_sample_use_case': self.get_process_voice_sample_use_case(),
            'audio_quality_validator': self.get_audio_quality_validator(),
            'completion_checker': self.get_completion_checker(),
            'user_status_manager': self.get_user_status_manager(),
            'notification_handler': self.get_notification_handler()
        }
    
    def reset(self):
        """Reset all singletons (useful for testing)."""
        self._aws_config_manager = None
        self._audio_processor = None
        self._storage_service = None
        self._user_repository = None
        self._process_voice_sample_use_case = None
        logger.debug("Dependency container reset")


# Global dependency container instance
_container = DependencyContainer()


def get_container() -> DependencyContainer:
    """Get the global dependency container."""
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


def get_process_voice_sample_use_case() -> ProcessVoiceSampleUseCase:
    """Get process voice sample use case."""
    return _container.get_process_voice_sample_use_case()


def get_audio_quality_validator():
    """Get audio quality validator service."""
    return _container.get_audio_quality_validator()


def get_completion_checker():
    """Get completion checker service."""
    return _container.get_completion_checker()


def get_user_status_manager():
    """Get user status manager service."""
    return _container.get_user_status_manager()


def get_notification_handler():
    """Get notification handler service."""
    return _container.get_notification_handler()


def setup_dependencies_for_testing() -> DependencyContainer:
    """
    Setup dependencies for testing environment.
    
    Returns:
        Fresh dependency container for testing
    """
    test_container = DependencyContainer()
    return test_container


def configure_dependencies(**overrides) -> DependencyContainer:
    """
    Configure dependencies with custom implementations.
    
    Args:
        **overrides: Dependency overrides for testing
        
    Returns:
        Configured dependency container
    """
    container = DependencyContainer()
    
    # Apply overrides
    for dependency_name, implementation in overrides.items():
        if hasattr(container, f'_{dependency_name}'):
            setattr(container, f'_{dependency_name}', implementation)
            logger.debug(f"Dependency override applied: {dependency_name}")
    
    return container
