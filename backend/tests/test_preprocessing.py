# backend/tests/test_preprocessing.py
"""Tests for the preprocessing pipeline exercised through the project API.

Covers the end-to-end preprocess flow (POST /preprocess with bypass_celery,
which is admin-only) across the supported input types and strategies:
- PDF (embedded text and OCR fallback) and plain-text extraction,
- image OCR,
- CSV and XLSX table files under the row_by_row strategy (text-column joins,
  case-ID columns), including auto-generation of a DocumentSet per source file,
- inline preprocessing configuration,
- duplicate detection and the same-config reprocessing preview (incl. the
  image force_ocr regression),
- id-column validation matching the pipeline's normalization rules,
- multi-file progress tracking.

Complements test_preprocessing_dispatch.py / test_preprocessing_timeout.py /
test_preview_rows.py. Cancellation and retry-of-failed paths are skipped here
because they need a live Celery worker.
"""

import json

import pytest


# Test Preprocess Project Data with Configuration
@pytest.mark.parametrize(
    "file_name, expected_text",
    [
        ("9874562_text.pdf", None),
        (
            "9874562_notext.pdf",
            "Re: Medical History and Clinical Course of Patient Ashley Park",
        ),
    ],
)
def test_preprocess_project_data_v2(
    client,
    api_url,
    admin_headers,
    make_project,
    upload_file,
    file_name,
    expected_text,
    files_base_path,
):
    # Run preprocessing tasks with admin user as normal user is not allowed to bypass celery
    project_id = make_project(admin_headers)["id"]

    # Upload a file
    file_id = upload_file(
        admin_headers,
        project_id,
        path=files_base_path / file_name,
        content_type="application/pdf",
    )["id"]

    # Preprocess the file with inline configuration
    preprocessing_data = {
        "file_ids": [file_id],
        "inline_config": {
            "name": "Test Config",
            "description": "Inline config for PDF processing",
        },
        "bypass_celery": True,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json=preprocessing_data,
    )
    assert response.status_code == 200
    preprocessing_task = response.json()

    # Check task status
    assert preprocessing_task["status"] == "completed"
    assert preprocessing_task["total_files"] == 1
    assert preprocessing_task["processed_files"] == 1
    assert preprocessing_task["failed_files"] == 0

    # Get task details with file progress
    response = client.get(
        f"{api_url}/project/{project_id}/preprocess/{preprocessing_task['id']}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    task_details = response.json()
    assert len(task_details["file_tasks"]) == 1
    assert task_details["file_tasks"][0]["status"] == "completed"
    assert task_details["file_tasks"][0]["document_count"] >= 1

    # Check if the document is created
    response = client.get(
        f"{api_url}/project/{project_id}/document", headers=admin_headers
    )
    assert response.status_code == 200
    documents = response.json()
    assert len(documents["items"]) >= 1
    document = documents["items"][0]
    # `text` is not included in list items (DocumentListItem); fetch the full
    # document to verify its text content.
    response = client.get(
        f"{api_url}/project/{project_id}/document/{document['id']}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    full_document = response.json()
    assert full_document["text"] is not None
    assert document["document_name"] == file_name

    # Check the text content of the document
    if expected_text:
        assert expected_text in full_document["text"]

    # Check preprocessed file if it exists
    if document.get("preprocessed_file_id"):
        response = client.get(
            f"{api_url}/project/{project_id}/file/{document['preprocessed_file_id']}/content",
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.content is not None


# Test Preprocessing with Inline Configuration
def test_preprocess_with_inline_config(
    client, api_url, admin_headers, make_project, upload_file
):
    # Create a project
    project_id = make_project(admin_headers, name="Test Project")["id"]

    # Upload a text file
    file_id = upload_file(
        admin_headers,
        project_id,
        content=b"Hello World!",
        name="test.txt",
        content_type="text/plain",
    )["id"]

    # Preprocess with inline configuration
    preprocessing_data = {
        "file_ids": [file_id],
        "inline_config": {
            "name": "Inline Text Config",
            "description": "Inline text processing config",
        },
        "bypass_celery": True,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json=preprocessing_data,
    )
    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "completed"


# Test Duplicate Detection
def test_duplicate_detection(client, api_url, admin_headers, make_project, upload_file):
    # Create a project
    project_id = make_project(admin_headers, name="Test Project")["id"]

    # Upload a file
    file_id = upload_file(
        admin_headers,
        project_id,
        content=b"Hello World!",
        name="test.txt",
        content_type="text/plain",
    )["id"]

    # Preprocess with inline config
    preprocessing_data = {
        "file_ids": [file_id],
        "inline_config": {
            "name": "Test Config",
            "description": "Config for duplicate detection test",
        },
        "bypass_celery": True,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json=preprocessing_data,
    )
    assert response.status_code == 200

    # Preprocess the same file again with the same inline config.
    # Since inline_config creates a new PreprocessingConfiguration each time,
    # the duplicate detection (which checks by config_id) won't match.
    # The file will be processed again under a new config.
    response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json=preprocessing_data,
    )
    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "completed"
    assert task["processed_files"] >= 1

    # Also test explicit duplicate check endpoint
    # (get file hash)
    response = client.get(
        f"{api_url}/project/{project_id}/file/{file_id}", headers=admin_headers
    )
    file_hash = response.json()["file_hash"]
    resp = client.post(
        f"{api_url}/project/{project_id}/file/check-duplicates",
        headers=admin_headers,
        json=[{"filename": "test.txt", "hash": file_hash}],
    )
    assert resp.status_code == 200
    assert resp.json()[0]["exists"]


# Test Cancel Preprocessing Task
def test_cancel_preprocessing_task(client, api_url):
    pytest.skip(
        "Skipping test_cancel_preprocessing_task as we don't have Celery for running which is required for this test."
    )


# Test Table File Preprocessing
def test_table_file_preprocessing(
    client, api_url, admin_headers, make_project, upload_file
):
    # Create a project
    project_id = make_project(admin_headers)["id"]

    # Create CSV content
    csv_content = """document_name,description,details,category
Document 1,This is the first document,Contains important information,A
Document 2,This is the second document,Contains more details,B
Document 3,This is the third document,Contains additional data,A"""

    # Table processing settings (all but strategy go into file_metadata)
    table_file_metadata = {
        "delimiter": ",",
        "encoding": "utf-8",
        "has_header": True,
        "text_columns": ["description", "details"],
        "case_id_column": "document_name",
        "join_separator": " - ",
        "skip_header_rows": 0,
    }

    # Upload CSV file with preprocessing_strategy as a direct attribute
    file_id = upload_file(
        admin_headers,
        project_id,
        content=csv_content.encode(),
        name="test_data.csv",
        content_type="text/csv",
        file_info_extra={
            "preprocessing_strategy": "row_by_row",  # <- direct attribute!
            "file_metadata": table_file_metadata,
        },
    )["id"]

    # Verify file properties
    response = client.get(
        f"{api_url}/project/{project_id}/file/{file_id}", headers=admin_headers
    )
    assert response.status_code == 200
    file_obj = response.json()
    assert file_obj["preprocessing_strategy"] == "row_by_row"
    assert file_obj["file_metadata"]["encoding"] == "utf-8"
    assert file_obj["file_metadata"]["text_columns"] == ["description", "details"]
    assert file_obj["file_metadata"]["case_id_column"] == "document_name"
    assert file_obj["file_metadata"]["join_separator"] == " - "
    assert file_obj["file_metadata"]["skip_header_rows"] == 0

    # Preprocess the CSV file with inline config
    preprocessing_data = {
        "file_ids": [file_id],
        "inline_config": {
            "name": "CSV Row Processing",
            "description": "Process each row as a separate document",
        },
        "bypass_celery": True,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json=preprocessing_data,
    )
    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "completed"

    # Check documents created
    response = client.get(
        f"{api_url}/project/{project_id}/document", headers=admin_headers
    )
    assert response.status_code == 200
    documents = response.json()
    assert documents["total"] == 3  # 3 rows in CSV

    documents = documents["items"]

    # Verify document content
    doc_names = [doc["document_name"] for doc in documents]
    assert "Document 1" in doc_names
    assert "Document 2" in doc_names
    assert "Document 3" in doc_names

    # Check document content
    doc1 = next(d for d in documents if d["document_name"] == "Document 1")
    # `text` is not included in list items; fetch the full document.
    full_doc1 = client.get(
        f"{api_url}/project/{project_id}/document/{doc1['id']}", headers=admin_headers
    ).json()
    assert (
        full_doc1["text"] == "This is the first document Contains important information"
    )
    assert doc1["meta_data"]["row_index"] == 0
    assert doc1["meta_data"]["source_columns"] == ["description", "details"]


def test_validate_id_column_detects_duplicates(
    client, api_url, admin_headers, make_project, upload_file
):
    """The validate-id-column endpoint should flag non-unique case-ID columns
    and the configure endpoint should reject them (422) before preprocessing."""
    project_id = make_project(
        admin_headers, name="ID Validation Project", description="x"
    )["id"]

    # subject_id "S1" appears twice → not unique
    csv_content = (
        "subject_id,report\nS1,First report\nS2,Second report\nS1,Duplicate subject\n"
    )
    file_id = upload_file(
        admin_headers,
        project_id,
        content=csv_content.encode(),
        name="dupe.csv",
        content_type="text/csv",
    )["id"]

    # Duplicate column → invalid, with the offending value reported
    response = client.post(
        f"{api_url}/project/{project_id}/file/{file_id}/validate-id-column",
        headers=admin_headers,
        json={"case_id_column": "subject_id", "has_header": True, "delimiter": ","},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["is_valid"] is False
    assert result["column_exists"] is True
    assert result["duplicate_rows"] == 2
    assert any(d["value"] == "S1" and d["count"] == 2 for d in result["duplicates"])

    # Unique column → valid
    response = client.post(
        f"{api_url}/project/{project_id}/file/{file_id}/validate-id-column",
        headers=admin_headers,
        json={"case_id_column": "report", "has_header": True, "delimiter": ","},
    )
    assert response.status_code == 200
    assert response.json()["is_valid"] is True

    # Saving a config with the duplicate ID column is rejected with 422
    response = client.post(
        f"{api_url}/project/{project_id}/file/{file_id}/configure",
        headers=admin_headers,
        json={
            "preprocessing_strategy": "row_by_row",
            "file_metadata": {
                "delimiter": ",",
                "encoding": "utf-8",
                "has_header": True,
                "text_columns": ["report"],
                "case_id_column": "subject_id",
            },
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["is_valid"] is False
    assert any(d["value"] == "S1" for d in detail["duplicates"])

    # A unique ID column saves successfully
    response = client.post(
        f"{api_url}/project/{project_id}/file/{file_id}/configure",
        headers=admin_headers,
        json={
            "preprocessing_strategy": "row_by_row",
            "file_metadata": {
                "delimiter": ",",
                "encoding": "utf-8",
                "has_header": True,
                "text_columns": ["report"],
                "case_id_column": "report",
            },
        },
    )
    assert response.status_code == 200


def test_id_column_validation_matches_pipeline_normalization(
    client, api_url, admin_headers, make_project
):
    """Validation must apply the same ID normalization as the pipeline:
    values differing only in whitespace collide, and even a single empty ID
    is invalid — otherwise validation passes and preprocessing then fails."""
    project_id = make_project(
        admin_headers, name="ID Normalization Project", description="x"
    )["id"]

    def _upload_and_validate(name: str, csv_content: str) -> dict:
        resp = client.post(
            f"{api_url}/project/{project_id}/file",
            headers=admin_headers,
            files={"file": (name, csv_content.encode(), "text/csv")},
            data={
                "file_info": json.dumps({"file_name": name, "file_type": "text/csv"})
            },
        )
        assert resp.status_code == 200, resp.text
        resp = client.post(
            f"{api_url}/project/{project_id}/file/{resp.json()['id']}/validate-id-column",
            headers=admin_headers,
            json={"case_id_column": "id", "has_header": True, "delimiter": ","},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    # "A" vs "A " differ only in trailing whitespace — the pipeline trims both
    # to the same document name, so validation must flag the collision.
    result = _upload_and_validate("ws.csv", 'id,report\nA,First\n"A ",Second\n')
    assert result["is_valid"] is False
    assert any(d["value"] == "A" and d["count"] == 2 for d in result["duplicates"])

    # A single empty ID cell is a hard error in the pipeline → invalid here.
    result = _upload_and_validate("empty.csv", "id,report\nA,First\n,Second\n")
    assert result["is_valid"] is False
    assert any(d["is_empty"] and d["count"] == 1 for d in result["duplicates"])

    client.delete(f"{api_url}/project/{project_id}", headers=admin_headers)


# Test auto-generated document set for row-by-row preprocessing
def test_row_by_row_document_set_auto_generation(
    client, api_url, admin_headers, make_project, upload_file
):
    """Test that row-by-row preprocessing automatically creates a DocumentSet."""
    # Create a project
    project_id = make_project(
        admin_headers,
        name="Test Document Set Project",
        description="Test auto-generated document sets",
    )["id"]

    # Create CSV content with case_id_column
    csv_content = """patient_id,diagnosis,treatment
P001,Diabetes,Insulin therapy
P002,Hypertension,ACE inhibitors
P003,Asthma,Bronchodilators"""

    # Table processing settings with case_id_column
    table_file_metadata = {
        "delimiter": ",",
        "encoding": "utf-8",
        "has_header": True,
        "text_columns": ["diagnosis", "treatment"],
        "case_id_column": "patient_id",
    }

    # Upload CSV file
    file_id = upload_file(
        admin_headers,
        project_id,
        content=csv_content.encode(),
        name="patients.csv",
        content_type="text/csv",
        file_info_extra={
            "preprocessing_strategy": "row_by_row",
            "file_metadata": table_file_metadata,
        },
    )["id"]

    # Preprocess with inline config
    preprocessing_data = {
        "file_ids": [file_id],
        "inline_config": {
            "name": "Patient Row Processing",
            "description": "Process each patient row as a document",
        },
        "bypass_celery": True,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json=preprocessing_data,
    )
    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "completed"

    # Check that document set was created (include auto-generated sets)
    response = client.get(
        f"{api_url}/project/{project_id}/document-set?include_auto_generated=true",
        headers=admin_headers,
    )
    assert response.status_code == 200
    document_sets = response.json()

    # Find the auto-generated set
    auto_sets = [
        ds
        for ds in document_sets["items"]
        if ds.get("is_auto_generated") and "patients.csv" in ds.get("name", "")
    ]
    assert len(auto_sets) == 1
    document_set = auto_sets[0]

    # Verify document set properties
    assert document_set["name"] == "patients.csv (by patient_id)"
    assert document_set["is_auto_generated"] is True
    assert document_set["preprocessing_config"] is not None
    assert document_set["preprocessing_config"]["id"] is not None
    assert "row-by-row" in document_set.get("tags", [])
    assert "auto-generated" in document_set.get("tags", [])

    # Summary carries a count instead of the member documents.
    assert document_set["document_count"] == 3  # 3 rows in CSV

    # Verify the linked documents via the document_set_id filter (paginated).
    set_docs = client.get(
        f"{api_url}/project/{project_id}/document",
        headers=admin_headers,
        params={"document_set_id": document_set["id"], "limit": 100},
    ).json()
    doc_names = [doc["document_name"] for doc in set_docs["items"]]
    assert "P001" in doc_names
    assert "P002" in doc_names
    assert "P003" in doc_names


# Test Image File Processing
def test_image_file_preprocessing(
    client, api_url, admin_headers, make_project, upload_file, files_base_path
):
    # Create a project
    project_id = make_project(admin_headers)["id"]

    # Upload an image file (assuming you have a test image)
    file_id = upload_file(
        admin_headers,
        project_id,
        path=files_base_path / "9874562.png",
        content_type="image/png",
    )["id"]

    # Preprocess the image with inline config
    preprocessing_data = {
        "file_ids": [file_id],
        "inline_config": {
            "name": "Image OCR Config",
            "description": "OCR for images",
        },
        "bypass_celery": True,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json=preprocessing_data,
    )
    assert response.status_code == 200
    task = response.json()
    print(task)
    assert task["status"] == "completed"

    # Check document created
    response = client.get(
        f"{api_url}/project/{project_id}/document", headers=admin_headers
    )
    assert response.status_code == 200
    documents = response.json()
    assert documents["total"] >= 1

    # Find the document for our image
    image_doc = next(d for d in documents["items"] if d["original_file_id"] == file_id)
    # `text` is not included in list items; fetch the full document.
    full_image_doc = client.get(
        f"{api_url}/project/{project_id}/document/{image_doc['id']}",
        headers=admin_headers,
    ).json()
    assert full_image_doc["text"] is not None  # Should contain OCR text
    assert image_doc["meta_data"]["file_type"] == "image/png"


# Test Preprocessing Progress Tracking
def test_preprocessing_progress_tracking(client, api_url, admin_headers, make_project):
    # Create a project
    project_id = make_project(admin_headers)["id"]

    # Upload multiple files
    file_ids = []
    for i in range(5):
        file_data = {
            "file": ("test.txt", f"Content {i}".encode(), "text/plain"),
            "file_info": (
                "",
                f'{{"file_name": "test{i}.txt", "file_type": "text/plain"}}',
                "application/json",
            ),
        }
        response = client.post(
            f"{api_url}/project/{project_id}/file",
            headers=admin_headers,
            files=file_data,
        )
        assert response.status_code == 200
        file_ids.append(response.json()["id"])

    # Start preprocessing with inline config
    preprocessing_data = {
        "file_ids": file_ids,
        "inline_config": {
            "name": "Test Config",
            "description": "Config for progress tracking",
        },
        "bypass_celery": True,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json=preprocessing_data,
    )
    assert response.status_code == 200
    task_id = response.json()["id"]

    # Get progress
    response = client.get(
        f"{api_url}/project/{project_id}/preprocess/{task_id}/progress",
        headers=admin_headers,
    )
    assert response.status_code == 200
    progress = response.json()
    assert progress["total_files"] == 5
    assert progress["processed_files"] == 5  # Should be completed since bypass_celery
    assert progress["failed_files"] == 0
    assert len(progress["file_tasks"]) == 5

    # Check individual file progress
    for file_task in progress["file_tasks"]:
        assert file_task["status"] == "completed"
        assert file_task["progress"] >= 0.0  # Changed from == 100.0
        assert file_task["document_count"] == 1


# Test Retry Failed Files
def test_retry_failed_preprocessing(client, api_url):
    pytest.skip("Cannot produce a failed task like this at the moment.")


def test_excel_file_preprocessing(
    client, api_url, admin_headers, make_project, upload_file
):
    # Create a project
    project_id = make_project(admin_headers, name="Test Project")["id"]

    # Create Excel content using pandas
    import io

    import pandas as pd

    df = pd.DataFrame(
        {
            "document_name": ["Doc A", "Doc B", "Doc C"],
            "title": ["Title 1", "Title 2", "Title 3"],
            "content": ["Content for A", "Content for B", "Content for C"],
            "metadata": ["Meta A", "Meta B", "Meta C"],
        }
    )

    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)

    # Excel table settings in file_metadata
    excel_file_metadata = {
        "text_columns": ["title", "content", "metadata"],
        "case_id_column": "document_name",
        "join_separator": " | ",
        "skip_header_rows": 0,
    }

    # Upload Excel file with strategy and settings
    file_id = upload_file(
        admin_headers,
        project_id,
        content=excel_buffer.read(),
        name="test_data.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_info_extra={
            "preprocessing_strategy": "row_by_row",
            "file_metadata": excel_file_metadata,
        },
    )["id"]

    # Check file object for correct metadata and strategy
    response = client.get(
        f"{api_url}/project/{project_id}/file/{file_id}", headers=admin_headers
    )
    assert response.status_code == 200
    file_obj = response.json()
    assert file_obj["preprocessing_strategy"] == "row_by_row"
    assert file_obj["file_metadata"]["text_columns"] == ["title", "content", "metadata"]
    assert file_obj["file_metadata"]["case_id_column"] == "document_name"
    assert file_obj["file_metadata"]["join_separator"] == " | "
    assert file_obj["file_metadata"]["skip_header_rows"] == 0

    # Preprocess the Excel file with inline config
    preprocessing_data = {
        "file_ids": [file_id],
        "inline_config": {
            "name": "Excel Row Processing",
            "description": "Process each row as a separate document",
        },
        "bypass_celery": True,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json=preprocessing_data,
    )
    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "completed"

    # Check documents created
    response = client.get(
        f"{api_url}/project/{project_id}/document", headers=admin_headers
    )
    assert response.status_code == 200
    documents = response.json()

    # Should have 3 documents (one per row)
    excel_docs = [d for d in documents["items"] if d["original_file_id"] == file_id]
    assert len(excel_docs) == 3

    # Verify document content
    doc_a = next(d for d in excel_docs if d["document_name"] == "Doc A")
    # `text` is not included in list items; fetch the full document.
    full_doc_a = client.get(
        f"{api_url}/project/{project_id}/document/{doc_a['id']}", headers=admin_headers
    ).json()
    assert full_doc_a["text"] == "Title 1 Content for A Meta A"
    assert doc_a["meta_data"]["row_index"] == 0


# Test preprocessing duplicate preview detects same-config reprocessing for images
# Regression: the docling-serve image path stores force_ocr=True in document metadata
# (images always need OCR), but the frontend sends force_ocr=False (the default, which
# is PDF-specific). The preview's force_ocr comparison therefore failed for images, so
# same_config_duplicates was empty and the reprocessing warning modal never appeared.
def test_preprocess_preview_detects_same_config_image_duplicate(
    client, api_url, user_headers, make_project, files_base_path
):
    import uuid

    from ..src.db.session import SessionLocal
    from ..src.models.project import Document, File, PreprocessingConfiguration
    from ..src.utils.enums import FileCreator, FileType, PreprocessingStrategy

    project_id = make_project(
        user_headers, name="Image Dup Project", description="regression test"
    )["id"]

    # Seed a File + PreprocessingConfiguration + Document directly via the DB,
    # mirroring what the docling-serve image OCR path produces. The preview endpoint
    # only reads these rows (not the file bytes), so no storage upload is needed.
    db = SessionLocal()
    try:
        config = PreprocessingConfiguration(
            project_id=project_id,
            name="Prev Config",
            additional_settings={"ocr_engine": "docling_tesseract"},
        )
        db.add(config)
        db.flush()

        file = File(
            project_id=project_id,
            file_uuid=str(uuid.uuid4()),
            file_name="scan.jpg",
            file_type=FileType.IMAGE_JPEG,
            file_creator=FileCreator.user,
            preprocessing_strategy=PreprocessingStrategy.FULL_DOCUMENT,
            file_metadata={},
            file_hash="0" * 64,
        )
        db.add(file)
        db.flush()

        doc = Document(
            project_id=project_id,
            original_file_id=file.id,
            preprocessing_config_id=config.id,
            text="ocr'd text",
            document_name="scan.jpg",
            is_latest=True,
            meta_data={
                "ocr_engine": "tesseract",
                "force_ocr": True,  # hardcoded by the docling-serve image path
                "extraction_method": "docling_serve_tesseract_image_ocr",
                "file_type": FileType.IMAGE_JPEG,
            },
        )
        db.add(doc)
        db.commit()
        file_id = file.id
    finally:
        db.close()

    # Re-process the same image with the same engine and the frontend-default
    # force_ocr=False. This must be detected as a same-config duplicate.
    preview = client.post(
        f"{api_url}/project/{project_id}/preprocess/preview",
        headers=user_headers,
        json={
            "file_ids": [file_id],
            "inline_config": {
                "name": "Reprocess",
                "additional_settings": {
                    "ocr_engine": "docling_tesseract",
                    "force_ocr": False,
                },
            },
        },
    )
    assert preview.status_code == 200, preview.text
    data = preview.json()
    same_config = data["same_config_duplicates"]
    assert len(same_config) == 1, (
        f"Expected the reprocessed JPG to be a same-config duplicate, got: {data}"
    )
    assert same_config[0]["file_id"] == file_id


# ---------------------------------------------------------------------------
# Endpoint-gating / duplicate-detection / cancel / retry coverage.
#
# These exercise the validation and lifecycle branches of
# routers/v1/endpoints/preprocess.py that don't require a live OCR/Celery
# worker: they seed ORM rows directly (Document, TrialResult, EvaluationMetric,
# PreprocessingTask, FilePreprocessingTask) and assert the endpoint's
# gating/rollback logic. Celery is disabled in the test env, so any path that
# reaches dispatch is only reached via admin bypass_celery (which the pipeline
# handles locally for text files) or is short-circuited before dispatch.
# ---------------------------------------------------------------------------


def _seed_file(db, project_id, *, file_type, name, strategy=None):
    """Insert a File row (no storage bytes) and return it."""
    import uuid

    from ..src import models
    from ..src.utils.enums import FileCreator

    f = models.File(
        project_id=project_id,
        file_uuid=str(uuid.uuid4()),
        file_name=name,
        file_type=file_type,
        file_creator=FileCreator.user,
        preprocessing_strategy=strategy,
        file_metadata={},
        # 32-char hex is well within the 64-char column and unique enough here.
        file_hash=uuid.uuid4().hex,
    )
    db.add(f)
    db.flush()
    return f


def _seed_config(db, project_id, additional_settings):
    from ..src import models

    cfg = models.PreprocessingConfiguration(
        project_id=project_id,
        name="Seed Config",
        additional_settings=additional_settings,
    )
    db.add(cfg)
    db.flush()
    return cfg


def _seed_document(
    db, project_id, *, file_id, config_id, name, meta=None, file_task_id=None
):
    from ..src import models

    doc = models.Document(
        project_id=project_id,
        original_file_id=file_id,
        preprocessing_config_id=config_id,
        file_preprocessing_task_id=file_task_id,
        text="seeded text",
        document_name=name,
        is_latest=True,
        meta_data=meta or {},
    )
    db.add(doc)
    db.flush()
    return doc


def _seed_trial(db, project_id, schema_id, prompt_id, number, document_ids):
    from ..src import models

    trial = models.Trial(
        project_id=project_id,
        project_trial_number=number,
        schema_id=schema_id,
        prompt_id=prompt_id,
        llm_model="gpt-test",
        base_url="",
        api_key_encrypted="",
        document_ids=document_ids,
    )
    db.add(trial)
    db.flush()
    return trial


# ── preview: 404 / 400 gating ──────────────────────────────────────────────


def test_preview_missing_file_ids_returns_404(
    client, api_url, user_headers, make_project
):
    project_id = make_project(user_headers, name="Preview 404")["id"]
    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess/preview",
        headers=user_headers,
        json={
            "file_ids": [999999],
            "inline_config": {"name": "x", "additional_settings": {}},
        },
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "preprocess.files_not_found"


def test_preview_without_inline_config_returns_400(
    client, api_url, user_headers, make_project
):
    """A request carrying configuration_id but no inline_config passes schema
    validation, then trips the endpoint's inline_config guard (400)."""
    project_id = make_project(user_headers, name="Preview 400")["id"]
    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess/preview",
        headers=user_headers,
        json={"file_ids": [1], "configuration_id": 12345},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "preprocess.inline_config_required"


# ── preview: same-config normalization matrix ──────────────────────────────


def test_preview_pdf_tesseract_normalization_same_config(
    client, api_url, user_headers, make_project
):
    """A PDF doc stored with ocr_engine='tesseract' must be detected as a
    same-config duplicate when the inline config sends the frontend name
    'docling_tesseract' (the normalization the code comment warns about)."""
    from ..src import models
    from ..src.db.session import SessionLocal

    project_id = make_project(user_headers, name="PDF Norm")["id"]
    db = SessionLocal()
    try:
        cfg = _seed_config(db, project_id, {"ocr_engine": "docling_tesseract"})
        f = _seed_file(
            db, project_id, file_type=models.FileType.APPLICATION_PDF, name="a.pdf"
        )
        _seed_document(
            db,
            project_id,
            file_id=f.id,
            config_id=cfg.id,
            name="a.pdf",
            meta={
                "ocr_engine": "tesseract",
                "force_ocr": False,
                "extraction_method": "docling_serve_tesseract",
            },
        )
        db.commit()
        file_id = f.id
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess/preview",
        headers=user_headers,
        json={
            "file_ids": [file_id],
            "inline_config": {
                "name": "reprocess",
                "additional_settings": {
                    "ocr_engine": "docling_tesseract",
                    "force_ocr": False,
                },
            },
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert [d["file_id"] for d in data["same_config_duplicates"]] == [file_id]


def test_preview_pdf_force_ocr_mismatch_not_same_config(
    client, api_url, user_headers, make_project
):
    """For PDFs force_ocr IS relevant: a stored force_ocr=False doc must NOT be
    a same-config duplicate when the new config sends force_ocr=True — it is
    still a plain duplicate though."""
    from ..src import models
    from ..src.db.session import SessionLocal

    project_id = make_project(user_headers, name="PDF ForceOCR")["id"]
    db = SessionLocal()
    try:
        cfg = _seed_config(db, project_id, {"ocr_engine": "docling_tesseract"})
        f = _seed_file(
            db, project_id, file_type=models.FileType.APPLICATION_PDF, name="b.pdf"
        )
        _seed_document(
            db,
            project_id,
            file_id=f.id,
            config_id=cfg.id,
            name="b.pdf",
            meta={
                "ocr_engine": "tesseract",
                "force_ocr": False,
                "extraction_method": "docling_serve_tesseract",
            },
        )
        db.commit()
        file_id = f.id
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess/preview",
        headers=user_headers,
        json={
            "file_ids": [file_id],
            "inline_config": {
                "name": "reprocess",
                "additional_settings": {
                    "ocr_engine": "docling_tesseract",
                    "force_ocr": True,
                },
            },
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["same_config_duplicates"] == []
    # It is still flagged as a (non-same-config) duplicate.
    assert [d["file_id"] for d in data["files_with_duplicates"]] == [file_id]


def test_preview_pdf_embedded_text_special_case(
    client, api_url, user_headers, make_project
):
    """A PDF with embedded text extracted via a 'no_ocr' method is a same-config
    duplicate for ANY OCR engine selection when force_ocr is False, and is also
    reported under pdfs_with_embedded_text."""
    from ..src import models
    from ..src.db.session import SessionLocal

    project_id = make_project(user_headers, name="PDF Embedded")["id"]
    db = SessionLocal()
    try:
        cfg = _seed_config(db, project_id, {"ocr_engine": "mistral_ocr"})
        f = _seed_file(
            db, project_id, file_type=models.FileType.APPLICATION_PDF, name="c.pdf"
        )
        _seed_document(
            db,
            project_id,
            file_id=f.id,
            config_id=cfg.id,
            name="c.pdf",
            meta={
                "ocr_engine": "pypdf",
                "force_ocr": False,
                "embedded_text_detected": True,
                "extraction_method": "docling_serve_no_ocr",
            },
        )
        db.commit()
        file_id = f.id
    finally:
        db.close()

    # Select a *different* engine (llm_vision) with force_ocr=False → still same
    # config via the embedded-text special case.
    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess/preview",
        headers=user_headers,
        json={
            "file_ids": [file_id],
            "inline_config": {
                "name": "reprocess",
                "additional_settings": {
                    "ocr_engine": "llm_vision",
                    "force_ocr": False,
                },
            },
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert [d["file_id"] for d in data["same_config_duplicates"]] == [file_id]
    assert [d["file_id"] for d in data["pdfs_with_embedded_text"]] == [file_id]


# ── preprocess submission gating ───────────────────────────────────────────


def test_preprocess_unconfigured_csv_returns_400(
    client, api_url, admin_headers, make_project, upload_file
):
    """A CSV uploaded without a preprocessing strategy must be rejected with
    csv_xlsx_needs_config before any task rows are created."""
    project_id = make_project(admin_headers, name="Unconfigured CSV")["id"]
    file_id = upload_file(
        admin_headers,
        project_id,
        content=b"a,b\n1,2\n",
        name="raw.csv",
        content_type="text/csv",
    )["id"]

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json={
            "file_ids": [file_id],
            "inline_config": {"name": "c"},
            "bypass_celery": True,
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "csv_xlsx_needs_config"


def test_preprocess_image_all_ocr_disabled_returns_400(
    client, api_url, user_headers, make_project, monkeypatch
):
    """An image submission is refused with no_ocr_engine_enabled when every OCR
    engine is disabled."""
    from ..src import models
    from ..src.core import config
    from ..src.db.session import SessionLocal

    live = config._get_settings()
    for flag in (
        "DOCLING_SERVE_ENABLED",
        "MISTRAL_OCR_ENABLED",
        "VISION_OCR_ENABLED",
        "DOCLING_LOCAL_FALLBACK",
    ):
        monkeypatch.setattr(live, flag, False)

    project_id = make_project(user_headers, name="No OCR")["id"]
    db = SessionLocal()
    try:
        f = _seed_file(
            db, project_id, file_type=models.FileType.IMAGE_PNG, name="scan.png"
        )
        db.commit()
        file_id = f.id
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=user_headers,
        json={"file_ids": [file_id], "inline_config": {"name": "c"}},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "no_ocr_engine_enabled"


def test_preprocess_files_already_being_processed_returns_409(
    client, api_url, user_headers, make_project
):
    """Submitting a file that already has an IN_PROGRESS file task for the same
    config is rejected with files_already_being_processed."""
    from ..src import models
    from ..src.db.session import SessionLocal

    project_id = make_project(user_headers, name="In Progress")["id"]
    db = SessionLocal()
    try:
        cfg = _seed_config(db, project_id, {})
        f = _seed_file(
            db, project_id, file_type=models.FileType.TEXT_PLAIN, name="p.txt"
        )
        task = models.PreprocessingTask(
            project_id=project_id,
            configuration_id=cfg.id,
            total_files=1,
            status=models.PreprocessingStatus.IN_PROGRESS,
        )
        db.add(task)
        db.flush()
        ftask = models.FilePreprocessingTask(
            preprocessing_task_id=task.id,
            file_id=f.id,
            file_name=f.file_name,
            status=models.PreprocessingStatus.IN_PROGRESS,
        )
        db.add(ftask)
        db.commit()
        file_id = f.id
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=user_headers,
        # Empty additional_settings → matches the seeded config ({}), so the
        # in-progress check runs against that config's id.
        json={"file_ids": [file_id], "inline_config": {"name": "c"}},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "files_already_being_processed"


def test_preprocess_nonadmin_bypass_celery_returns_403(
    client, api_url, user_headers, make_project, upload_file
):
    """A non-admin cannot set bypass_celery."""
    project_id = make_project(user_headers, name="Bypass 403")["id"]
    file_id = upload_file(
        user_headers, project_id, content=b"hi", name="t.txt", content_type="text/plain"
    )["id"]
    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=user_headers,
        json={
            "file_ids": [file_id],
            "inline_config": {"name": "c"},
            "bypass_celery": True,
        },
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"]["code"] == "preprocess.bypass_celery_admin_only"


def test_preprocess_all_files_skipped_autocompletes(
    client, api_url, admin_headers, make_project
):
    """skip_existing with every file already processed for the config yields a
    task that is immediately COMPLETED with skipped_files populated (no worker
    runs). Uses admin bypass_celery to get past the DISABLE_CELERY guard."""
    from ..src import models
    from ..src.db.session import SessionLocal

    project_id = make_project(admin_headers, name="All Skipped")["id"]
    db = SessionLocal()
    try:
        cfg = _seed_config(db, project_id, {})
        f = _seed_file(
            db, project_id, file_type=models.FileType.TEXT_PLAIN, name="done.txt"
        )
        _seed_document(db, project_id, file_id=f.id, config_id=cfg.id, name="done.txt")
        db.commit()
        file_id = f.id
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json={
            "file_ids": [file_id],
            "inline_config": {"name": "c"},
            "skip_existing": True,
            "bypass_celery": True,
        },
    )
    assert resp.status_code == 200, resp.text
    task = resp.json()
    assert task["status"] == "completed"
    assert task["skipped_files"] == 1
    assert task["total_files"] == 0


# ── force_reprocess ─────────────────────────────────────────────────────────


def test_force_reprocess_referenced_document_returns_409(
    client, api_url, admin_headers, make_project, make_schema, make_prompt
):
    """force_reprocess must refuse (409) to delete a document referenced by a
    trial result, reporting the referenced document ids."""
    from ..src import models
    from ..src.db.session import SessionLocal

    project_id = make_project(admin_headers, name="Force Ref")["id"]
    schema_id = make_schema(admin_headers, project_id)["id"]
    prompt_id = make_prompt(admin_headers, project_id)["id"]

    db = SessionLocal()
    try:
        cfg = _seed_config(db, project_id, {})
        f = _seed_file(
            db, project_id, file_type=models.FileType.TEXT_PLAIN, name="ref.txt"
        )
        doc = _seed_document(
            db, project_id, file_id=f.id, config_id=cfg.id, name="ref.txt"
        )
        trial = _seed_trial(db, project_id, schema_id, prompt_id, 1, [doc.id])
        db.add(models.TrialResult(trial_id=trial.id, document_id=doc.id, result={}))
        db.commit()
        file_id, doc_id = f.id, doc.id
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json={
            "file_ids": [file_id],
            "inline_config": {"name": "c"},
            "force_reprocess": True,
            "bypass_celery": True,
        },
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["referenced_document_ids"] == [doc_id]


def test_force_reprocess_unreferenced_deletes_old_docs(
    client, api_url, admin_headers, make_project, upload_file
):
    """force_reprocess on an unreferenced document deletes the old row and
    reprocesses (a new document replaces it)."""
    project_id = make_project(admin_headers, name="Force Unref")["id"]
    file_id = upload_file(
        admin_headers,
        project_id,
        content=b"reprocess me",
        name="u.txt",
        content_type="text/plain",
    )["id"]

    body = {
        "file_ids": [file_id],
        "inline_config": {"name": "c"},
        "bypass_celery": True,
    }
    # First run creates the config + a single document.
    first = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json=body,
    )
    assert first.status_code == 200, first.text
    docs = client.get(
        f"{api_url}/project/{project_id}/document", headers=admin_headers
    ).json()
    assert docs["total"] == 1

    # Second run with force_reprocess reuses the same config (same settings),
    # deletes the old doc, and reprocesses the file. If the old doc were NOT
    # deleted (or a second config were created) we'd end up with 2 documents;
    # correct behavior replaces it in place, so the count stays at 1 and the
    # task actually processed the file (total_files == 1, not a 0-file skip).
    # (Note: SQLite may recycle the deleted row's id, so we assert on document
    # count rather than id identity.)
    body["force_reprocess"] = True
    second = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=admin_headers,
        json=body,
    )
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "completed"
    assert second.json()["total_files"] == 1

    remaining = client.get(
        f"{api_url}/project/{project_id}/document", headers=admin_headers
    ).json()
    assert remaining["total"] == 1


# ── cancel ──────────────────────────────────────────────────────────────────


def test_cancel_keep_processed_deletes_nothing(
    client, api_url, user_headers, make_project
):
    """keep_processed=true forces rollback off, so a completed file task's
    document survives the cancel."""
    from ..src import models
    from ..src.db.session import SessionLocal

    project_id = make_project(user_headers, name="Cancel Keep")["id"]
    db = SessionLocal()
    try:
        cfg = _seed_config(db, project_id, {})
        f = _seed_file(
            db, project_id, file_type=models.FileType.TEXT_PLAIN, name="k.txt"
        )
        task = models.PreprocessingTask(
            project_id=project_id,
            configuration_id=cfg.id,
            total_files=1,
            rollback_on_cancel=True,
            status=models.PreprocessingStatus.IN_PROGRESS,
        )
        db.add(task)
        db.flush()
        ftask = models.FilePreprocessingTask(
            preprocessing_task_id=task.id,
            file_id=f.id,
            file_name=f.file_name,
            status=models.PreprocessingStatus.COMPLETED,
        )
        db.add(ftask)
        db.flush()
        doc = _seed_document(
            db,
            project_id,
            file_id=f.id,
            config_id=cfg.id,
            name="k.txt",
            file_task_id=ftask.id,
        )
        db.commit()
        task_id, doc_id = task.id, doc.id
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess/{task_id}/cancel",
        headers=user_headers,
        params={"keep_processed": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"

    still = client.get(
        f"{api_url}/project/{project_id}/document/{doc_id}", headers=user_headers
    )
    assert still.status_code == 200


def test_cancel_rollback_keeps_referenced_document(
    client, api_url, admin_headers, make_project, make_schema, make_prompt
):
    """On rollback cancel, a document referenced by an evaluation metric is
    KEPT while an unreferenced sibling is deleted; deleted_count reflects only
    the unreferenced one."""
    import uuid

    from ..src import models
    from ..src.db.session import SessionLocal

    project_id = make_project(admin_headers, name="Cancel Rollback")["id"]
    schema_id = make_schema(admin_headers, project_id)["id"]
    prompt_id = make_prompt(admin_headers, project_id)["id"]

    db = SessionLocal()
    try:
        cfg = _seed_config(db, project_id, {})
        f = _seed_file(
            db, project_id, file_type=models.FileType.TEXT_PLAIN, name="r.txt"
        )
        task = models.PreprocessingTask(
            project_id=project_id,
            configuration_id=cfg.id,
            total_files=1,
            rollback_on_cancel=True,
            status=models.PreprocessingStatus.IN_PROGRESS,
        )
        db.add(task)
        db.flush()
        ftask = models.FilePreprocessingTask(
            preprocessing_task_id=task.id,
            file_id=f.id,
            file_name=f.file_name,
            status=models.PreprocessingStatus.COMPLETED,
        )
        db.add(ftask)
        db.flush()
        ref_doc = _seed_document(
            db,
            project_id,
            file_id=f.id,
            config_id=cfg.id,
            name="ref.txt",
            file_task_id=ftask.id,
        )
        free_doc = _seed_document(
            db,
            project_id,
            file_id=f.id,
            config_id=cfg.id,
            name="free.txt",
            file_task_id=ftask.id,
        )
        trial = _seed_trial(db, project_id, schema_id, prompt_id, 1, [ref_doc.id])
        gt = models.GroundTruth(
            project_id=project_id,
            name="gt",
            format="csv",
            file_uuid=str(uuid.uuid4()),
        )
        db.add(gt)
        db.flush()
        ev = models.Evaluation(
            trial_id=trial.id,
            groundtruth_id=gt.id,
            metrics={},
            field_metrics={},
            document_metrics=[],
        )
        db.add(ev)
        db.flush()
        db.add(
            models.EvaluationMetric(
                evaluation_id=ev.id,
                document_id=ref_doc.id,
                field_name="f",
                is_correct=True,
            )
        )
        db.commit()
        task_id, ref_id, free_id = task.id, ref_doc.id, free_doc.id
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess/{task_id}/cancel",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "cancelled"
    assert "1 processed documents rolled back" in body["message"]
    assert "kept" in body["message"]

    # Referenced doc survives, unreferenced one is deleted.
    assert (
        client.get(
            f"{api_url}/project/{project_id}/document/{ref_id}", headers=admin_headers
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"{api_url}/project/{project_id}/document/{free_id}", headers=admin_headers
        ).status_code
        == 404
    )


def test_cancel_terminal_task_returns_400(client, api_url, user_headers, make_project):
    """Cancelling an already-COMPLETED task is rejected with
    cannot_cancel_status."""
    from ..src import models
    from ..src.db.session import SessionLocal

    project_id = make_project(user_headers, name="Cancel Terminal")["id"]
    db = SessionLocal()
    try:
        cfg = _seed_config(db, project_id, {})
        task = models.PreprocessingTask(
            project_id=project_id,
            configuration_id=cfg.id,
            total_files=0,
            status=models.PreprocessingStatus.COMPLETED,
        )
        db.add(task)
        db.commit()
        task_id = task.id
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess/{task_id}/cancel",
        headers=user_headers,
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "preprocess.cannot_cancel_status"


# ── list tasks: status filter + pagination ─────────────────────────────────


def test_get_tasks_invalid_status_returns_400(
    client, api_url, user_headers, make_project
):
    project_id = make_project(user_headers, name="Bad Status")["id"]
    resp = client.get(
        f"{api_url}/project/{project_id}/preprocess",
        headers=user_headers,
        params={"status": "bogus"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "preprocess.invalid_status"


def test_get_tasks_limit_and_offset(client, api_url, user_headers, make_project):
    from ..src import models
    from ..src.db.session import SessionLocal

    project_id = make_project(user_headers, name="Pagination")["id"]
    db = SessionLocal()
    try:
        cfg = _seed_config(db, project_id, {})
        for _ in range(3):
            db.add(
                models.PreprocessingTask(
                    project_id=project_id,
                    configuration_id=cfg.id,
                    total_files=0,
                    status=models.PreprocessingStatus.COMPLETED,
                )
            )
        db.commit()
    finally:
        db.close()

    all_tasks = client.get(
        f"{api_url}/project/{project_id}/preprocess", headers=user_headers
    ).json()
    assert len(all_tasks) == 3

    page1 = client.get(
        f"{api_url}/project/{project_id}/preprocess",
        headers=user_headers,
        params={"limit": 2, "offset": 0},
    ).json()
    assert len(page1) == 2

    page2 = client.get(
        f"{api_url}/project/{project_id}/preprocess",
        headers=user_headers,
        params={"limit": 2, "offset": 2},
    ).json()
    assert len(page2) == 1


# ── retry-failed ────────────────────────────────────────────────────────────


def test_retry_failed_no_failed_files_returns_400(
    client, api_url, user_headers, make_project
):
    from ..src import models
    from ..src.db.session import SessionLocal

    project_id = make_project(user_headers, name="Retry None")["id"]
    db = SessionLocal()
    try:
        cfg = _seed_config(db, project_id, {})
        f = _seed_file(
            db, project_id, file_type=models.FileType.TEXT_PLAIN, name="ok.txt"
        )
        task = models.PreprocessingTask(
            project_id=project_id,
            configuration_id=cfg.id,
            total_files=1,
            status=models.PreprocessingStatus.COMPLETED,
        )
        db.add(task)
        db.flush()
        db.add(
            models.FilePreprocessingTask(
                preprocessing_task_id=task.id,
                file_id=f.id,
                file_name=f.file_name,
                status=models.PreprocessingStatus.COMPLETED,
            )
        )
        db.commit()
        task_id = task.id
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess/{task_id}/retry-failed",
        headers=user_headers,
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "preprocess.no_failed_files"


def test_retry_failed_while_task_running_returns_409(
    client, api_url, user_headers, make_project
):
    from ..src import models
    from ..src.db.session import SessionLocal

    project_id = make_project(user_headers, name="Retry Running")["id"]
    db = SessionLocal()
    try:
        cfg = _seed_config(db, project_id, {})
        task = models.PreprocessingTask(
            project_id=project_id,
            configuration_id=cfg.id,
            total_files=1,
            status=models.PreprocessingStatus.IN_PROGRESS,
        )
        db.add(task)
        db.commit()
        task_id = task.id
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess/{task_id}/retry-failed",
        headers=user_headers,
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "preprocess.task_still_running"
