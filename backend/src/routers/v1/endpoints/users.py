import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Path, status
from sqlalchemy.orm import Session

from .... import models, schemas
from ....core.config import settings
from ....core.security import (
    get_admin_user,
    get_current_user,
    get_password_hash,
    verify_password,
)
from ....dependencies import get_db
from ....schemas import PasswordSet
from ....utils.enums import UserRole

router = APIRouter()


from fastapi import Body

@router.post("/change-password", response_model=schemas.UserResponse)
def change_password(
    password_data: schemas.PasswordChange,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.UserResponse:
    # Verify old password
    if not verify_password(password_data.old_password, str(current_user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect.",
        )
    if password_data.old_password == password_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the old password.",
        )
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    db.refresh(current_user)
    return schemas.UserResponse.model_validate(current_user)


@router.post("/{user_id}/set-password", response_model=schemas.UserResponse)
def admin_set_user_password(
    user_id: int = Path(...),
    password_data: PasswordSet = Body(...),
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> schemas.UserResponse:
    """Set a new password for any user (admin only)."""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user.role == UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password of other admin users",
        )
    user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    db.refresh(user)
    return schemas.UserResponse.model_validate(user)


@router.post("", response_model=schemas.UserResponse)
def create_user(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
) -> schemas.UserResponse:
    # Prevent creating admin users via API
    if user_in.role == UserRole.admin:
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
                detail="Unable to create account. Please check your invitation and try again.",
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
                detail="Unable to create account. Please check your invitation and try again.",
            )

        # Optional: Check if the email matches the invitation (if provided)
        if invitation.email and invitation.email != user_in.email:
            raise HTTPException(
                status_code=400,
                detail="Unable to create account. Please check your invitation and try again.",
            )

        # Check if user already exists (only after invitation checks)
        user = db.query(models.User).filter(models.User.email == user_in.email).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail="Unable to create account. Please check your invitation and try again.",
            )

        # Mark the invitation as used
        invitation.is_used = True
        db.add(invitation)

    else:
        # Open registration mode
        user = db.query(models.User).filter(models.User.email == user_in.email).first()
        if user:
            # Still use a generic error
            raise HTTPException(
                status_code=400,
                detail="Unable to create account. Please check your input and try again.",
            )

    # Create the user
    user = models.User(
        email=str(user_in.email),
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role if user_in.role else UserRole.user,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.UserResponse.model_validate(user)



@router.get("", response_model=list[schemas.UserResponse])
def list_users(
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> list[schemas.UserResponse]:
    """List all users (admin only)."""
    users = db.query(models.User).all()
    return [schemas.UserResponse.model_validate(user) for user in users]


@router.get("/me", response_model=schemas.UserResponse)
def read_current_user(
    current_user: models.User = Depends(get_current_user),
) -> schemas.UserResponse:
    """Get current user."""
    return schemas.UserResponse.model_validate(current_user)


@router.delete("/{user_id}", response_model=schemas.UserResponse)
def delete_user(
    user_id: int = Path(...),
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> schemas.UserResponse:
    """Delete a user (admin only)."""
    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own user account",
        )

    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent deleting admin users
    if user.role == UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin users",
        )

    db.delete(user)
    db.commit()
    return schemas.UserResponse.model_validate(user)


@router.patch("/{user_id}/toggle-status", response_model=schemas.UserResponse)
def toggle_user_status(
    user_id: int = Path(...),
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> schemas.UserResponse:
    """Toggle user active status (admin only)."""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role == UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change status of admin users",
        )

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return schemas.UserResponse.model_validate(user)


@router.post("/invite", response_model=schemas.InvitationResponse)
async def invite(
    email: str = Form(...),
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> schemas.InvitationResponse:
    """Invite a new user."""
    # Check if invitation already exists for this email
    existing_invitation = (
        db.query(models.Invitation)
        .filter(models.Invitation.email == email, models.Invitation.is_used.is_(False))
        .first()
    )
    if existing_invitation:
        return schemas.InvitationResponse.model_validate(existing_invitation)

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
    return schemas.InvitationResponse.model_validate(invitation)


@router.get("/invitations", response_model=list[schemas.InvitationResponse])
def list_invitations(
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> list[schemas.InvitationResponse]:
    """List all invitations (admin only)."""
    invitations = db.query(models.Invitation).all()
    return [
        schemas.InvitationResponse.model_validate(invitation)
        for invitation in invitations
    ]


@router.delete(
    "/invitations/{invitation_id}",
    response_model=schemas.InvitationResponse,
)
def delete_invitation(
    invitation_id: int = Path(...),
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> schemas.InvitationResponse:
    """Delete an invitation (admin only)."""
    invitation = db.get(models.Invitation, invitation_id)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )
    db.delete(invitation)
    db.commit()
    return schemas.InvitationResponse.model_validate(invitation)


@router.get("/validate-invitation/{token}", response_model=schemas.InvitationInfo)
def validate_invitation(
    token: str,
    db: Session = Depends(get_db),
) -> schemas.InvitationInfo:
    """Validate an invitation token and return associated email."""
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
    return schemas.InvitationInfo(valid=True, email=str(invitation.email))


@router.post("/reset-password", response_model=schemas.UserResponse)
def reset_password(
    new_password: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.UserResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Reset password not implemented yet",
    )
