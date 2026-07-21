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
        "admin@example.com": ("Admin User", "Adminpassword1", UserRole.admin),
        "test@example.com": ("Test User", "Testpassword1", UserRole.user),
        "another@example.com": ("Another User", "Anotherpassword1", UserRole.user),
        "delete@example.com": ("Delete User", "Testpassword1", UserRole.user),
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


# ---------------------------------------------------------------------------
# Shared auth / setup fixtures
#
# Every API test needs to log in, build an Authorization header, and usually
# create a project + upload files before it can assert anything. These factory
# fixtures remove that boilerplate. `admin@example.com` is required for the
# admin-only paths (e.g. Trial.bypass_celery); `test@example.com` is a plain
# user. Both are seeded by `setup_test_environment` above.
# ---------------------------------------------------------------------------

# (email, password) for the users seeded in setup_test_environment.
USER_CREDS = ("test@example.com", "Testpassword1")
ADMIN_CREDS = ("admin@example.com", "Adminpassword1")


@pytest.fixture
def login(client, api_url):
    """Return `login(email, password) -> {"Authorization": "Bearer ..."}`."""

    def _login(email: str = USER_CREDS[0], password: str = USER_CREDS[1]) -> dict:
        resp = client.post(
            f"{api_url}/auth/login",
            data={"username": email, "password": password},
        )
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _login


@pytest.fixture
def user_headers(login):
    """Auth headers for the plain `test@example.com` user."""
    return login(*USER_CREDS)


@pytest.fixture
def admin_headers(login):
    """Auth headers for the `admin@example.com` admin user."""
    return login(*ADMIN_CREDS)


@pytest.fixture
def make_project(client, api_url):
    """Return `make_project(headers, name=..., description=...) -> project dict`."""

    def _make(
        headers: dict,
        name: str = "Test Project",
        description: str = "This is a test project",
    ) -> dict:
        resp = client.post(
            f"{api_url}/project",
            headers=headers,
            json={"name": name, "description": description},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _make


@pytest.fixture
def upload_file(client, api_url):
    """Return an `upload_file(...)` helper for both in-memory bytes and disk paths.

    Usage:
        upload_file(headers, project_id, content=b"hi", name="a.txt")
        upload_file(headers, project_id, path=some_pdf, content_type="application/pdf")

    `file_info_extra` merges extra keys (e.g. preprocessing_strategy,
    file_metadata) into the ``file_info`` JSON part.
    """
    import json as _json

    def _upload(
        headers: dict,
        project_id: int,
        *,
        content: bytes | None = None,
        path=None,
        name: str | None = None,
        content_type: str = "text/plain",
        file_info_extra: dict | None = None,
    ) -> dict:
        if path is not None:
            with open(path, "rb") as f:
                data = f.read()
            name = name or path.name
        else:
            if content is None:
                content = b"Hello World!"
            name = name or "test.txt"
            data = content

        file_info = {"file_name": name, "file_type": content_type}
        if file_info_extra:
            file_info.update(file_info_extra)

        resp = client.post(
            f"{api_url}/project/{project_id}/file",
            headers=headers,
            files={"file": (name, data, content_type)},
            data={"file_info": _json.dumps(file_info)},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _upload


@pytest.fixture
def make_schema(client, api_url):
    """Return `make_schema(headers, project_id, name=..., definition=...) -> dict`."""

    def _make(
        headers: dict,
        project_id: int,
        name: str = "Test Schema",
        definition: dict | None = None,
    ) -> dict:
        if definition is None:
            definition = {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "location": {"type": "string"},
                },
            }
        resp = client.post(
            f"{api_url}/project/{project_id}/schema",
            headers=headers,
            json={"schema_name": name, "schema_definition": definition},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _make


@pytest.fixture
def make_prompt(client, api_url):
    """Return `make_prompt(headers, project_id, ...) -> prompt dict`."""

    def _make(
        headers: dict,
        project_id: int,
        name: str = "Test Prompt",
        system_prompt: str = "Extract info: {document_content}",
        user_prompt: str = "Please extract data from {document_content}.",
    ) -> dict:
        resp = client.post(
            f"{api_url}/project/{project_id}/prompt",
            headers=headers,
            json={
                "name": name,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "project_id": project_id,
            },
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _make


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
