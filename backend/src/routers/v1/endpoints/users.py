from fastapi import APIRouter, Depends, Path, HTTPException, status
from sqlalchemy.orm import Session

from .... import schemas
from .... import models
from ....core.security import get_admin_user
from ....dependencies import get_db

router = APIRouter()


@router.delete("/{user_id}", response_model=schemas.UserResponse)
def delete_user(
    *,
    db: Session = Depends(get_db),
    user_id: int = Path(...),
    current_user: models.User = Depends(get_admin_user),
):
    """
    Delete a user (admin only).
    """

    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own user account",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent deleting admin users
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin users",
        )

    db.delete(user)
    db.commit()

    return user
