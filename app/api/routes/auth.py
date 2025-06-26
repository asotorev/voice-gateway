"""
Authentication routes for Voice Gateway.
Handles user registration with DynamoDB persistence and optimized dependency injection.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.user import UserRegisterRequest, UserRegisterResponse
from app.core.usecases.register_user import RegisterUserUseCase
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository
from app.core.ports.user_repository import UserRepositoryPort


router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_user_repository() -> UserRepositoryPort:
    """
    Dependency provider for DynamoDB user repository.
    
    Returns repository instance configured for current environment.
    
    Returns:
        UserRepositoryPort: Repository instance for user operations
    """
    return DynamoDBUserRepository()


def get_register_use_case(
    user_repository: UserRepositoryPort = Depends(get_user_repository)
) -> RegisterUserUseCase:
    """
    Dependency provider for register user use case.
    
    Args:
        user_repository: Repository instance from dependency injection
        
    Returns:
        RegisterUserUseCase: Use case configured with repository
    """
    return RegisterUserUseCase(user_repository)


@router.post("/register", response_model=UserRegisterResponse)
async def register(
    request: UserRegisterRequest,
    use_case: RegisterUserUseCase = Depends(get_register_use_case)
):
    """
    Register a new user with DynamoDB persistence.
    
    Args:
        request: User registration data (name, email, password)
        use_case: Register user use case instance
        
    Returns:
        UserRegisterResponse: Created user information
        
    Raises:
        HTTPException: 400 if user already exists or validation fails
        HTTPException: 500 if database operation fails
    """
    try:
        user = await use_case.execute(
            email=request.email,
            name=request.name,
            password=request.password
        )
        return UserRegisterResponse.model_validate(user.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")