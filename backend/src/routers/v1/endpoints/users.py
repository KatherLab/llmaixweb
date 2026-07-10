# backend/src/routers/v1/endpoints/users.py
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Form,
    HTTPException,
    Path,
    Query,
    Request,
    status,
)
from sqlalchemy.orm import Session

from .... import models, schemas
from ....core.config import settings
from ....core.rate_limit import limiter
from ....core.security import (
    _hash_token,
    get_admin_user,
    get_current_user,
    get_password_hash,
    verify_password,
)
from ....dependencies import get_db, remove_file
from ....schemas import PasswordSet
from ....utils.audit import record_audit
from ....utils.email_service import send_invitation_email, send_password_reset_email
from ....utils.enums import AuditAction, AuditOutcome, UserRole
from ....utils.password_policy import validate_password

logger = logging.getLogger(__name__)

router = APIRouter()


def _invitation_expiry() -> datetime | None:
    """Compute an invitation's ``expires_at`` (naive UTC, matching the
    password-reset token pattern). Returns ``None`` if expiry is disabled
    (``INVITATION_EXPIRE_HOURS <= 0``)."""
    hours = settings.INVITATION_EXPIRE_HOURS
    if hours <= 0:
        return None
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=hours)


def _invitation_expired(invitation: models.Invitation) -> bool:
    """True if the invitation has passed its ``expires_at``. ``None`` means
    "no expiry" (only legacy rows predating the column)."""
    if invitation.expires_at is None:
        return False
    return invitation.expires_at < datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/first-admin-check")
def first_admin_check(db: Session = Depends(get_db)):
    """Returns True if no admin exists and first-admin setup is allowed."""
    from ....core.security import any_admin_exists

    return {
        "allow_first_admin_setup": settings.ALLOW_FIRST_ADMIN_SETUP
        and not any_admin_exists(db)
    }


@router.post("/first-admin", response_model=schemas.UserResponse)
@limiter.limit("3/hour" if not settings.DISABLE_RATE_LIMIT else "1000/hour")
def create_first_admin(
    request: Request,
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    from ....core.security import any_admin_exists
    from ....utils.enums import UserRole

    # Only allow if config enabled and NO admin exists
    if not settings.ALLOW_FIRST_ADMIN_SETUP or any_admin_exists(db):
        raise HTTPException(status_code=403, detail="First admin creation not allowed.")

    # Validate and create admin user (role must be 'admin')
    if user_in.role != UserRole.admin:
        raise HTTPException(
            status_code=400, detail="Role must be admin for this endpoint."
        )

    validate_password(user_in.password)

    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400, detail="User with this email already exists."
        )

    new_user = models.User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=UserRole.admin,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    # Security-relevant bootstrap event: the first admin account being created.
    record_audit(
        AuditAction.USER_CREATE,
        actor=new_user,
        resource_type="user",
        resource_id=new_user.id,
        detail={"first_admin": True, "role": "admin"},
    )
    return schemas.UserResponse.model_validate(new_user)


@router.post("/change-password", response_model=schemas.UserResponse)
def change_password(
    password_data: schemas.PasswordChange,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.UserResponse:
    # Verify old password
    if not verify_password(
        password_data.old_password, str(current_user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect.",
        )
    if password_data.old_password == password_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the old password.",
        )
    validate_password(password_data.new_password)
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.token_version += 1  # Revoke existing tokens
    db.commit()
    db.refresh(current_user)
    record_audit(
        AuditAction.PASSWORD_CHANGE,
        actor=current_user,
        resource_type="user",
        resource_id=current_user.id,
        detail={"self": True},
    )
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
    validate_password(password_data.new_password)
    user.hashed_password = get_password_hash(password_data.new_password)
    user.token_version += 1  # Revoke existing tokens
    db.commit()
    db.refresh(user)
    record_audit(
        AuditAction.PASSWORD_CHANGE,
        actor=current_user,
        resource_type="user",
        resource_id=user.id,
        detail={"self": False, "by_admin": True},
    )
    return schemas.UserResponse.model_validate(user)


@router.post("", response_model=schemas.UserResponse)
@limiter.limit("5/minute" if not settings.DISABLE_RATE_LIMIT else "1000/minute")
def create_user(
    request: Request,
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

    # If an invitation token is provided, validate and mark it as used
    # (works regardless of REQUIRE_INVITATION setting)
    if user_in.invitation_token:
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

        if _invitation_expired(invitation):
            raise HTTPException(
                status_code=400,
                detail="Unable to create account. Please check your invitation and try again.",
            )

        # Check if the email matches the invitation
        if invitation.email and invitation.email != user_in.email:
            raise HTTPException(
                status_code=400,
                detail="Unable to create account. Please check your invitation and try again.",
            )

        # Mark the invitation as used
        invitation.is_used = True
        db.add(invitation)

    # Check if user already exists
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="Unable to create account. Please check your invitation and try again.",
        )

    validate_password(user_in.password)

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
    record_audit(
        AuditAction.USER_CREATE,
        actor=user,
        resource_type="user",
        resource_id=user.id,
        detail={"via": "invitation" if user_in.invitation_token else "open"},
    )
    return schemas.UserResponse.model_validate(user)


@router.get("", response_model=list[schemas.UserResponse])
def list_users(
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
) -> list[schemas.UserResponse]:
    """List all users (admin only)."""
    users = (
        db.query(models.User).order_by(models.User.id).limit(limit).offset(offset).all()
    )
    return [schemas.UserResponse.model_validate(user) for user in users]


@router.get("/me", response_model=schemas.UserResponse)
def read_current_user(
    current_user: models.User = Depends(get_current_user),
) -> schemas.UserResponse:
    """Get current user."""
    return schemas.UserResponse.model_validate(current_user)


@router.get("/me/identities", response_model=list[schemas.UserIdentityResponse])
def list_my_identities(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.UserIdentityResponse]:
    """List the SSO identities linked to the current user."""
    identities = (
        db.query(models.UserIdentity)
        .filter(models.UserIdentity.user_id == current_user.id)
        .all()
    )
    return [
        schemas.UserIdentityResponse(
            id=ident.id,
            provider_name=ident.provider.name,
            external_subject=ident.external_subject,
            created_at=ident.created_at,
            last_login_at=ident.last_login_at,
        )
        for ident in identities
    ]


@router.delete("/me/identities/{identity_id}")
def delete_my_identity(
    identity_id: int = Path(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unlink an SSO identity from the current user's account.

    Refuses if it's the user's last sign-in method and the account has no
    password set (would lock the user out).
    """
    identity = db.get(models.UserIdentity, identity_id)
    if not identity or identity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found."
        )
    remaining = (
        db.query(models.UserIdentity)
        .filter(models.UserIdentity.user_id == current_user.id)
        .all()
    )
    if len(remaining) <= 1 and not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disconnect your last sign-in method without a password set on the account.",
        )
    db.delete(identity)
    db.commit()
    return {"deleted": identity_id}


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

    # Collect all file UUIDs from the user's projects before cascade-delete
    file_uuids = (
        db.query(models.File.file_uuid)
        .join(models.Project, models.File.project_id == models.Project.id)
        .filter(models.Project.owner_id == user.id)
        .all()
    )
    file_uuids = [row[0] for row in file_uuids]

    # Delete physical files from storage
    for file_uuid in file_uuids:
        try:
            remove_file(file_uuid)
        except FileNotFoundError:
            pass  # File may not exist on disk — that's okay
        except Exception:
            logger.warning(
                "Failed to remove stored file %s while deleting user %s",
                file_uuid,
                user_id,
                exc_info=True,
            )

    db.delete(user)
    db.commit()
    record_audit(
        AuditAction.DELETE,
        actor=current_user,
        resource_type="user",
        resource_id=user_id,
        detail={"deleted_email": user.email, "stored_files_removed": len(file_uuids)},
    )
    return schemas.UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=schemas.UserResponse)
def admin_update_user(
    user_id: int = Path(...),
    update_data: schemas.UserUpdateAdmin = Body(...),
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> schemas.UserResponse:
    """Update user details (admin only). Only provided fields will be updated."""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent modifying other admin users (except setting self)
    if user.role == UserRole.admin and user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify other admin users",
        )

    # Track if we need to revoke tokens (on role/active changes)
    revoke_tokens = False

    if update_data.full_name is not None:
        user.full_name = update_data.full_name
    if update_data.email is not None:
        existing = (
            db.query(models.User)
            .filter(
                models.User.email == update_data.email,
                models.User.id != user_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )
        user.email = str(update_data.email)
    if update_data.role is not None:
        if update_data.role != UserRole.admin and current_user.id == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot demote yourself from admin",
            )
        user.role = update_data.role
        revoke_tokens = True
    if update_data.is_active is not None:
        if current_user.id == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot change your own active status",
            )
        user.is_active = update_data.is_active
        revoke_tokens = True

    if revoke_tokens:
        user.token_version += 1

    db.commit()
    db.refresh(user)
    if update_data.role is not None:
        record_audit(
            AuditAction.USER_ROLE_CHANGE,
            actor=current_user,
            resource_type="user",
            resource_id=user.id,
            detail={
                "new_role": str(
                    user.role.value if hasattr(user.role, "value") else user.role
                )
            },
        )
    if update_data.is_active is not None:
        record_audit(
            AuditAction.USER_DEACTIVATE,
            actor=current_user,
            resource_type="user",
            resource_id=user.id,
            outcome=AuditOutcome.SUCCESS,
            detail={"is_active": user.is_active},
        )
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
    user.token_version += 1  # Revoke all existing tokens on status change
    db.commit()
    db.refresh(user)
    record_audit(
        AuditAction.USER_DEACTIVATE,
        actor=current_user,
        resource_type="user",
        resource_id=user.id,
        detail={"is_active": user.is_active},
    )
    return schemas.UserResponse.model_validate(user)


@router.post("/invite", response_model=schemas.InvitationResponse)
def invite(
    email: str = Form(...),
    send_email: bool = Form(False),
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> schemas.InvitationResponse:
    """Invite a new user. Optionally sends invitation email if SMTP is configured."""
    # Check if invitation already exists for this email
    existing_invitation = (
        db.query(models.Invitation)
        .filter(models.Invitation.email == email, models.Invitation.is_used.is_(False))
        .first()
    )
    if existing_invitation:
        # Refresh the expiry so re-inviting a pending invite extends its window
        # (mirrors the password-reset flow, which always mints a fresh window).
        existing_invitation.expires_at = _invitation_expiry()
        db.commit()
        db.refresh(existing_invitation)
        resp = schemas.InvitationResponse.model_validate(existing_invitation)
        if send_email:
            base_url = settings.APP_URL
            invite_url = f"{base_url}/register?token={existing_invitation.token}"
            email_sent = send_invitation_email(
                email, existing_invitation.token, invite_url
            )
            resp.email_sent = email_sent
        return resp

    # Check if email is already registered
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists.",
        )

    # Generate a unique token
    token = secrets.token_urlsafe(32)
    invitation = models.Invitation(
        email=email,
        token=token,
        is_used=False,
        expires_at=_invitation_expiry(),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    record_audit(
        AuditAction.INVITATION_SEND,
        actor=current_user,
        resource_type="invitation",
        resource_id=invitation.id,
        detail={"email": email, "send_email": bool(send_email)},
    )

    resp = schemas.InvitationResponse.model_validate(invitation)

    # Send email if requested and SMTP is configured
    if send_email:
        base_url = settings.APP_URL
        invite_url = f"{base_url}/register?token={token}"
        email_sent = send_invitation_email(email, token, invite_url)
        resp.email_sent = email_sent

    return resp


@router.get("/invitations", response_model=list[schemas.InvitationResponse])
def list_invitations(
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
) -> list[schemas.InvitationResponse]:
    """List all invitations (admin only)."""
    invitations = (
        db.query(models.Invitation)
        .order_by(models.Invitation.id)
        .limit(limit)
        .offset(offset)
        .all()
    )
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
@limiter.limit("30/hour" if not settings.DISABLE_RATE_LIMIT else "1000/hour")
def validate_invitation(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> schemas.InvitationInfo:
    """Validate an invitation token and return associated email."""
    invitation = (
        db.query(models.Invitation)
        .filter(models.Invitation.token == token, models.Invitation.is_used.is_(False))
        .first()
    )
    if not invitation or _invitation_expired(invitation):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation token",
        )
    return schemas.InvitationInfo(valid=True, email=str(invitation.email))


# ---------- Password Reset (public endpoints) ----------


@router.post("/forgot-password")
@limiter.limit("5/hour" if not settings.DISABLE_RATE_LIMIT else "1000/hour")
def forgot_password(
    request: Request,
    body: schemas.PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """Request a password reset email.

    Always returns success to prevent email enumeration.
    """
    # Look up user silently — always return success
    user = db.query(models.User).filter(models.User.email == body.email).first()

    if user and user.is_active:
        # Delete any existing reset tokens for this user
        db.query(models.PasswordResetToken).filter(
            models.PasswordResetToken.user_id == user.id
        ).delete()

        # Create new reset token (24h expiry). Only the sha256 hash is stored;
        # the plaintext is emailed once and never persisted, so a DB read
        # (SQLi, backup/replica exposure) cannot yield a usable reset token.
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            hours=24
        )
        reset_token = models.PasswordResetToken(
            user_id=user.id,
            token=_hash_token(token),
            expires_at=expires_at,
        )
        db.add(reset_token)
        db.commit()

        # Send email if configured
        base_url = settings.APP_URL
        reset_url = f"{base_url}/reset-password/{token}"
        email_sent = send_password_reset_email(body.email, token, reset_url)

        if not email_sent:
            return {
                "message": "If an account with this email exists, a password reset link has been generated. "
                "Please contact your administrator to obtain the reset link.",
                "warning": "Email delivery is not configured. The reset link was not sent.",
            }

    return {
        "message": "If an account with this email exists, a password reset link has been sent.",
    }


@router.get(
    "/validate-reset-token/{token}", response_model=schemas.PasswordResetValidate
)
@limiter.limit("30/hour" if not settings.DISABLE_RATE_LIMIT else "1000/hour")
def validate_reset_token(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> schemas.PasswordResetValidate:
    """Check if a password reset token is valid and not expired."""
    reset_token = (
        db.query(models.PasswordResetToken)
        .filter(models.PasswordResetToken.token == _hash_token(token))
        .first()
    )
    if not reset_token or reset_token.expires_at < datetime.now(timezone.utc).replace(
        tzinfo=None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired reset token",
        )
    return schemas.PasswordResetValidate(valid=True)


@router.post("/reset-password/{token}")
@limiter.limit("10/hour" if not settings.DISABLE_RATE_LIMIT else "1000/hour")
def reset_password(
    request: Request,
    token: str,
    body: schemas.PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """Reset password using a valid reset token."""
    # Validate token in URL matches body
    if body.token != token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token mismatch",
        )

    reset_token = (
        db.query(models.PasswordResetToken)
        .filter(models.PasswordResetToken.token == _hash_token(token))
        .first()
    )
    if not reset_token or reset_token.expires_at < datetime.now(timezone.utc).replace(
        tzinfo=None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired reset token",
        )

    # Update user password
    user = db.get(models.User, reset_token.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired reset token",
        )

    validate_password(body.new_password)
    user.hashed_password = get_password_hash(body.new_password)
    user.token_version += 1  # Revoke existing JWT sessions

    # Delete the used token
    db.delete(reset_token)
    db.commit()

    record_audit(
        AuditAction.PASSWORD_RESET,
        actor=user,
        resource_type="user",
        resource_id=user.id,
    )
    return {"message": "Password has been reset successfully."}
