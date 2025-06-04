import shutil
import pytest
from fastapi.testclient import TestClient
import os


# Fixtures for setup and teardown
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
        db.add(test_user)
        db.add(admin_user)
        db.commit()
    db.close()


# Test Create Project
def test_create_project(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post("/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    assert response.json()["name"] == project_data["name"]


# Test Get Projects
def test_get_projects(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/project/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) > 0


# Test Get Project
def test_get_project(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post("/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]
    response = client.get(f"/project/{project_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == project_data["name"]


# Test Update Project
def test_update_project(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post("/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]
    updated_project_data = {
        "name": "Updated Test Project",
        "description": "This is an updated test project",
    }
    response = client.put(
        f"/project/{project_id}", headers=headers, json=updated_project_data
    )
    assert response.status_code == 200
    assert response.json()["name"] == updated_project_data["name"]


# Test Delete Project
def test_delete_project(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post("/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]
    response = client.delete(f"/project/{project_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == project_data["name"]


# Test Get Project Files
def test_get_project_files(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post("/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]
    response = client.get(f"/project/{project_id}/files", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 0  # No files uploaded yet


# Test Upload File
def test_upload_file(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}  # Removed Content-Type header
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(
        "/project/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=project_data,
    )
    assert response.status_code == 200
    project_id = response.json()["id"]
    with open("files/9874562_text.pdf", "rb") as f:
        file_data = {
            "file": ("9874562_text.pdf", f, "application/pdf"),
        }
        file_info = '{"file_name": "9874562_text.pdf", "file_type": "application/pdf"}'
        response = client.post(
            f"/project/{project_id}/file",
            headers=headers,
            files=file_data,
            data={"file_info": file_info},
        )
    assert response.status_code == 200
    response_json = response.json()
    assert "id" in response_json
    assert "file_name" in response_json
    assert "file_type" in response_json
    assert response_json["file_name"] == "9874562_text.pdf"
    assert response_json["file_type"] == "application/pdf"


# Test Get Project File
def test_get_project_file(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}  # Removed Content-Type header
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(
        "/project/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=project_data,
    )
    assert response.status_code == 200
    project_id = response.json()["id"]
    file_data = {
        "file": ("test.txt", b"Hello World!", "text/plain"),
        "file_info": (
            "",
            '{"file_name": "test.txt", "file_type": "text/plain"}',
            "application/json",
        ),
    }
    response = client.post(
        f"/project/{project_id}/file", headers=headers, files=file_data
    )
    assert response.status_code == 200
    file_id = response.json()["id"]
    response = client.get(f"/project/{project_id}/file/{file_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["file_name"] == "test.txt"


# Test Delete File
def test_delete_file(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}  # Removed Content-Type header
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(
        "/project/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=project_data,
    )
    assert response.status_code == 200
    project_id = response.json()["id"]
    file_data = {
        "file": ("test.txt", b"Hello World!", "text/plain"),
        "file_info": (
            "",
            '{"file_name": "test.txt", "file_type": "text/plain"}',
            "application/json",
        ),
    }
    response = client.post(
        f"/project/{project_id}/file", headers=headers, files=file_data
    )
    assert response.status_code == 200
    file_id = response.json()["id"]
    response = client.delete(f"/project/{project_id}/file/{file_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["file_name"] == "test.txt"


# Test Get Project File Content
def test_get_project_file_content(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}  # Removed Content-Type header
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(
        "/project/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=project_data,
    )
    assert response.status_code == 200
    project_id = response.json()["id"]
    file_data = {
        "file": ("test.txt", b"Hello KatherLab!", "text/plain"),
        "file_info": (
            "",
            '{"file_name": "test.txt", "file_type": "text/plain"}',
            "application/json",
        ),
    }
    response = client.post(
        f"/project/{project_id}/file", headers=headers, files=file_data
    )
    assert response.status_code == 200
    file_id = response.json()["id"]
    response = client.get(
        f"/project/{project_id}/file/{file_id}/content", headers=headers
    )
    assert response.status_code == 200
    assert response.content == b"Hello KatherLab!"


# Test Preprocess Project Data
def test_preprocess_project_data(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(
        "/project/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=project_data,
    )
    assert response.status_code == 200
    project_id = response.json()["id"]

    preprocessing_data = {
        "bypass_celery": True,
    }

    response = client.post(
        f"/project/{project_id}/preprocess", headers=headers, json=preprocessing_data
    )
    assert response.status_code == 200


# Test Create Project and check that another user can't access it
def test_project_access_control(client):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post("/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post("/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]

    # Login as another user
    another_user_data = {
        "username": "another@example.com",
        "password": "anotherpassword",
    }
    # Create another user
    admin_user_data = {
        "username": "admin@example.com",
        "password": "adminpassword",
    }
    response = client.post("/auth/login", data=admin_user_data)
    assert response.status_code == 200
    admin_access_token = response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_access_token}"}
    invitation_data = {"email": "another@example.com"}
    response = client.post("/auth/invite", headers=admin_headers, data=invitation_data)
    assert response.status_code == 200
    invitation_token = response.json()["token"]
    another_user_create_data = {
        "email": "another@example.com",
        "full_name": "Another User",
        "password": "anotherpassword",
        "invitation_token": invitation_token,
    }
    response = client.post("/auth/register", json=another_user_create_data)
    assert response.status_code == 200

    response = client.post("/auth/login", data=another_user_data)
    assert response.status_code == 200
    another_access_token = response.json()["access_token"]
    another_headers = {"Authorization": f"Bearer {another_access_token}"}

    # Try to get the project as another user
    response = client.get(f"/project/{project_id}", headers=another_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access this project"

    # Try to update the project as another user
    updated_project_data = {
        "name": "Updated Test Project",
        "description": "This is an updated test project",
    }
    response = client.put(
        f"/project/{project_id}", headers=another_headers, json=updated_project_data
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update this project"

    # Try to delete the project as another user
    response = client.delete(f"/project/{project_id}", headers=another_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to delete this project"
