from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict  # Include basic user info in token response


class TokenPayload(BaseModel):
    sub: Optional[int] = None
