# backend/tests/test_document_combine.py
"""Tests for POST /project/{id}/document/combine (combined/derived documents).

Covers:
- happy path: merged text with per-source section headers, meta_data provenance,
  document_source_association rows, and the optional document set.
- downstream: a trial over a combined document runs and stores a result.
- re-combining under the same name archives the previous combined document.
- validation: duplicate group names, unknown documents, nesting combined docs.
- deleting a source document keeps the combined document (only the link goes).
- list/search endpoints return combined documents (no original file joined).
"""


def _make_documents(client, api_url, headers, pid, names):
    """Upload one txt file per name, preprocess, and return doc ids by name."""
    file_ids = []
    for name in names:
        file_ids.append(
            client.post(
                f"{api_url}/project/{pid}/file",
                headers=headers,
                files={
                    "file": (name, f"content of {name}".encode(), "text/plain"),
                    "file_info": (
                        "",
                        f'{{"file_name": "{name}", "file_type": "text/plain"}}',
                        "application/json",
                    ),
                },
            ).json()["id"]
        )
    assert (
        client.post(
            f"{api_url}/project/{pid}/preprocess",
            headers=headers,
            json={
                "file_ids": file_ids,
                "inline_config": {"name": "Cfg", "description": "d"},
                "bypass_celery": True,
            },
        ).status_code
        == 200
    )
    docs = client.get(f"{api_url}/project/{pid}/document", headers=headers).json()[
        "items"
    ]
    by_name = {}
    for doc in docs:
        by_name[doc["original_file"]["file_name"]] = doc["id"]
    return by_name


def test_combine_documents_happy_path(client, api_url, admin_headers, make_project):
    from sqlalchemy import select

    from backend.src.db.session import SessionLocal
    from backend.src.models.project import document_source_association

    headers = admin_headers
    pid = make_project(headers, name="CombineProj")["id"]
    ids = _make_documents(
        client, api_url, headers, pid, ["visit1.txt", "visit2.txt", "other.txt"]
    )

    resp = client.post(
        f"{api_url}/project/{pid}/document/combine",
        headers=headers,
        json={
            "groups": [
                {
                    "name": "PATIENT-001",
                    "document_ids": [ids["visit1.txt"], ids["visit2.txt"]],
                }
            ]
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_set_id"] is None
    assert body["replaced"] == []
    assert len(body["documents"]) == 1
    combined = body["documents"][0]
    assert combined["document_name"] == "PATIENT-001"
    assert combined["original_file_id"] is None
    assert combined["preprocessing_config_id"] is None
    assert combined["meta_data"]["combined"] is True
    assert combined["meta_data"]["source_document_ids"] == [
        ids["visit1.txt"],
        ids["visit2.txt"],
    ]
    assert combined["meta_data"]["source_count"] == 2

    # Full text carries both sections, labeled and in order.
    text = client.get(
        f"{api_url}/project/{pid}/document/{combined['id']}", headers=headers
    ).json()["text"]
    assert "--- Document: visit1.txt ---" in text
    assert "--- Document: visit2.txt ---" in text
    assert "content of visit1.txt" in text
    assert "content of visit2.txt" in text
    assert text.index("visit1.txt") < text.index("visit2.txt")

    # Provenance rows exist with positions preserving the source order.
    db = SessionLocal()
    try:
        rows = db.execute(
            select(
                document_source_association.c.source_document_id,
                document_source_association.c.position,
            )
            .where(document_source_association.c.derived_document_id == combined["id"])
            .order_by(document_source_association.c.position)
        ).all()
        assert rows == [(ids["visit1.txt"], 0), (ids["visit2.txt"], 1)]
    finally:
        db.close()

    # Search finds the combined document by name (outer join regression).
    found = client.get(
        f"{api_url}/project/{pid}/document?search=PATIENT-001", headers=headers
    ).json()["items"]
    assert [d["id"] for d in found] == [combined["id"]]


def test_combine_with_document_set_and_trial(
    client, api_url, admin_headers, make_project, monkeypatch
):
    from .fake_llm import make_fake_openai

    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"val": "x"}),
    )
    headers = admin_headers
    pid = make_project(headers, name="CombineTrialProj")["id"]
    ids = _make_documents(
        client, api_url, headers, pid, ["p1a.txt", "p1b.txt", "p2a.txt"]
    )

    resp = client.post(
        f"{api_url}/project/{pid}/document/combine",
        headers=headers,
        json={
            "groups": [
                {"name": "P1", "document_ids": [ids["p1a.txt"], ids["p1b.txt"]]},
                {"name": "P2", "document_ids": [ids["p2a.txt"]]},
            ],
            "create_document_set": True,
            "document_set_name": "Combined by patient",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    set_id = body["document_set_id"]
    assert set_id is not None
    combined_ids = {d["id"] for d in body["documents"]}
    assert len(combined_ids) == 2

    # The set contains exactly the combined documents.
    in_set = client.get(
        f"{api_url}/project/{pid}/document?document_set_id={set_id}", headers=headers
    ).json()["items"]
    assert {d["id"] for d in in_set} == combined_ids

    # A trial over the set runs and produces one result per combined document.
    prompt_id = client.post(
        f"{api_url}/project/{pid}/prompt",
        headers=headers,
        json={
            "name": "P",
            "system_prompt": "SP {document_content}",
            "user_prompt": "UP {document_content}",
            "project_id": pid,
        },
    ).json()["id"]
    schema_id = client.post(
        f"{api_url}/project/{pid}/schema",
        headers=headers,
        json={
            "schema_name": "S",
            "schema_definition": {
                "type": "object",
                "properties": {"val": {"type": "string"}},
            },
        },
    ).json()["id"]
    trial = client.post(
        f"{api_url}/project/{pid}/trial",
        headers=headers,
        json={
            "schema_id": schema_id,
            "prompt_id": prompt_id,
            "document_set_id": set_id,
            "bypass_celery": True,
            "llm_model": "mock-model",
            "api_key": "test-key",
            "base_url": "http://localhost:11434/v1",
        },
    )
    assert trial.status_code == 200
    results = client.get(
        f"{api_url}/project/{pid}/trial/{trial.json()['id']}/results",
        headers=headers,
    ).json()
    items = results["items"] if isinstance(results, dict) else results
    assert {r["document_id"] for r in items} == combined_ids


def test_recombine_same_name_archives_previous(
    client, api_url, admin_headers, make_project
):
    headers = admin_headers
    pid = make_project(headers, name="RecombineProj")["id"]
    ids = _make_documents(client, api_url, headers, pid, ["a.txt", "b.txt"])

    first = client.post(
        f"{api_url}/project/{pid}/document/combine",
        headers=headers,
        json={"groups": [{"name": "CASE-7", "document_ids": [ids["a.txt"]]}]},
    ).json()["documents"][0]

    resp = client.post(
        f"{api_url}/project/{pid}/document/combine",
        headers=headers,
        json={
            "groups": [{"name": "CASE-7", "document_ids": [ids["a.txt"], ids["b.txt"]]}]
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["replaced"] == ["CASE-7"]
    second = body["documents"][0]
    assert second["id"] != first["id"]
    assert second["version_of"] == first["id"]

    # Only the new combined document is latest.
    items = client.get(
        f"{api_url}/project/{pid}/document?search=CASE-7", headers=headers
    ).json()["items"]
    assert [d["id"] for d in items] == [second["id"]]


def test_combine_validation_errors(client, api_url, admin_headers, make_project):
    headers = admin_headers
    pid = make_project(headers, name="CombineValProj")["id"]
    ids = _make_documents(client, api_url, headers, pid, ["v1.txt", "v2.txt"])

    # Duplicate group names in one request.
    resp = client.post(
        f"{api_url}/project/{pid}/document/combine",
        headers=headers,
        json={
            "groups": [
                {"name": "X", "document_ids": [ids["v1.txt"]]},
                {"name": "X", "document_ids": [ids["v2.txt"]]},
            ]
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "documents.combine_duplicate_names"

    # Unknown document id.
    resp = client.post(
        f"{api_url}/project/{pid}/document/combine",
        headers=headers,
        json={"groups": [{"name": "Y", "document_ids": [999999]}]},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "documents.combine_documents_not_found"

    # Combining a combined document is rejected.
    combined_id = client.post(
        f"{api_url}/project/{pid}/document/combine",
        headers=headers,
        json={"groups": [{"name": "Z", "document_ids": [ids["v1.txt"]]}]},
    ).json()["documents"][0]["id"]
    resp = client.post(
        f"{api_url}/project/{pid}/document/combine",
        headers=headers,
        json={"groups": [{"name": "Z2", "document_ids": [combined_id]}]},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "documents.combine_nested"


def test_source_delete_keeps_combined_document(
    client, api_url, admin_headers, make_project
):
    from sqlalchemy import select

    from backend.src.db.session import SessionLocal
    from backend.src.models.project import document_source_association

    headers = admin_headers
    pid = make_project(headers, name="CombineDelProj")["id"]
    ids = _make_documents(client, api_url, headers, pid, ["s1.txt", "s2.txt"])

    combined_id = client.post(
        f"{api_url}/project/{pid}/document/combine",
        headers=headers,
        json={
            "groups": [{"name": "KEEP", "document_ids": [ids["s1.txt"], ids["s2.txt"]]}]
        },
    ).json()["documents"][0]["id"]

    assert (
        client.delete(
            f"{api_url}/project/{pid}/document/{ids['s1.txt']}?cascade=true",
            headers=headers,
        ).status_code
        == 200
    )

    # Combined document survives with its materialized text; only the link went.
    doc = client.get(
        f"{api_url}/project/{pid}/document/{combined_id}", headers=headers
    ).json()
    assert "content of s1.txt" in doc["text"]
    db = SessionLocal()
    try:
        remaining = (
            db.execute(
                select(document_source_association.c.source_document_id).where(
                    document_source_association.c.derived_document_id == combined_id
                )
            )
            .scalars()
            .all()
        )
        assert remaining == [ids["s2.txt"]]
    finally:
        db.close()
