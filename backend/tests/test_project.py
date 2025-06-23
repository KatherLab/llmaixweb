import shutil
import pytest
from fastapi.testclient import TestClient
import os
import jsonschema

from backend.src.core.config import settings


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
def api_url():
    print("Provide API URL")
    return "/api/v1"


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
def test_create_project(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(f"{api_url}/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    assert response.json()["name"] == project_data["name"]


# Test Get Projects
def test_get_projects(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get(f"{api_url}/project/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) > 0


# Test Get Project
def test_get_project(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(f"{api_url}/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]
    response = client.get(f"{api_url}/project/{project_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == project_data["name"]

    response = client.get(f"{api_url}/project/372849078/", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


# Test Update Project
def test_update_project(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(f"{api_url}/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]
    updated_project_data = {
        "name": "Updated Test Project",
        "description": "This is an updated test project",
    }
    response = client.put(
        f"{api_url}/project/{project_id}", headers=headers, json=updated_project_data
    )
    assert response.status_code == 200
    assert response.json()["name"] == updated_project_data["name"]


# Test Delete Project
def test_delete_project(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(f"{api_url}/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]
    response = client.delete(f"{api_url}/project/{project_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == project_data["name"]


# Test Get Project Files
def test_get_project_files(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(f"{api_url}/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]
    response = client.get(f"{api_url}/project/{project_id}/files", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 0  # No files uploaded yet


# Test Upload File
def test_upload_file(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}  # Removed Content-Type header
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(
        f"{api_url}/project/",
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
            f"{api_url}/project/{project_id}/file",
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
def test_get_project_file(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}  # Removed Content-Type header
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(
        f"{api_url}/project/",
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
        f"{api_url}/project/{project_id}/file", headers=headers, files=file_data
    )
    assert response.status_code == 200
    file_id = response.json()["id"]
    response = client.get(
        f"{api_url}/project/{project_id}/file/{file_id}", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["file_name"] == "test.txt"


# Test Delete File
def test_delete_file(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}  # Removed Content-Type header
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(
        f"{api_url}/project/",
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
        f"{api_url}/project/{project_id}/file", headers=headers, files=file_data
    )
    assert response.status_code == 200
    file_id = response.json()["id"]
    response = client.delete(
        f"{api_url}/project/{project_id}/file/{file_id}", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["file_name"] == "test.txt"


# Test Get Project File Content
def test_get_project_file_content(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}  # Removed Content-Type header
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(
        f"{api_url}/project/",
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
        f"{api_url}/project/{project_id}/file", headers=headers, files=file_data
    )
    assert response.status_code == 200
    file_id = response.json()["id"]
    response = client.get(
        f"{api_url}/project/{project_id}/file/{file_id}/content", headers=headers
    )
    assert response.status_code == 200
    assert response.content == b"Hello KatherLab!"


# Test Preprocess Project Data
@pytest.mark.parametrize(
    "use_ocr, file_name, expected_text",
    [
        (False, "9874562_text.pdf", None),
        (
            True,
            "9874562_notext.pdf",
            "Re: Medical History and Clinical Course of Patient Ashley Park",
        ),
    ],
)
def test_preprocess_project_data_v2(client, api_url, use_ocr, file_name, expected_text):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create a project
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(f"{api_url}/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]

    # Upload a file
    with open(f"files/{file_name}", "rb") as f:
        file_data = {
            "file": (file_name, f, "application/pdf"),
        }
        file_info = f'{{"file_name": "{file_name}", "file_type": "application/pdf"}}'
        response = client.post(
            f"{api_url}/project/{project_id}/file",
            headers=headers,
            files=file_data,
            data={"file_info": file_info},
        )
    assert response.status_code == 200
    file_id = response.json()["id"]

    # Preprocess the file
    preprocessing_data = {
        "file_ids": [file_id],
        "bypass_celery": True,
    }
    if use_ocr:
        preprocessing_data["use_ocr"] = True

    response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json=preprocessing_data,
    )
    assert response.status_code == 200
    preprocessing_task = response.json()

    # Check if the document is created
    response = client.get(f"{api_url}/project/{project_id}", headers=headers)
    assert response.status_code == 200
    project = response.json()
    assert len(project.get("documents", [])) == 1
    document = project["documents"][0]
    assert document["text"] is not None

    # Check the text content of the document
    if expected_text:
        assert expected_text in document["text"]

    response = client.get(
        f"{api_url}/project/{project_id}/file/{document['preprocessed_file_id']}/content",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.content is not None

    # Check the preprocessing task
    assert preprocessing_task["documents"] is not None
    assert len(preprocessing_task["documents"]) == 1
    assert preprocessing_task["documents"][0]["id"] == document["id"]

    # Check that the document linked to the preprocessing task is available in the project
    response = client.get(
        f"{api_url}/project/{project_id}/preprocess/{preprocessing_task['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    preprocessing_task = response.json()
    assert "documents" in preprocessing_task
    assert len(preprocessing_task["documents"]) == 1
    for doc in preprocessing_task.get("documents"):
        response = client.get(
            f"{api_url}/project/{project_id}/document/{doc['id']}", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["id"] == doc["id"]


# Test Create Project and check that another user can't access it
def test_project_access_control(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(f"{api_url}/project/", headers=headers, json=project_data)
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
    response = client.post(f"{api_url}/auth/login", data=admin_user_data)
    assert response.status_code == 200
    admin_access_token = response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_access_token}"}
    invitation_data = {"email": "another@example.com"}
    response = client.post(
        f"{api_url}/auth/invite", headers=admin_headers, data=invitation_data
    )
    assert response.status_code == 200
    invitation_token = response.json()["token"]
    another_user_create_data = {
        "email": "another@example.com",
        "full_name": "Another User",
        "password": "anotherpassword",
        "invitation_token": invitation_token,
    }
    response = client.post(f"{api_url}/auth/register", json=another_user_create_data)
    assert response.status_code == 200

    response = client.post(f"{api_url}/auth/login", data=another_user_data)
    assert response.status_code == 200
    another_access_token = response.json()["access_token"]
    another_headers = {"Authorization": f"Bearer {another_access_token}"}

    # Try to get the project as another user
    response = client.get(f"{api_url}/project/{project_id}", headers=another_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access this project"

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
    assert response.json()["detail"] == "Not authorized to update this project"

    # Try to delete the project as another user
    response = client.delete(f"{api_url}/project/{project_id}", headers=another_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to delete this project"


# Test Create Schema
def test_create_schema(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create a project
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(f"{api_url}/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]

    # Create a schema
    schema_data = {
        "schema_name": "Test Schema",
        "schema_definition": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "location": {"type": "string"},
            },
        },
    }
    response = client.post(
        f"{api_url}/project/{project_id}/schema", headers=headers, json=schema_data
    )
    assert response.status_code == 200
    schema = response.json()
    assert schema["schema_name"] == schema_data["schema_name"]
    assert schema["schema_definition"] == schema_data["schema_definition"]


# Test Get Schema
def test_get_schema(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create a project
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(f"{api_url}/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]

    # Create a schema
    schema_data = {
        "schema_name": "Test Schema",
        "schema_definition": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "location": {"type": "string"},
            },
        },
    }
    response = client.post(
        f"{api_url}/project/{project_id}/schema", headers=headers, json=schema_data
    )
    assert response.status_code == 200
    schema_id = response.json()["id"]

    # Get the schema
    response = client.get(
        f"{api_url}/project/{project_id}/schema/{schema_id}", headers=headers
    )
    assert response.status_code == 200
    schema = response.json()
    assert schema["schema_name"] == schema_data["schema_name"]
    assert schema["schema_definition"] == schema_data["schema_definition"]


# Test Delete Schema
def test_delete_schema(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create a project
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(f"{api_url}/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]

    # Create a schema
    schema_data = {
        "schema_name": "Test Schema",
        "schema_definition": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "location": {"type": "string"},
            },
        },
    }
    response = client.post(
        f"{api_url}/project/{project_id}/schema", headers=headers, json=schema_data
    )
    assert response.status_code == 200
    schema_id = response.json()["id"]

    # Delete the schema
    response = client.delete(
        f"{api_url}/project/{project_id}/schema/{schema_id}", headers=headers
    )
    assert response.status_code == 200

    # Try to get the deleted schema
    response = client.get(
        f"{api_url}/project/{project_id}/schema/{schema_id}", headers=headers
    )
    assert response.status_code == 404


# Test Delete Schema Referenced by Trial
def test_delete_schema_referenced_by_trial(client, api_url):
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create a project
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(f"{api_url}/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]

    # Create a schema
    schema_data = {
        "schema_name": "Test Schema",
        "schema_definition": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "location": {"type": "string"},
            },
        },
    }
    response = client.post(
        f"{api_url}/project/{project_id}/schema", headers=headers, json=schema_data
    )
    assert response.status_code == 200
    schema_id = response.json()["id"]

    # Create a trial
    trial_data = {
        "schema_id": schema_id,
        "document_ids": [],
        "bypass_celery": True,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/trials", headers=headers, json=trial_data
    )
    assert response.status_code == 200

    # Try to delete the schema
    response = client.delete(
        f"{api_url}/project/{project_id}/schema/{schema_id}", headers=headers
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot delete schema referenced by a trial"


# Test Get Available LLM Models
def test_get_available_llm_models(client, api_url):
    if settings.OPENAI_NO_API_CHECK:
        pytest.skip("Skipping LLM models test due to OPENAI_NO_API_CHECK setting")  # type: ignore
    response = client.get(f"{api_url}/project/llm/models")
    assert response.status_code == 200
    assert len(response.json()) > 0


# Test Test LLM Connection
def test_test_llm_connection(client, api_url):
    if settings.OPENAI_NO_API_CHECK:
        pytest.skip("Skipping LLM models test due to OPENAI_NO_API_CHECK setting")  # type: ignore
    response = client.post(f"{api_url}/project/llm/test")
    assert response.status_code == 200
    assert response.json() is True


# Test Create Trial with Preprocessing and Extract Information
def test_create_trial_with_preprocessing_and_extract_information(client, api_url):
    if settings.OPENAI_NO_API_CHECK:
        pytest.skip("Skipping LLM models test due to OPENAI_NO_API_CHECK setting")  # type: ignore
    user_data = {
        "username": "test@example.com",
        "password": "testpassword",
    }
    response = client.post(f"{api_url}/auth/login", data=user_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create a project
    project_data = {
        "name": "Test Project",
        "description": "This is a test project",
    }
    response = client.post(f"{api_url}/project/", headers=headers, json=project_data)
    assert response.status_code == 200
    project_id = response.json()["id"]

    # Upload a file
    with open("files/9874562_text.pdf", "rb") as f:
        file_data = {
            "file": ("9874562_text.pdf", f, "application/pdf"),
        }
        file_info = '{"file_name": "9874562_text.pdf", "file_type": "application/pdf"}'
        response = client.post(
            f"{api_url}/project/{project_id}/file",
            headers=headers,
            files=file_data,
            data={"file_info": file_info},
        )
    assert response.status_code == 200
    file_id = response.json()["id"]

    # Preprocess the file
    preprocessing_data = {
        "file_ids": [file_id],
        "bypass_celery": True,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json=preprocessing_data,
    )
    assert response.status_code == 200
    preprocessing_task = response.json()
    document_id = preprocessing_task["documents"][0]["id"]

    # Create a schema
    schema_data = {
        "schema_name": "Test Schema",
        "schema_definition": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "location": {"type": "string"},
            },
        },
    }
    response = client.post(
        f"{api_url}/project/{project_id}/schema", headers=headers, json=schema_data
    )
    assert response.status_code == 200
    schema_id = response.json()["id"]

    # Create a trial
    trial_data = {
        "schema_id": schema_id,
        "document_ids": [document_id],
        "bypass_celery": True,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/trials", headers=headers, json=trial_data
    )
    assert response.status_code == 200
    trial_id = response.json()["id"]

    # Check the trial result
    response = client.get(
        f"{api_url}/project/{project_id}/trials/{trial_id}", headers=headers
    )

    print(response.json())
    assert response.status_code == 200
    trial_result = response.json()
    assert trial_result["status"] == "completed"

    # Validate the extracted JSON against the schema
    extracted_json = trial_result["results"][0]["result"]
    schema = schema_data["schema_definition"]
    try:
        jsonschema.validate(instance=extracted_json, schema=schema)
    except jsonschema.ValidationError as e:
        assert False, f"Extracted JSON is not valid according to the schema: {e}"
