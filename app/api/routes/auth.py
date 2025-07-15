"""
Authentication routes for Voice Gateway.
Handles user registration with automatic password generation and DynamoDB persistence.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.user import UserRegisterRequest, UserRegisterResponse
from app.core.ports.password_service import PasswordServicePort
from app.core.ports.user_repository import UserRepositoryPort
from app.core.services.password_service import PasswordService
from app.core.usecases.register_user import RegisterUserUseCase
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_user_repository() -> UserRepositoryPort:
    """
    Dependency provider for user repository.
    
    Returns:
        UserRepositoryPort: Repository instance for user operations
    """
    return DynamoDBUserRepository()


def get_password_service() -> PasswordServicePort:
    """
    Dependency provider for password service.
    
    Returns:
        PasswordServicePort: Service instance for password generation
    """
    return PasswordService()


def get_register_use_case(
    user_repository: UserRepositoryPort = Depends(get_user_repository),
    password_service: PasswordServicePort = Depends(get_password_service)
) -> RegisterUserUseCase:
    """
    Dependency provider for register user use case.
    
    Args:
        user_repository: Repository instance from dependency injection
        password_service: Password service instance from dependency injection
        
    Returns:
        RegisterUserUseCase: Use case configured with dependencies
    """
    return RegisterUserUseCase(user_repository, password_service)


@router.post("/register", response_model=UserRegisterResponse)
async def register(
    request: UserRegisterRequest,
    use_case: RegisterUserUseCase = Depends(get_register_use_case)
):
    """
    Register a new user with automatic password generation.
    
    Args:
        request: User registration data (name, email)
        use_case: Register user use case instance
        
    Returns:
        UserRegisterResponse: Created user information with generated password (one-time display)
        
    Raises:
        HTTPException: 400 if user already exists or validation fails
        HTTPException: 500 if password generation or database operation fails
    """
    try:
        user, voice_password = await use_case.execute(
            email=request.email,
            name=request.name
        )
        
        # Create response with temporary password display
        return UserRegisterResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            voice_password=voice_password,
            message="SAVE THESE WORDS - No recovery available"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")