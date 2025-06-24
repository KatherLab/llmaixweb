import secrets
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Form, Path
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .... import schemas
from .... import models
from ....core.config import settings
from ....core.security import (
    get_password_hash,
    verify_password,
    get_current_user,
    get_admin_user,
    create_access_token,
)
from ....dependencies import get_db

router = APIRouter()


@router.post("/login", response_model=schemas.Token)
def login(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, str(user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user.id, expires_delta=access_token_expires)

    # Return token and user info
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


@router.post("/register", response_model=schemas.UserResponse)
def register(
    *,
    db: Session = Depends(get_db),
    user_in: schemas.UserCreate,
) -> Any:
    """
    Create new user with or without invitation token based on settings.
    """
    # Check if user already exists
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    # Prevent creating admin users via API
    if user_in.role == "admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot create admin user via API!",
        )

    # Check if invitation is required by app settings
    if settings.REQUIRE_INVITATION:
        # Ensure invitation token is provided
        if not user_in.invitation_token:
            raise HTTPException(
                status_code=400,
                detail="Invitation token is required for registration.",
            )

        # Validate invitation token
        invitation = (
            db.query(models.Invitation)
            .filter(
                models.Invitation.token == user_in.invitation_token,
                models.Invitation.is_used.is_(False),
            )
            .first()
        )

        if not invitation:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired invitation token.",
            )

        # Optional: Check if the email matches the invitation (if provided)
        if invitation.email and invitation.email != user_in.email:
            raise HTTPException(
                status_code=400,
                detail="Email does not match the invitation.",
            )

        # Mark the invitation as used
        invitation.is_used = True
        db.add(invitation)

    # Create the user
    user = models.User(
        email=str(user_in.email),
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role if user_in.role else models.UserRole.user.value,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/invite", response_model=schemas.InvitationResponse)
async def invite(
    email: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user),
) -> Any:
    """
    Invite a new user.
    """
    print(f"Received invitation request with email: {email}")  # Debug print

    # Check if invitation already exists for this email
    existing_invitation = (
        db.query(models.Invitation)
        .filter(models.Invitation.email == email, models.Invitation.is_used.is_(False))
        .first()
    )

    if existing_invitation:
        return existing_invitation

    # Check if email is already registered
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists.",
        )

    # Generate a unique token
    token = secrets.token_urlsafe(32)

    invitation = models.Invitation(email=email, token=token, is_used=False)

    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return invitation


@router.get("/invitations", response_model=list[schemas.InvitationResponse])
def list_invitations(
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user),
) -> Any:
    """
    List all invitations (admin only).
    """

    invitations = db.query(models.Invitation).all()
    return invitations


@router.delete(
    "/invitations/{invitation_id}", response_model=schemas.InvitationResponse
)
def delete_invitation(
    *,
    db: Session = Depends(get_db),
    invitation_id: int = Path(...),
    current_user: models.User = Depends(get_admin_user),
) -> Any:
    """
    Delete an invitation (admin only).
    """

    invitation = (
        db.query(models.Invitation)
        .filter(models.Invitation.id == invitation_id)
        .first()
    )
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    db.delete(invitation)
    db.commit()

    return invitation


@router.get("/validate-invitation/{token}", response_model=schemas.InvitationInfo)
def validate_invitation(
    *,
    db: Session = Depends(get_db),
    token: str,
) -> Any:
    """
    Validate an invitation token and return associated email.
    """
    invitation = (
        db.query(models.Invitation)
        .filter(models.Invitation.token == token, models.Invitation.is_used.is_(False))
        .first()
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation token",
        )

    return {"valid": True, "email": invitation.email}


@router.get("/users", response_model=list[schemas.UserResponse])
def list_users(
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user),
) -> Any:
    """
    List all users (admin only).
    """

    users = db.query(models.User).all()
    return users


@router.patch("/users/{user_id}/toggle-status", response_model=schemas.UserResponse)
def toggle_user_status(
    *,
    db: Session = Depends(get_db),
    user_id: int = Path(...),
    current_user: models.User = Depends(get_admin_user),
) -> Any:
    """
    Toggle user active status (admin only).
    """

    # Prevent toggling admin users
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change status of admin users",
        )

    # Toggle the is_active status
    user.is_active = not user.is_active
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.get("/me", response_model=schemas.UserResponse)
def read_current_user(
    current_user: models.User = Depends(get_current_user),
) -> Any:
    """
    Get current user.
    """
    return current_user


@router.post("/reset-password", response_model=schemas.UserResponse)
def reset_password(
    new_password: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Reset password not implemented yet",
    )
