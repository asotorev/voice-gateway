"""
Shared test configuration and fixtures for Voice Gateway tests.
"""
import pytest
from unittest.mock import Mock
from app.core.ports.user_repository import UserRepositoryPort
from app.core.ports.password_service import PasswordServicePort
from app.core.models.user import User
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository
from app.core.services.password_service import PasswordService
from app.core.services.unique_password_service import UniquePasswordService
from app.core.usecases.register_user import RegisterUserUseCase

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
            "casa", "verde", "mesa", "libro", "agua",
            "fuego", "tierra", "cielo", "mar", "sol"
        ],
        "entropy_bits": 6.64,
        "total_combinations": 100
    }

# === Global fixtures for real services/repos ===
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