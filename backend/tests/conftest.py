# backend/tests/conftest.py
import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Set up test environment variables BEFORE any app imports
@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Configure test environment variables"""
    # Store original values
    original_env_vars = {
        "SQLALCHEMY_DATABASE_URI": os.environ.get("SQLALCHEMY_DATABASE_URI"),
        "LOCAL_DIRECTORY": os.environ.get("LOCAL_DIRECTORY"),
    }

    # Get test directory path
    test_dir = Path("test_local_storage").resolve()
    os.makedirs(test_dir, exist_ok=True)

    # Set test database path
    test_db_path = test_dir / "test_database.db"
    os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{test_db_path}"

    # Set local directory for file storage
    os.environ["LOCAL_DIRECTORY"] = str(test_dir)

    yield  # Tests run here

    # Restore original environment variables
    for var, value in original_env_vars.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]

    # Cleanup test directory
    try:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
        if test_dir.exists():
            shutil.rmtree(test_dir)
    except Exception as e:
        print(f"Cleanup error: {e}")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(configure_test_environment):
    """Setup database and users after environment is configured"""
    from backend.src.core.security import get_password_hash
    from backend.src.db.base import Base
    from backend.src.db.session import SessionLocal, engine
    from backend.src.models.user import User, UserRole

    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Create test users
    users = {
        "admin@example.com": ("Admin User", "adminpassword", UserRole.admin),
        "test@example.com": ("Test User", "testpassword", UserRole.user),
        "another@example.com": ("Another User", "anotherpassword", UserRole.user),
        "delete@example.com": ("Delete User", "testpassword", UserRole.user),
    }

    db = SessionLocal()
    for email, (name, password, role) in users.items():
        if not db.query(User).filter(User.email == email).first():
            user = User(
                email=email,
                full_name=name,
                hashed_password=get_password_hash(password),
                role=role,
                is_active=True,
            )
            db.add(user)
    db.commit()
    db.close()


@pytest.fixture
def client():
    """Client fixture that imports app AFTER environment setup"""
    from backend.src.main import app  # Only import here!

    return TestClient(app)


@pytest.fixture
def api_url():
    return "/api/v1"


@pytest.fixture
def files_base_path():
    """Absolute path to test files directory (in backend/tests/files)"""
    return Path(__file__).parent / "files"  # This points to backend/tests/files


# Helper function to restore deleted users
def restore_user(email: str, password: str, role, is_active: bool = True):
    """Helper to restore a deleted user after tests"""
    from backend.src.core.security import get_password_hash
    from backend.src.db.session import SessionLocal
    from backend.src.models.user import User

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.is_active = is_active
        user.hashed_password = get_password_hash(password)
    else:
        user = User(
            email=email,
            full_name=f"{str(role).capitalize()} User",
            hashed_password=get_password_hash(password),
            role=role,
            is_active=is_active,
        )
        db.add(user)
    db.commit()
    db.close()
