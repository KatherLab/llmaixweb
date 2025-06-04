import shutil

import pytest
from fastapi.testclient import TestClient
import os


@pytest.fixture(scope="session", autouse=True)
def set_working_directory():
    os.chdir(os.path.dirname(__file__))


@pytest.fixture(scope="session", autouse=True)
def setup_and_teardown_test_dir():
    test_dir = "test_local_storage"
    db_file = "database.db"

    print("Current working directory:", os.getcwd())

    # Create the test directory
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)

    yield

    # Teardown: Delete the database file and the test directory
    try:
        if os.path.exists(db_file):
            os.remove(db_file)
    except Exception as e:
        print(f"Error deleting database file: {e}")

    try:
        shutil.rmtree(test_dir)
    except Exception as e:
        print(f"Error deleting test directory: {e}")


@pytest.fixture
def client():
    print("Provide client")
    from ..src.main import app

    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    from ..src.db.base import Base

    from ..src.db.session import SessionLocal, engine
    from ..src.models.user import User, UserRole
    from ..src.core.security import get_password_hash

    print("Current working directory:", os.getcwd())
    # Create admin user
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    admin_user = db.query(User).filter(User.role == UserRole.ADMIN).first()
    if not admin_user:
        admin_user = User(
            email="admin@example.com",
            full_name="Admin User",
            hashed_password=get_password_hash("adminpassword"),
            role=UserRole.ADMIN.value,
            is_active=True,
        )

        test_user = User(
            email="test@example.com",
            full_name="Test User",
            hashed_password=get_password_hash("testpassword"),
            role=UserRole.USER.value,
            is_active=True,
        )
        test_user_to_delete = User(
            email="delete@example.com",
            full_name="Delete User",
            hashed_password=get_password_hash("testpassword"),
            role=UserRole.USER.value,
            is_active=True,
        )
        db.add(test_user)
        db.add(test_user_to_delete)
        db.add(admin_user)
        db.commit()
    db.close()


# Test Register User
def test_register_user(client):
    # Create an invitation first
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post("/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    invitation_data = {"email": "test@example.com"}
    response = client.post("/auth/invite", headers=headers, data=invitation_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email already exists."

    invitation_data = {"email": "inviteduser@example.com"}
    response = client.post("/auth/invite", headers=headers, data=invitation_data)
    assert response.status_code == 200

    invitation_token = response.json()["token"]

    # Register a new user using the invitation token
    user_data = {
        "email": "new@example.com",
        "full_name": "New User",
        "password": "testpassword",
        "invitation_token": invitation_token,
    }
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email does not match the invitation."

    user_data = {
        "email": "inviteduser@example.com",
        "full_name": "New User",
        "password": "testpassword",
        "invitation_token": invitation_token,
    }
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 200

    assert response.json()["email"] == user_data["email"]


# Test Login User
def test_login_user(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    assert "access_token" in response.json()


# Test Read Current User
def test_read_current_user(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == user_data["username"]


# Test List Users (admin only)
def test_list_users(client):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post("/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/auth/users", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) > 0

    # Test with user role
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/auth/users", headers=headers)
    assert response.status_code == 403  # Forbidden


# ... (rest of the test code)


# Test Invite User (admin only)
def test_invite_user(client):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post("/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    invitation_data = {"email": "invited@example.com"}
    response = client.post("/auth/invite", headers=headers, data=invitation_data)
    assert response.status_code == 200
    assert response.json()["email"] == invitation_data["email"]

    # Test with user role
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post("/auth/invite", headers=headers, data=invitation_data)
    assert response.status_code == 403  # Forbidden


# ... (rest of the test code)


# Test Validate Invitation
def test_validate_invitation(client):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post("/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    invitation_data = {"email": "invitedtest@example.com"}
    response = client.post("/auth/invite", headers=headers, data=invitation_data)
    assert response.status_code == 200
    invitation_token = response.json()["token"]

    response = client.get(f"/auth/validate-invitation/{invitation_token}")
    assert response.status_code == 200
    assert response.json()["valid"]


# Test List Invitations (admin only)
def test_list_invitations(client):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post("/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/auth/invitations", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) > 0

    # Test with user role
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/auth/invitations", headers=headers)
    assert response.status_code == 403  # Forbidden


# Test Delete Invitation (admin only)
def test_delete_invitation(client):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post("/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    invitation_data = {"email": "inviteddelete@example.com"}
    response = client.post("/auth/invite", headers=headers, data=invitation_data)
    assert response.status_code == 200
    invitation_id = response.json()["id"]

    response = client.delete(f"/auth/invitations/{invitation_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == invitation_data["email"]

    # Test with user role
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.delete(f"/auth/invitations/{invitation_id}", headers=headers)
    assert response.status_code == 403  # Forbidden


# Test Toggle User Status (admin only)
def test_toggle_user_status(client):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post("/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    user_id = 2  # Assuming the test user has ID 2
    response = client.patch(f"/auth/users/{user_id}/toggle-status", headers=headers)
    assert response.status_code == 200
    assert not response.json()["is_active"]

    # Test with user role
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.patch(f"/auth/users/{user_id}/toggle-status", headers=headers)
    assert response.status_code == 403  # Forbidden


# Test Reset Password
def test_reset_password(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    new_password = "newpassword"
    response = client.post(
        f"/auth/reset-password?new_password={new_password}", headers=headers
    )
    # Not implemented in yet, so we expect a 501 Not Implemented status
    assert response.status_code == 501
    # assert response.json()["email"] == user_data["username"]


# Test Delete User (admin only)
def test_delete_user(client):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post("/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/auth/users", headers=headers)
    user_id: None | int = next(
        (
            user["id"]
            for user in response.json()
            if user["email"] == "delete@example.com"
        ),
        None,
    )

    assert user_id is not None, "User to delete not found"

    response = client.delete(f"/user/{user_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "delete@example.com"
