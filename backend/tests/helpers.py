# backend/tests/helpers.py
from backend.src.core.security import get_password_hash
from backend.src.db.session import SessionLocal
from backend.src.models.user import User
from backend.src.utils.enums import UserRole


def restore_user(email: str, password: str, role: UserRole, is_active: bool = True):
    """Helper function to restore a deleted user after a test"""
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.is_active = is_active
        user.hashed_password = get_password_hash(password)
    else:
        user = User(
            email=email,
            full_name=f"{role.name.capitalize()} User",
            hashed_password=get_password_hash(password),
            role=role,
            is_active=is_active,
        )
        db.add(user)
    db.commit()
    db.close()
