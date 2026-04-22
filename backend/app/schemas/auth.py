from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class ConnectResponse(BaseModel):
    redirect_url: str = Field(..., max_length=2048)
    state: str = Field(..., max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_email: EmailStr


class UserRead(BaseModel):
    id: str
    email: EmailStr
    display_name: str | None = Field(None, max_length=255)
    timezone: str = Field("UTC", max_length=60)

    model_config = {"from_attributes": True}
