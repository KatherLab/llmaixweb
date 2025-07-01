import os
import shutil

import pytest
from fastapi.testclient import TestClient


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
def api_url():
    return "/api/v1"


@pytest.fixture
def client():
    from ..src.main import app

    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    from ..src.core.security import get_password_hash
    from ..src.db.base import Base
    from ..src.db.session import SessionLocal, engine
    from ..src.models.user import User, UserRole

    print("Current working directory:", os.getcwd())
    # Create admin user
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    admin_user = db.query(User).filter(User.role == UserRole.admin).first()
    if not admin_user:
        admin_user = User(
            email="admin@example.com",
            full_name="Admin User",
            hashed_password=get_password_hash("adminpassword"),
            role=UserRole.admin.value,
            is_active=True,
        )

        test_user = User(
            email="test@example.com",
            full_name="Test User",
            hashed_password=get_password_hash("testpassword"),
            role=UserRole.user.value,
            is_active=True,
        )
        test_user_to_delete = User(
            email="delete@example.com",
            full_name="Delete User",
            hashed_password=get_password_hash("testpassword"),
            role=UserRole.user.value,
            is_active=True,
        )
        db.add(test_user)
        db.add(test_user_to_delete)
        db.add(admin_user)
        db.commit()
    db.close()


# Test Register User
def test_register_user(client, api_url):
    # Create an invitation first
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    invitation_data = {"email": "test@example.com"}
    response = client.post(
        f"{api_url}/user/invite", headers=headers, data=invitation_data
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email already exists."

    invitation_data = {"email": "inviteduser@example.com"}
    response = client.post(
        f"{api_url}/user/invite", headers=headers, data=invitation_data
    )
    assert response.status_code == 200

    invitation_token = response.json()["token"]

    # Register a new user using the invitation token
    user_data = {
        "email": "new@example.com",
        "full_name": "New User",
        "password": "testpassword",
        "invitation_token": invitation_token,
    }
    response = client.post(f"{api_url}/user", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email does not match the invitation."

    user_data = {
        "email": "inviteduser@example.com",
        "full_name": "New User",
        "password": "testpassword",
        "invitation_token": invitation_token,
    }
    response = client.post(f"{api_url}/user", json=user_data)
    assert response.status_code == 200

    assert response.json()["email"] == user_data["email"]


# Test Login User
def test_login_user(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    assert "access_token" in response.json()


# Test Read Current User
def test_read_current_user(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get(f"{api_url}/user/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == user_data["username"]


# Test List Users (admin only)
def test_list_users(client, api_url):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get(f"{api_url}/user", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) > 0
    # Test with user role
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get(f"{api_url}/user", headers=headers)
    assert response.status_code == 403  # Forbidden
    # Test with invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get(f"{api_url}/user", headers=headers)
    assert response.status_code == 401  # Unauthorized


# Test Invite User (admin only)
def test_invite_user(client, api_url):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {access_token}"}
    invitation_data = {"email": "invited@example.com"}
    response = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data=invitation_data
    )
    assert response.status_code == 200
    assert response.json()["email"] == invitation_data["email"]
    # Test with existing user email
    invitation_data = {"email": "test@example.com"}
    response = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data=invitation_data
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email already exists."
    # Test with user role
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post(
        f"{api_url}/user/invite", headers=user_headers, data=invitation_data
    )
    assert response.status_code == 403  # Forbidden


# Test Validate Invitation
def test_validate_invitation(client, api_url):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    invitation_data = {"email": "invitedtest@example.com"}
    response = client.post(
        f"{api_url}/user/invite", headers=headers, data=invitation_data
    )
    assert response.status_code == 200
    invitation_token = response.json()["token"]
    response = client.get(f"{api_url}/user/validate-invitation/{invitation_token}")
    assert response.status_code == 200
    assert response.json()["valid"]
    # Test with invalid token
    response = client.get(f"{api_url}/user/validate-invitation/invalid_token_748")
    assert response.status_code == 404
    assert response.json()["detail"] == "Invalid or expired invitation token"


# Test List Invitations (admin only)
def test_list_invitations(client, api_url):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get(f"{api_url}/user/invitations", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) > 0
    # Test with user role
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get(f"{api_url}/user/invitations", headers=headers)
    assert response.status_code == 403  # Forbidden


# Test Delete Invitation (admin only)
def test_delete_invitation(client, api_url):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {access_token}"}
    invitation_data = {"email": "inviteddelete@example.com"}
    response = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data=invitation_data
    )
    assert response.status_code == 200
    invitation_id = response.json()["id"]
    response = client.delete(
        f"{api_url}/user/invitations/{invitation_id}", headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["email"] == invitation_data["email"]
    # Test with user role
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {access_token}"}
    response = client.delete(
        f"{api_url}/user/invitations/{invitation_id}", headers=user_headers
    )
    assert response.status_code == 403  # Forbidden
    # Test with invalid invitation id
    response = client.delete(f"{api_url}/user/invitations/99999", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Invitation not found"


# Test Toggle User Status (admin only)
def test_toggle_user_status(client, api_url):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {access_token}"}
    user_id = 2  # Assuming the test user has ID 2
    response = client.patch(
        f"{api_url}/user/{user_id}/toggle-status", headers=admin_headers
    )
    assert response.status_code == 200
    assert not response.json()["is_active"]
    # Test with invalid user id
    response = client.patch(
        f"{api_url}/user/99999/toggle-status", headers=admin_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
    # Test with user role
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {access_token}"}
    response = client.patch(
        f"{api_url}/user/{user_id}/toggle-status", headers=user_headers
    )
    assert response.status_code == 403  # Forbidden


# Test Reset Password
def test_reset_password(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    new_password = "newpassword"
    response = client.post(
        f"{api_url}/user/reset-password?new_password={new_password}", headers=headers
    )
    # Not implemented in yet, so we expect a 501 Not Implemented status
    print(response.json())
    assert response.status_code == 501
    # assert response.json()["email"] == user_data["username"]


# Test Delete User (admin only)
def test_delete_user(client, api_url):
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get(f"{api_url}/user", headers=admin_headers)
    user_id: None | int = next(
        (
            user["id"]
            for user in response.json()
            if user["email"] == "delete@example.com"
        ),
        None,
    )
    assert user_id is not None, "User to delete not found"
    response = client.delete(f"{api_url}/user/{user_id}", headers=admin_headers)
    # print(response.json())
    assert response.status_code == 200
    assert response.json()["email"] == "delete@example.com"
    # Test with invalid user id
    response = client.delete(f"{api_url}/user/99999", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
    # Test with user role
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    print(response.json())
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {access_token}"}
    response = client.delete(f"{api_url}/user/{user_id}", headers=user_headers)
    assert response.status_code == 403  # Forbidden
