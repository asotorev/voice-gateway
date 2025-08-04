"""
Shared test configuration and fixtures for Voice Gateway tests.
"""
import pytest
import sys
import asyncio
import uuid
from pathlib import Path
from unittest.mock import Mock
from fastapi.testclient import TestClient
from app.main import app

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

# Test helpers and infrastructure imports
from tests.utils.infrastructure_test_helpers import InfrastructureTestHelpers
from tests.utils.mock_helpers import MockHelpers
from app.infrastructure.services.health_checks import health_check_service



# ENVIRONMENT & CONFIGURATION FIXTURES

@pytest.fixture
def test_settings(monkeypatch):
    """Create InfrastructureSettings instance with test configuration."""
    # Configure test environment variables using centralized config
    test_env = MockHelpers.create_test_environment_config()
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    # Create and return InfrastructureSettings instance
    from app.infrastructure.config.infrastructure_settings import InfrastructureSettings
    return InfrastructureSettings()


@pytest.fixture
def infrastructure_helpers():
    """Fixture to provide InfrastructureTestHelpers instance for all tests."""
    return InfrastructureTestHelpers()


# MOCK FIXTURES (for unit tests)

@pytest.fixture
def mock_user_repository() -> Mock:
    """Mock user repository for unit tests."""
    return MockHelpers.create_mock_user_repository()


@pytest.fixture
def mock_password_service() -> Mock:
    """Mock password service for unit tests."""
    return MockHelpers.create_mock_password_service()


@pytest.fixture
def mock_storage_service() -> Mock:
    """Mock storage service for unit tests."""
    return MockHelpers.create_mock_storage_service()


# REAL SERVICE FIXTURES (for integration tests)

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





@pytest.fixture
def health_service():
    """Fixture to provide health check service."""
    return health_check_service


# TEST DATA FIXTURES

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
def test_user_id():
    """Generate test user ID for voice sample tests."""
    return str(uuid.uuid4())


@pytest.fixture
def test_audio_path() -> str:
    return "tests/utils/audio_samples/test_sample.wav"


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



# INFRASTRUCTURE & CLEANUP FIXTURES

@pytest.fixture
def test_files(infrastructure_helpers):
    """Track test files for cleanup across integration tests."""
    files = []
    yield files
    
    # Cleanup after all tests in module
    if files:
        service = infrastructure_helpers.create_real_service()
        
        async def async_cleanup():
            return await MockHelpers.cleanup_test_files(service, files)
        
        cleanup_errors = asyncio.run(async_cleanup())
        
        if cleanup_errors:
            # Use pytest warnings instead of print
            import warnings
            warnings.warn(f"S3 cleanup issues: {cleanup_errors}")



# API TESTING FIXTURES

@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture(scope="module")
def base_url():
    """Base URL for API testing."""
    return "http://localhost:8080/api"
