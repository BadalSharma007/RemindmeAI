from __future__ import annotations

from pydantic import BaseModel, EmailStr


class ConnectResponse(BaseModel):
    redirect_url: str
    state: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_email: str


class UserRead(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    timezone: str = "UTC"

    model_config = {"from_attributes": True}
