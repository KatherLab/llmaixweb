# backend/src/schemas/auth.py
from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict  # Include basic user info in token response
    # Present when refresh tokens are issued (login / refresh flows). The
    # frontend stores this alongside the access token and uses it to silently
    # refresh on 401.
    refresh_token: Optional[str] = None


class TokenPayload(BaseModel):
    sub: Optional[int] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None
    everywhere: bool = False
