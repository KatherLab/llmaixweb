# backend/tests/test_projects.py
"""Tests for the core project resource: CRUD + access control.

Covers the project lifecycle endpoints (create, list, get, update, delete under
/project) and the cross-user authorization boundary: a project is owned by its
creator, so a different (non-admin) user gets 403 `projects.not_authorized` when
trying to read, update, or delete it. The 404 `projects.not_found` path for an
unknown project id is pinned down alongside the happy-path get.
"""


# Test Create Project
def test_create_project(client, api_url, user_headers):
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(
        f"{api_url}/project", headers=user_headers, json=project_data
    )
    assert response.status_code == 200
    assert response.json()["name"] == project_data["name"]


# Test Get Projects
def test_get_projects(client, api_url, user_headers):
    response = client.get(f"{api_url}/project", headers=user_headers)
    assert response.status_code == 200
    assert len(response.json()) > 0


# Test Get Project
def test_get_project(client, api_url, user_headers):
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(
        f"{api_url}/project", headers=user_headers, json=project_data
    )
    assert response.status_code == 200
    project_id = response.json()["id"]
    response = client.get(f"{api_url}/project/{project_id}", headers=user_headers)
    assert response.status_code == 200
    assert response.json()["name"] == project_data["name"]

    response = client.get(f"{api_url}/project/372849078", headers=user_headers)
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "projects.not_found"


# Test Update Project
def test_update_project(client, api_url, user_headers, make_project):
    project_id = make_project(user_headers)["id"]
    updated_project_data = {
        "name": "Updated Test Project",
        "description": "This is an updated test project",
    }
    response = client.put(
        f"{api_url}/project/{project_id}",
        headers=user_headers,
        json=updated_project_data,
    )
    assert response.status_code == 200
    assert response.json()["name"] == updated_project_data["name"]


# Test Delete Project
def test_delete_project(client, api_url, user_headers, make_project):
    project = make_project(user_headers)
    project_id = project["id"]
    response = client.delete(f"{api_url}/project/{project_id}", headers=user_headers)
    assert response.status_code == 200
    assert response.json()["name"] == project["name"]


def test_project_access_control(
    client, api_url, user_headers, admin_headers, make_project
):
    project_id = make_project(user_headers)["id"]

    # Login as another user
    another_user_data = {
        "username": "another@example.com",
        "password": "Anotherpassword1",
    }
    # Create another user
    invitation_data = {"email": "anotherinvited@example.com"}
    response = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data=invitation_data
    )
    assert response.status_code == 200
    invitation_token = response.json()["token"]
    another_user_create_data = {
        "email": "anotherinvited@example.com",
        "full_name": "Another User",
        "password": "Anotherpassword1",
        "invitation_token": invitation_token,
    }
    response = client.post(f"{api_url}/user", json=another_user_create_data)
    assert response.status_code == 200

    response = client.post(f"{api_url}/auth/login", data=another_user_data)
    print(response.json())
    assert response.status_code == 200
    another_access_token = response.json()["access_token"]
    another_headers = {"Authorization": f"Bearer {another_access_token}"}

    # Try to get the project as another user
    response = client.get(f"{api_url}/project/{project_id}", headers=another_headers)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "projects.not_authorized"

    # Try to update the project as another user
    updated_project_data = {
        "name": "Updated Test Project",
        "description": "This is an updated test project",
    }
    response = client.put(
        f"{api_url}/project/{project_id}",
        headers=another_headers,
        json=updated_project_data,
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "projects.not_authorized"

    # Try to delete the project as another user
    response = client.delete(f"{api_url}/project/{project_id}", headers=another_headers)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "projects.not_authorized"
