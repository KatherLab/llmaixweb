# backend/tests/test_preview_rows.py
"""Tests for GET /file/{id}/preview-rows hardened branches (files.py).

The endpoint promises robust handling of hostile/ambiguous spreadsheet
uploads; these tests pin each branch:
- CSV: delimiter sniffing, blank/duplicate header normalization,
  has_header=false column fallback, truncation flag, long-cell clipping,
  empty file, binary bytes named .csv → clean 400 (not a 500).
- Format decision: CSV content mislabeled application/vnd.ms-excel parses as
  CSV; OLE2 magic bytes → legacy-.xls 400; textual bytes named .xlsx fall
  back to CSV parsing; ZIP-but-not-a-workbook .xlsx → 400 with error id.
- XLSX: sheet list, sheet selection, invalid sheet name falls back to the
  first sheet.
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\x1e"


@pytest.fixture
def api_url():
    return "/api/v1"


@pytest.fixture
def client():
    from ..src.main import app

    return TestClient(app)


def _admin_headers(client, api_url):
    resp = client.post(
        f"{api_url}/auth/login",
        data={"username": "admin@example.com", "password": "Adminpassword1"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def project_id(client, api_url):
    headers = _admin_headers(client, api_url)
    pid = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Preview Rows"}
    ).json()["id"]
    yield pid
    client.delete(f"{api_url}/project/{pid}", headers=headers)


def _seed_file(project_id: int, name: str, content: bytes, file_type: str) -> int:
    """Create a File row + storage blob directly (bypasses upload-side MIME
    sniffing so each test controls the exact stored type/bytes)."""
    from ..src import models
    from ..src.db.session import SessionLocal
    from ..src.dependencies import save_file

    blob_uuid = save_file(content)
    db = SessionLocal()
    try:
        file = models.File(
            project_id=project_id,
            file_uuid=blob_uuid,
            file_name=name,
            file_type=file_type,
            file_hash=str(uuid.uuid4()),
        )
        db.add(file)
        db.commit()
        return file.id
    finally:
        db.close()


def _preview(client, api_url, headers, project_id, file_id, **params):
    return client.get(
        f"{api_url}/project/{project_id}/file/{file_id}/preview-rows",
        headers=headers,
        params=params,
    )


def _xlsx_bytes(sheets: dict[str, list[list]]) -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name, rows in sheets.items():
        ws = wb.create_sheet(sheet_name)
        for row in rows:
            ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_csv_preview_sniffs_delimiter_and_truncates(client, api_url, project_id):
    headers = _admin_headers(client, api_url)
    rows = "\n".join(f"v{i};w{i}" for i in range(20))
    file_id = _seed_file(
        project_id, "semi.csv", f"col_a;col_b\n{rows}\n".encode(), "text/csv"
    )

    resp = _preview(client, api_url, headers, project_id, file_id, max_rows=5)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["detected_delimiter"] == ";"
    assert body["headers"] == ["col_a", "col_b"]
    assert body["rows"] == [[f"v{i}", f"w{i}"] for i in range(5)]
    assert body["total_rows"] == 20
    assert body["truncated"] is True


def test_csv_preview_normalizes_blank_and_duplicate_headers(
    client, api_url, project_id
):
    headers = _admin_headers(client, api_url)
    file_id = _seed_file(
        project_id, "dupes.csv", b"name,,name,age\na,b,c,d\n", "text/csv"
    )

    resp = _preview(client, api_url, headers, project_id, file_id)
    assert resp.status_code == 200, resp.text
    assert resp.json()["headers"] == ["name", "Column 2", "name (2)", "age"]


def test_csv_preview_without_header_uses_column_fallback(client, api_url, project_id):
    headers = _admin_headers(client, api_url)
    file_id = _seed_file(project_id, "nohead.csv", b"1,2,3\n4,5,6\n", "text/csv")

    resp = _preview(client, api_url, headers, project_id, file_id, has_header="false")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["headers"] == ["Column 1", "Column 2", "Column 3"]
    assert body["rows"] == [["1", "2", "3"], ["4", "5", "6"]]
    assert body["total_rows"] == 2


def test_csv_preview_clips_very_long_cells(client, api_url, project_id):
    headers = _admin_headers(client, api_url)
    long_cell = "x" * 6000
    file_id = _seed_file(
        project_id, "long.csv", f"col\n{long_cell}\n".encode(), "text/csv"
    )

    resp = _preview(client, api_url, headers, project_id, file_id)
    assert resp.status_code == 200, resp.text
    cell = resp.json()["rows"][0][0]
    assert len(cell) == 5001
    assert cell.endswith("…")


def test_empty_csv_preview_returns_empty_shape(client, api_url, project_id):
    headers = _admin_headers(client, api_url)
    file_id = _seed_file(project_id, "empty.csv", b"", "text/csv")

    resp = _preview(client, api_url, headers, project_id, file_id)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["headers"] == []
    assert body["rows"] == []
    assert body["total_rows"] == 0
    assert body["truncated"] is False


def test_binary_bytes_named_csv_do_not_500(client, api_url, project_id):
    """NUL-ridden binary bytes stored as .csv must never 500. (On Python
    ≥3.11 the csv module parses NUL bytes fine, so this decodes with
    replacement characters and returns 200; the csv.Error → 400 branch stays
    as the defensive net for inputs the parser does reject.)"""
    headers = _admin_headers(client, api_url)
    file_id = _seed_file(
        project_id, "binary.csv", b"\x00\x01\x02\x00garbage\x00", "text/csv"
    )

    resp = _preview(client, api_url, headers, project_id, file_id)
    assert resp.status_code in (200, 400), resp.text


def test_csv_content_mislabeled_ms_excel_parses_as_csv(client, api_url, project_id):
    """Windows browsers upload CSVs as application/vnd.ms-excel; magic-byte
    elimination must route them to the CSV parser."""
    headers = _admin_headers(client, api_url)
    file_id = _seed_file(
        project_id, "report", b"a,b\n1,2\n", "application/vnd.ms-excel"
    )

    resp = _preview(client, api_url, headers, project_id, file_id)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["headers"] == ["a", "b"]
    assert body["rows"] == [["1", "2"]]


def test_legacy_ole_xls_rejected_with_clear_message(client, api_url, project_id):
    headers = _admin_headers(client, api_url)
    file_id = _seed_file(
        project_id,
        "legacy.xls",
        OLE_MAGIC + b"\x00" * 64,
        "application/vnd.ms-excel",
    )

    resp = _preview(client, api_url, headers, project_id, file_id)
    assert resp.status_code == 400, resp.text
    assert ".xls (binary)" in resp.json()["detail"]["message"]


def test_textual_bytes_named_xlsx_fall_back_to_csv(client, api_url, project_id):
    """A CSV renamed to .xlsx (no ZIP magic) must fall back to CSV parsing
    instead of failing the openpyxl load."""
    headers = _admin_headers(client, api_url)
    file_id = _seed_file(
        project_id,
        "renamed.xlsx",
        b"x,y\n7,8\n",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    resp = _preview(client, api_url, headers, project_id, file_id)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["headers"] == ["x", "y"]
    assert body["rows"] == [["7", "8"]]
    # CSV-branch response shape (proves the fallback path ran).
    assert "detected_delimiter" in body


def test_zip_but_not_workbook_xlsx_returns_400_with_error_id(
    client, api_url, project_id
):
    """A genuine ZIP that isn't an OOXML workbook is ambiguous (corruption or
    storage returning wrong bytes) → 400 carrying a support correlation id."""
    import zipfile

    headers = _admin_headers(client, api_url)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("not-a-workbook.txt", "hello")
    file_id = _seed_file(
        project_id,
        "corrupt.xlsx",
        buf.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    resp = _preview(client, api_url, headers, project_id, file_id)
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]["message"]
    assert "could not be read as an Excel workbook" in detail
    assert "Quote this ID" in detail


def test_xlsx_preview_lists_sheets_and_selects_by_name(client, api_url, project_id):
    headers = _admin_headers(client, api_url)
    content = _xlsx_bytes(
        {
            "First": [["h1", "h2"], ["a", "b"]],
            "Second": [["k1"], ["z"]],
        }
    )
    file_id = _seed_file(
        project_id,
        "book.xlsx",
        content,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # Default: first sheet.
    resp = _preview(client, api_url, headers, project_id, file_id)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sheets"] == ["First", "Second"]
    assert body["headers"] == ["h1", "h2"]
    assert body["rows"] == [["a", "b"]]

    # Explicit second sheet.
    resp = _preview(client, api_url, headers, project_id, file_id, sheet="Second")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["headers"] == ["k1"]
    assert body["rows"] == [["z"]]

    # Invalid sheet name falls back to the first sheet, no error.
    resp = _preview(client, api_url, headers, project_id, file_id, sheet="Nope")
    assert resp.status_code == 200, resp.text
    assert resp.json()["headers"] == ["h1", "h2"]
