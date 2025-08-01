"""
Shared test configuration and fixtures for Voice Gateway tests.
"""
import pytest
import sys
import asyncio
from pathlib import Path
from unittest.mock import Mock

# Setup Python path once for all tests
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import after path setup
from app.core.ports.user_repository import UserRepositoryPort
from app.core.ports.password_service import PasswordServicePort
from app.core.models.user import User
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository
from app.core.services.password_service import PasswordService
from app.core.services.unique_password_service import UniquePasswordService
from app.core.usecases.register_user import RegisterUserUseCase

# S3/Storage related imports
from tests.fixtures.infrastructure_test_helpers import InfrastructureTestHelpers
from app.infrastructure.services.health_checks import health_check_service


# Mock Fixtures
@pytest.fixture
def mock_user_repository() -> Mock:
    mock_repo = Mock(spec=UserRepositoryPort)
    mock_repo.save.return_value = None
    mock_repo.get_by_id.return_value = None
    mock_repo.get_by_email.return_value = None
    mock_repo.check_password_hash_exists.return_value = False
    return mock_repo


@pytest.fixture
def mock_password_service() -> Mock:
    mock_service = Mock(spec=PasswordServicePort)
    mock_service.generate_password.return_value = "test password"
    mock_service.hash_password.return_value = "hashed_password"
    mock_service.validate_password_format.return_value = True
    return mock_service

# Sample Data Fixtures
@pytest.fixture
def sample_user() -> User:
    return User.create(
        email="test@example.com",
        name="Test User",
        password_hash="hashed_password"
    )


@pytest.fixture
def sample_users_list() -> list[User]:
    return [
        User.create(
            email=f"user{i}@example.com",
            name=f"User {i}",
            password_hash=f"hash_{i}"
        )
        for i in range(1, 6)
    ]


@pytest.fixture
def test_audio_path() -> str:
    return "tests/fixtures/audio_samples/test_sample.wav"


@pytest.fixture
def test_dictionary_data() -> dict:
    return {
        "version": "1.0",
        "language": "es-MX",
        "total_words": 10,
        "words": [
            "academia", "actividad", "alimento", "biblioteca", "computadora",
            "desierto", "escritorio", "hospital", "laboratorio", "medicina"
        ],
        "entropy_bits": 6.64,
        "total_combinations": 90  # 10 * 9 = 90 combinations
    }


# Infrastructure Fixtures
@pytest.fixture
def infrastructure_helpers():
    """Fixture to provide InfrastructureTestHelpers instance for all tests."""
    return InfrastructureTestHelpers()


@pytest.fixture
def test_files(infrastructure_helpers):
    """Track test files for cleanup across integration tests."""
    files = []
    yield files
    
    # Cleanup after all tests in module
    if files:
        service = infrastructure_helpers.create_real_service()
        cleanup_errors = []
        
        async def async_cleanup():
            for file_path in files:
                try:
                    result = await service.delete_file(file_path)
                    if not result:
                        cleanup_errors.append(f"Could not delete: {file_path}")
                except Exception as e:
                    cleanup_errors.append(f"Error deleting {file_path}: {str(e)}")
        
        asyncio.run(async_cleanup())
        
        if cleanup_errors:
            # Use pytest warnings instead of print
            import warnings
            warnings.warn(f"S3 cleanup issues: {cleanup_errors}")


# Storage Mock Fixtures
@pytest.fixture
def mock_storage_service() -> Mock:
    """Mock storage service for unit tests."""
    mock_service = Mock()
    mock_service.generate_upload_url.return_value = {
        'upload_url': 'https://test-bucket.s3.amazonaws.com',
        'file_path': 'test/path.wav',
        'upload_method': 'POST',
        'content_type': 'audio/wav',
        'upload_fields': {},
        'expires_at': '2024-01-01T12:00:00Z',
        'max_file_size_bytes': 10485760
    }
    mock_service.generate_download_url.return_value = 'https://test-bucket.s3.amazonaws.com/download/path.wav'
    mock_service.file_exists.return_value = True
    mock_service.delete_file.return_value = True
    return mock_service


# Environment Fixtures
@pytest.fixture
def test_settings(monkeypatch):
    """Create InfrastructureSettings instance with test configuration."""
    # Configure test environment variables
    test_env = {
        'ENVIRONMENT': 'test',
        'AWS_REGION': 'us-east-1',
        'S3_BUCKET_NAME': 'test-bucket',
        'S3_ENDPOINT_URL': 'http://localhost:9000',
        'DYNAMODB_ENDPOINT_URL': 'http://localhost:8000',
        'USERS_TABLE_NAME': 'voice-gateway-users-test',
        'AUDIO_BASE_URL': 's3://test-bucket/',
        'MAX_AUDIO_FILE_SIZE_MB': '10'
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    # Create and return InfrastructureSettings instance
    from app.infrastructure.config.infrastructure_settings import InfrastructureSettings
    return InfrastructureSettings()


# Health Check Fixtures
@pytest.fixture
def health_service():
    """Fixture to provide health check service."""
    return health_check_service

# Real Services/Repos (Module Scope)
@pytest.fixture(scope="module")
def user_repository():
    return DynamoDBUserRepository()


@pytest.fixture(scope="module")
def password_service():
    return PasswordService()


@pytest.fixture(scope="module")
def unique_password_service(password_service, user_repository):
    return UniquePasswordService(password_service, user_repository)


@pytest.fixture(scope="module")
def register_user_use_case(user_repository, password_service):
    return RegisterUserUseCase(user_repository, password_service)