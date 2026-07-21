# backend/tests/test_files.py
"""Tests for the basic per-file CRUD endpoints under a project's /file route.

Covers listing an empty project's files, uploading a file (disk PDF and inline
bytes), fetching a single file's metadata, deleting a file, and downloading a
file's raw content. Complements the batch-ops suite in
``test_file_batch_ops.py`` (batch-delete / move), which exercises the bulk
paths.
"""


# Test Get Project Files
def test_get_project_files(client, api_url, user_headers, make_project):
    project_id = make_project(user_headers)["id"]
    response = client.get(f"{api_url}/project/{project_id}/file", headers=user_headers)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["total"] == 0  # No files uploaded yet
    assert response_data["items"] == []


# Test Upload File
def test_upload_file(
    client, api_url, files_base_path, user_headers, make_project, upload_file
):
    project_id = make_project(user_headers)["id"]
    response_json = upload_file(
        user_headers,
        project_id,
        path=files_base_path / "9874562_text.pdf",
        content_type="application/pdf",
    )
    assert "id" in response_json
    assert "file_name" in response_json
    assert "file_type" in response_json
    assert response_json["file_name"] == "9874562_text.pdf"
    assert response_json["file_type"] == "application/pdf"


# Test Get Project File
def test_get_project_file(client, api_url, user_headers, make_project, upload_file):
    project_id = make_project(user_headers)["id"]
    file_id = upload_file(
        user_headers, project_id, content=b"Hello World!", name="test.txt"
    )["id"]
    response = client.get(
        f"{api_url}/project/{project_id}/file/{file_id}", headers=user_headers
    )
    assert response.status_code == 200
    assert response.json()["file_name"] == "test.txt"


# Test Delete File
def test_delete_file(client, api_url, user_headers, make_project, upload_file):
    project_id = make_project(user_headers)["id"]
    file_id = upload_file(
        user_headers, project_id, content=b"Hello World!", name="test.txt"
    )["id"]
    response = client.delete(
        f"{api_url}/project/{project_id}/file/{file_id}", headers=user_headers
    )
    assert response.status_code == 200
    assert response.json()["file_name"] == "test.txt"


# Test Get Project File Content
def test_get_project_file_content(
    client, api_url, user_headers, make_project, upload_file
):
    project_id = make_project(user_headers)["id"]
    file_id = upload_file(
        user_headers, project_id, content=b"Hello KatherLab!", name="test.txt"
    )["id"]
    response = client.get(
        f"{api_url}/project/{project_id}/file/{file_id}/content", headers=user_headers
    )
    assert response.status_code == 200
    assert response.content == b"Hello KatherLab!"
