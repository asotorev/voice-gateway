from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)


class UserRegisterResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    created_at: datetime 