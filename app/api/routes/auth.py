from fastapi import APIRouter, Depends, HTTPException

from app.schemas.user import UserRegisterRequest, UserRegisterResponse
from app.core.usecases.register_user import RegisterUserUseCase
from app.adapters.repositories.mock_user_repository import MockUserRepository

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_user_repository() -> MockUserRepository:
    return MockUserRepository()


def get_register_use_case(
    user_repository: MockUserRepository = Depends(get_user_repository),
) -> RegisterUserUseCase:
    return RegisterUserUseCase(user_repository)


@router.post("/register", response_model=UserRegisterResponse)
async def register(
    request: UserRegisterRequest,
    use_case: RegisterUserUseCase = Depends(get_register_use_case)
):
    try:
        user = await use_case.execute(
            email=request.email,
            name=request.name,
            password=request.password
        )
        return UserRegisterResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) 