import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_url():
    return "/api/v1"


@pytest.fixture
def client():
    from ..src.main import app

    return TestClient(app)


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
    assert (
        response.json()["detail"]
        == "Unable to create account. Please check your invitation and try again."
    )

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
    # Admin user login
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=admin_user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {access_token}"}

    # Create a new test user with unique email
    toggle_test_email = "toggletest@example.com"
    test_password = "toggletestpassword"

    # Admin invites the new user
    invitation_data = {"email": toggle_test_email}
    response = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data=invitation_data
    )
    assert response.status_code == 200
    invitation_token = response.json()["token"]

    # User registers themselves
    user_register_data = {
        "email": toggle_test_email,
        "full_name": "Toggle Test User",
        "password": test_password,
        "invitation_token": invitation_token,
    }
    response = client.post(f"{api_url}/user", json=user_register_data)
    assert response.status_code == 200

    # Get the ID of our new user
    response = client.get(f"{api_url}/user", headers=admin_headers)
    assert response.status_code == 200
    toggle_test_user = next(
        (user for user in response.json() if user["email"] == toggle_test_email),
        None,
    )
    toggle_test_user_id = toggle_test_user["id"]
    assert toggle_test_user is not None, "Test user not found"

    # Toggle the status to inactive
    response = client.patch(
        f"{api_url}/user/{toggle_test_user_id}/toggle-status", headers=admin_headers
    )
    assert response.status_code == 200
    toggled_user = response.json()
    assert not toggled_user["is_active"]

    # Toggle back to active
    response = client.patch(
        f"{api_url}/user/{toggle_test_user_id}/toggle-status", headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["is_active"]

    # Test invalid user ID
    invalid_user_id = 99999
    response = client.patch(
        f"{api_url}/user/{invalid_user_id}/toggle-status", headers=admin_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

    # Test with user role (should fail)
    # Log in as the test user
    test_user_login = {
        "username": toggle_test_email,
        "password": test_password,
    }
    response = client.post(f"{api_url}/auth/login", data=test_user_login)
    assert response.status_code == 200
    test_user_token = response.json()["access_token"]
    test_headers = {"Authorization": f"Bearer {test_user_token}"}

    # Try to toggle own status
    response = client.patch(
        f"{api_url}/user/{toggle_test_user_id}/toggle-status", headers=test_headers
    )
    assert response.status_code == 403  # Forbidden

    # Restore the test user to active in case they were deactivated
    from backend.src.utils.enums import UserRole

    from .helpers import restore_user

    restore_user(toggle_test_email, test_password, UserRole.user, True)


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
    new_password = "testpassword"
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

    from backend.src.utils.enums import UserRole

    from .helpers import restore_user

    restore_user("delete@example.com", "testpassword", UserRole.user, True)
