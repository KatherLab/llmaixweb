import time
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from .... import models, schemas
from ....core.config import settings
from ....core.security import create_access_token, verify_password
from ....dependencies import get_db

router = APIRouter()

# Shared limiter instance (injected from app state by FastAPI)
limiter = Limiter(key_func=get_remote_address)


@router.get("/settings")
def get_settings():
    return {
        "require_invitation": settings.REQUIRE_INVITATION,
        "mistral_ocr_enabled": settings.MISTRAL_OCR_ENABLED,
        "mistral_api_base": settings.MISTRAL_API_BASE,
        "vision_ocr_enabled": settings.VISION_OCR_ENABLED,
        "vision_ocr_api_base": settings.VISION_OCR_API_BASE,
        "vision_ocr_model": settings.VISION_OCR_MODEL,
        "vision_ocr_prompt": settings.VISION_OCR_PROMPT,
        "mistral_ocr_display_name": settings.MISTRAL_OCR_DISPLAY_NAME,
        "mistral_ocr_display_subtitle": settings.MISTRAL_OCR_DISPLAY_SUBTITLE,
        "vision_ocr_display_name": settings.VISION_OCR_DISPLAY_NAME,
        "vision_ocr_display_subtitle": settings.VISION_OCR_DISPLAY_SUBTITLE,
    }


@router.post("/login", response_model=schemas.Token)
@router.post("/api/v1/login", response_model=schemas.Token)
@limiter.limit(None if settings.DISABLE_RATE_LIMIT else "10/minute")
def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> schemas.Token:
    """OAuth2 compatible token login, get an access token for future requests."""
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(
        form_data.password, str(user.hashed_password)
    ):  #
        time.sleep(0.5)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        time.sleep(0.5)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user"
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user.id,
        expires_delta=access_token_expires,
        token_version=user.token_version,
    )
    # Return token and user info
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    )
