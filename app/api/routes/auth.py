"""
Authentication routes for Voice Gateway.
Handles user registration and authentication endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.user import UserRegisterRequest, UserRegisterResponse
from app.core.usecases.register_user import RegisterUserUseCase
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_user_repository() -> DynamoDBUserRepository:
    """
    Dependency provider for DynamoDB user repository.
    
    Returns:
        DynamoDBUserRepository: Repository instance for user operations
    """
    return DynamoDBUserRepository()


def get_register_use_case(
    user_repository: DynamoDBUserRepository = Depends(get_user_repository)
) -> RegisterUserUseCase:
    """
    Dependency provider for register user use case.
    
    Args:
        user_repository: DynamoDB repository instance
        
    Returns:
        RegisterUserUseCase: Use case for user registration
    """
    return RegisterUserUseCase(user_repository)


@router.post("/register", response_model=UserRegisterResponse)
async def register(
    request: UserRegisterRequest,
    use_case: RegisterUserUseCase = Depends(get_register_use_case)
):
    """
    Register a new user.
    
    Args:
        request: User registration data (name, email, password)
        use_case: Register user use case instance
        
    Returns:
        UserRegisterResponse: Created user information
        
    Raises:
        HTTPException: 400 if user already exists or validation fails
    """
    try:
        user = await use_case.execute(
            email=request.email,
            name=request.name,
            password=request.password
        )
        return UserRegisterResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
