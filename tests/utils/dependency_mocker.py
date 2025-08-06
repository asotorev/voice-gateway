#!/usr/bin/env python3
"""
Dependency mocker for testing.
Provides utilities for mocking dependencies in tests with a fluent interface.
"""
from app.api.dependencies import get_dependency_container
from app.core.ports.user_repository import UserRepositoryPort
from app.core.ports.password_service import PasswordServicePort
from app.core.ports.audio_storage import AudioStorageServicePort
from app.core.usecases.register_user import RegisterUserUseCase


class DependencyMocker:
    """
    Mocks dependencies for testing by overriding real services.
    Provides a fluent interface for setting up test environments.
    """
    
    def __init__(self):
        self.container = get_dependency_container()
    
    def with_mock_user_repository(self, mock_repo: UserRepositoryPort):
        """Override user repository with mock."""
        self.container.override_user_repository(mock_repo)
        return self
    
    def with_mock_audio_storage(self, mock_storage: AudioStorageServicePort):
        """Override audio storage with mock."""
        self.container.override_audio_storage(mock_storage)
        return self
    
    def with_mock_password_service(self, mock_service: PasswordServicePort):
        """Override password service with mock."""
        self.container.override_password_service(mock_service)
        return self
    
    def get_register_use_case(self) -> RegisterUserUseCase:
        """Get register use case with mocked dependencies."""
        return self.container.register_use_case 