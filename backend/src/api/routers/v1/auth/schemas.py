from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    # Web clients: HttpOnly refresh_token cookie (auto-sent), empty body.
    # Mobile / API clients: refresh_token in body.
    # The router enforces that one or the other is present.
    refresh_token: Optional[str] = None
