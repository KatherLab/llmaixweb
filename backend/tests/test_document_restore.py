# backend/tests/test_document_restore.py
"""Tests for restoring an archived document version.

Restore promotes an archived version's content to a fresh ``is_latest=True``
document WITHOUT reprocessing — so the restored text is exactly the archived
version's content (never re-derived from the original file).
"""


def _login(client, api_url, username="admin@example.com", password="Adminpassword1"):
    resp = client.post(
        f"{api_url}/auth/login", data={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_project_with_document(client, api_url, headers, file_text=b"Hello World!"):
    """Create a project, upload a text file, preprocess it, and return
    ``(project_id, full_document)`` for the single latest document produced."""
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Restore Test"}
    ).json()["id"]

    file_resp = client.post(
        f"{api_url}/project/{project_id}/file",
        headers=headers,
        files={
            "file": ("restore.txt", file_text, "text/plain"),
            "file_info": (
                "",
                '{"file_name": "restore.txt", "file_type": "text/plain"}',
                "application/json",
            ),
        },
    )
    assert file_resp.status_code == 200, file_resp.text
    file_id = file_resp.json()["id"]

    pp = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": [file_id],
            "inline_config": {"name": "RestoreCfg"},
            "bypass_celery": True,
        },
    )
    assert pp.status_code == 200, pp.text

    doc_id = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()["items"][0]["id"]
    full = client.get(
        f"{api_url}/project/{project_id}/document/{doc_id}", headers=headers
    ).json()
    return project_id, full


def _seed_archived_version(project_id, current_doc, text):
    """Insert an ``is_latest=False`` archived version of ``current_doc`` with
    distinct ``text``, mirroring the versioning convention (version_of → root).
    Returns the archived document's id."""
    from backend.src import models
    from backend.src.db.session import SessionLocal

    db = SessionLocal()
    try:
        archived = models.Document(
            project_id=project_id,
            original_file_id=current_doc["original_file_id"],
            preprocessing_config_id=current_doc["preprocessing_config_id"],
            text=text,
            document_name=current_doc["document_name"],
            meta_data={"note": "seeded archived version"},
            is_latest=False,
            version_of=current_doc["id"],
        )
        db.add(archived)
        db.commit()
        db.refresh(archived)
        return archived.id
    finally:
        db.close()


def test_restore_promotes_archived_content_without_reprocessing(client, api_url):
    headers = _login(client, api_url)
    project_id, current = _make_project_with_document(client, api_url, headers)

    # The archived text deliberately differs from the file's real content
    # ("Hello World!"). If restore reprocessed the file it would yield the file
    # content; copying the archived version yields exactly this text.
    archived_text = "OLD VERSION CONTENT — never in the source file"
    archived_id = _seed_archived_version(project_id, current, archived_text)

    resp = client.post(
        f"{api_url}/project/{project_id}/document/{archived_id}/restore",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    restored = resp.json()

    # New latest carries the archived content verbatim (no reprocessing).
    assert restored["text"] == archived_text
    assert restored["is_latest"] is True
    assert restored["id"] not in (current["id"], archived_id)
    # Version chain root points back at the original document.
    assert restored["version_of"] == current["id"]
    assert restored["meta_data"]["restored_from_document_id"] == archived_id

    # The previously-latest document is now archived.
    prev = client.get(
        f"{api_url}/project/{project_id}/document/{current['id']}", headers=headers
    ).json()
    assert prev["is_latest"] is False

    # The default (latest-only) list now shows the restored doc, not the old one.
    items = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()["items"]
    ids = {i["id"] for i in items}
    assert restored["id"] in ids
    assert current["id"] not in ids
    assert archived_id not in ids

    # Fetching the restored doc returns the archived content.
    fetched = client.get(
        f"{api_url}/project/{project_id}/document/{restored['id']}", headers=headers
    ).json()
    assert fetched["text"] == archived_text


def test_restore_already_latest_returns_400(client, api_url):
    headers = _login(client, api_url)
    project_id, current = _make_project_with_document(client, api_url, headers)

    resp = client.post(
        f"{api_url}/project/{project_id}/document/{current['id']}/restore",
        headers=headers,
    )
    assert resp.status_code == 400
    assert "already the latest" in resp.json()["detail"].lower()


def test_restore_unknown_document_returns_404(client, api_url):
    headers = _login(client, api_url)
    project_id, _ = _make_project_with_document(client, api_url, headers)

    resp = client.post(
        f"{api_url}/project/{project_id}/document/99999999/restore",
        headers=headers,
    )
    assert resp.status_code == 404


def test_restore_preserves_group_membership(client, api_url):
    headers = _login(client, api_url)
    project_id, current = _make_project_with_document(client, api_url, headers)

    # Put the current document into a group.
    set_id = client.post(
        f"{api_url}/project/{project_id}/document-set",
        headers=headers,
        json={"name": "Restore Group", "document_ids": [current["id"]]},
    ).json()["id"]

    archived_id = _seed_archived_version(project_id, current, "archived group text")
    restored = client.post(
        f"{api_url}/project/{project_id}/document/{archived_id}/restore",
        headers=headers,
    ).json()

    # The restored doc inherits the group; the archived-out old doc leaves it.
    members = client.get(
        f"{api_url}/project/{project_id}/document",
        headers=headers,
        params={"document_set_id": set_id, "limit": 100},
    ).json()
    member_ids = {i["id"] for i in members["items"]}
    assert restored["id"] in member_ids
    assert current["id"] not in member_ids

    summary = client.get(
        f"{api_url}/project/{project_id}/document-set/{set_id}", headers=headers
    ).json()
    assert summary["document_count"] == 1


def test_restore_forbidden_for_non_owner(client, api_url):
    owner_headers = _login(client, api_url)
    project_id, current = _make_project_with_document(client, api_url, owner_headers)
    archived_id = _seed_archived_version(project_id, current, "archived text")

    other_headers = _login(
        client, api_url, username="another@example.com", password="Anotherpassword1"
    )
    resp = client.post(
        f"{api_url}/project/{project_id}/document/{archived_id}/restore",
        headers=other_headers,
    )
    assert resp.status_code == 403
