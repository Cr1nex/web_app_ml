from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from models.token import TokenPair


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str
    email: EmailStr


class RegistrationResponse(BaseModel):
    user: UserOut
    tokens: TokenPair


class LoginResponse(BaseModel):
    user: UserOut
    tokens: TokenPair
