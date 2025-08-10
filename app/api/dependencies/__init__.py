"""
Dependency injection configuration for Voice Gateway.
Central configuration following Clean Architecture principles.
"""
from functools import lru_cache

# Domain ports
from app.core.ports.user_repository import UserRepositoryPort
from app.core.ports.password_service import PasswordServicePort
from app.core.ports.audio_storage import AudioStorageServicePort
from app.core.ports.lambda_invocation import LambdaInvocationPort

# Domain use cases
from app.core.usecases.register_user import RegisterUserUseCase
from app.core.usecases.audio_management import AudioManagementUseCase
from app.core.usecases.voice_authentication import VoiceAuthenticationUseCase

# Infrastructure adapters
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository
from app.core.services.password_service import PasswordService
from app.adapters.services.audio_storage_service import AudioStorageAdapter
from app.adapters.services.lambda_invocation_service import AWSLambdaInvocationService


class DependencyContainer:
    """
    Dependency injection container following Clean Architecture.
    """
    
    def __init__(self):
        """Initialize dependency container."""
        self._user_repository = None
        self._password_service = None
        self._audio_storage_service = None
        self._lambda_invocation_service = None
        self._register_use_case = None
        self._audio_management_use_case = None
        self._voice_authentication_use_case = None
    
    # INFRASTRUCTURE LAYER (Outer layer)
    @property
    def user_repository(self) -> UserRepositoryPort:
        """Get user repository instance (singleton)."""
        if self._user_repository is None:
            self._user_repository = DynamoDBUserRepository()
        return self._user_repository
    
    @property
    def password_service(self) -> PasswordServicePort:
        """Get password service instance (singleton)."""
        if self._password_service is None:
            self._password_service = PasswordService()
        return self._password_service
    
    @property
    def audio_storage_service(self) -> AudioStorageServicePort:
        """Get audio storage service instance (singleton)."""
        if self._audio_storage_service is None:
            self._audio_storage_service = AudioStorageAdapter()
        return self._audio_storage_service
    
    @property
    def lambda_invocation_service(self) -> LambdaInvocationPort:
        """Get Lambda invocation service instance (singleton)."""
        if self._lambda_invocation_service is None:
            self._lambda_invocation_service = AWSLambdaInvocationService()
        return self._lambda_invocation_service
    
    # APPLICATION LAYER (Use cases)
    @property
    def register_use_case(self) -> RegisterUserUseCase:
        """Get register user use case (singleton)."""
        if self._register_use_case is None:
            self._register_use_case = RegisterUserUseCase(
                user_repository=self.user_repository,
                password_service=self.password_service
            )
        return self._register_use_case
    
    @property
    def audio_management_use_case(self) -> AudioManagementUseCase:
        """Get audio management use case (singleton)."""
        if self._audio_management_use_case is None:
            self._audio_management_use_case = AudioManagementUseCase(
                audio_storage=self.audio_storage_service,
                user_repository=self.user_repository
            )
        return self._audio_management_use_case
    
    @property
    def voice_authentication_use_case(self) -> VoiceAuthenticationUseCase:
        """Get voice authentication use case (singleton)."""
        if self._voice_authentication_use_case is None:
            self._voice_authentication_use_case = VoiceAuthenticationUseCase(
                lambda_invocation=self.lambda_invocation_service,
                user_repository=self.user_repository
            )
        return self._voice_authentication_use_case
    
    # TESTING SUPPORT
    def override_user_repository(self, repository: UserRepositoryPort) -> None:
        """Override user repository (for testing)."""
        self._user_repository = repository
        # Reset dependent services
        self._register_use_case = None
        self._audio_management_use_case = None
        self._voice_authentication_use_case = None
    
    def override_audio_storage(self, storage: AudioStorageServicePort) -> None:
        """Override audio storage service (for testing)."""
        self._audio_storage_service = storage
        # Reset dependent services
        self._audio_management_use_case = None
    
    def override_lambda_invocation(self, service: LambdaInvocationPort) -> None:
        """Override Lambda invocation service (for testing)."""
        self._lambda_invocation_service = service
        # Reset dependent services
        self._voice_authentication_use_case = None
    
    def override_password_service(self, service: PasswordServicePort) -> None:
        """Override password service (for testing)."""
        self._password_service = service
        # Reset dependent services
        self._register_use_case = None
        self._audio_management_use_case = None


# GLOBAL CONTAINER INSTANCE
@lru_cache()
def get_dependency_container() -> DependencyContainer:
    """Get global dependency container (singleton)."""
    return DependencyContainer()


# FASTAPI DEPENDENCY FUNCTIONS
def get_user_repository() -> UserRepositoryPort:
    """FastAPI dependency for user repository."""
    return get_dependency_container().user_repository


def get_password_service() -> PasswordServicePort:
    """FastAPI dependency for password service."""
    return get_dependency_container().password_service


def get_audio_storage_service() -> AudioStorageServicePort:
    """FastAPI dependency for audio storage service."""
    return get_dependency_container().audio_storage_service


def get_register_use_case() -> RegisterUserUseCase:
    """FastAPI dependency for register use case."""
    return get_dependency_container().register_use_case


def get_audio_management_use_case() -> AudioManagementUseCase:
    """FastAPI dependency for audio management use case."""
    return get_dependency_container().audio_management_use_case


def get_lambda_invocation_service() -> LambdaInvocationPort:
    """FastAPI dependency for Lambda invocation service."""
    return get_dependency_container().lambda_invocation_service


def get_voice_authentication_use_case() -> VoiceAuthenticationUseCase:
    """FastAPI dependency for voice authentication use case."""
    return get_dependency_container().voice_authentication_use_case



# CONFIGURATION VALIDATION
def validate_dependencies() -> None:
    """
    Validate that all dependencies can be created successfully.
    Call this at application startup.
    """
    try:
        container = get_dependency_container()
        
        # Try to create all services
        user_repo = container.user_repository
        password_svc = container.password_service
        audio_storage = container.audio_storage_service
        
        # Try to create all use cases
        register_uc = container.register_use_case
        audio_mgmt_uc = container.audio_management_use_case
        voice_auth_uc = container.voice_authentication_use_case
        
        
    except Exception as e:
        raise 