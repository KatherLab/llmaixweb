import datetime
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import PyJWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..dependencies import get_db
from ..models.user import User
from ..utils.enums import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


def any_admin_exists(db: Session) -> bool:
    return db.query(User).filter(User.role == UserRole.admin).count() > 0


def create_access_token(
    subject: str | Any, expires_delta: datetime.timedelta | None = None
) -> str:
    if expires_delta:
        expire = datetime.datetime.now(datetime.UTC) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Convert plain password to bytes if it's not already
    if isinstance(plain_password, str):
        plain_password: bytes = plain_password.encode("utf-8")

    # Convert hashed password to bytes if it's not already
    if isinstance(hashed_password, str):
        hashed_password: bytes = hashed_password.encode("utf-8")

    try:
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    # Convert password to bytes if it's not already
    if isinstance(password, str):
        password: bytes = password.encode("utf-8")

    # Generate a salt and hash the password
    salt = bcrypt.gensalt(rounds=12)  # Higher rounds = more secure but slower
    hashed = bcrypt.hashpw(password, salt)

    # Return the hash as a string
    return hashed.decode("utf-8")


async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception

    user = db.execute(select(User).where(User.id == int(user_id))).scalars().one()
    if user is None:
        raise credentials_exception
    return user


# Add this function to protect admin-only endpoints
async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to check if the current user is an admin.

    Usage:
        @router.get("/admin-only")
        def admin_endpoint(admin: User = Depends(get_admin_user)):
            return {"message": "Hello Admin!"}
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required.",
        )
    return current_user
