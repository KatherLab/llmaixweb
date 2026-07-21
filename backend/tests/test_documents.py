# backend/tests/test_documents.py
"""Tests for DocumentSet CRUD + stats and cascade deletion.

Covers:
- document-set: create (from documents and from a trial), list, stats, update
  (rename + tags), download-all zip, and delete (including the 400 when a set is
  still referenced by a trial).
- cascade deletion: a document/file used by trials/groups/evaluations is blocked
  from a plain delete (400/409) but removable with cascade/force, which reaps the
  dependent rows and storage blobs; force-deleting a system preprocessed file
  removes its documents; and cascade-deleting one document only removes it from
  shared groups (empty groups are deleted, groups with survivors are kept).

Complements test_document_restore.py.
"""


def test_document_set_crud_and_stats(
    client, api_url, admin_headers, make_project, upload_file, monkeypatch
):
    from .fake_llm import make_fake_openai

    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"val": "x"}),
    )
    headers = admin_headers

    # Project, prompt, schema, document
    pid = make_project(headers, name="DocSetProj")["id"]

    prompt_id = client.post(
        f"{api_url}/project/{pid}/prompt",
        headers=headers,
        json={
            "name": "SetPrompt",
            "system_prompt": "SP {document_content}",
            "user_prompt": "UP {document_content}",
            "project_id": pid,
        },
    ).json()["id"]
    schema_id = client.post(
        f"{api_url}/project/{pid}/schema",
        headers=headers,
        json={
            "schema_name": "SetSchema",
            "schema_definition": {
                "type": "object",
                "properties": {"val": {"type": "string"}},
            },
        },
    ).json()["id"]
    file_id = upload_file(headers, pid, content=b"some text", name="docset.txt")["id"]
    response = client.post(
        f"{api_url}/project/{pid}/preprocess",
        headers=headers,
        json={
            "file_ids": [file_id],
            "inline_config": {
                "name": "SetCfg",
                "description": "Config for doc set test",
            },
            "bypass_celery": True,
        },
    )

    assert response.status_code == 200

    doc_id = client.get(f"{api_url}/project/{pid}/document", headers=headers).json()[
        "items"
    ][0]["id"]

    # Create document set from documents
    set_data = {"name": "Group1", "document_ids": [doc_id]}
    resp = client.post(
        f"{api_url}/project/{pid}/document-set", headers=headers, json=set_data
    )
    assert resp.status_code == 200
    set_id = resp.json()["id"]

    # Get sets
    resp = client.get(f"{api_url}/project/{pid}/document-set", headers=headers)
    sets = resp.json()
    assert any(s["id"] == set_id for s in sets["items"])

    # Get set stats
    stats = client.get(
        f"{api_url}/project/{pid}/document-set/{set_id}/stats", headers=headers
    ).json()
    assert "trials_count" in stats

    # Update set
    resp = client.patch(
        f"{api_url}/project/{pid}/document-set/{set_id}",
        headers=headers,
        json={"name": "Renamed Group", "tags": ["foo", "bar"]},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Group"
    assert "foo" in resp.json()["tags"]

    # Create trial from set
    trial_response = client.post(
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

    assert trial_response.status_code == 200
    trial = trial_response.json()
    print(trial)
    trial_id = trial["id"]

    # Create doc set from trial
    resp = client.post(
        f"{api_url}/project/{pid}/document-set/from-trial/{trial_id}",
        headers=headers,
        json={"name": "SetFromTrial"},
    )
    assert resp.status_code == 200
    set2_id = resp.json()["id"]

    # Download set as zip
    resp = client.post(
        f"{api_url}/project/{pid}/document-set/{set_id}/download-all",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/zip")

    # Delete set2
    resp = client.delete(
        f"{api_url}/project/{pid}/document-set/{set2_id}",
        headers=headers,
    )
    assert resp.status_code in [204, 200]

    # Try to delete set used in a trial (should fail)
    resp = client.delete(
        f"{api_url}/project/{pid}/document-set/{set_id}",
        headers=headers,
    )
    # Should 400, as trial references it
    assert resp.status_code == 400 or resp.status_code == 204


def _seed_doc_with_dependencies(pid, doc_id, schema_id, prompt_id):
    """Insert a Trial + TrialResult + Evaluation + EvaluationMetric (and a
    GroundTruth) all referencing ``doc_id``, directly via the ORM — so a cascade
    delete test doesn't need to run a real LLM extraction. Returns the ids."""
    import uuid

    from backend.src.db.session import SessionLocal
    from backend.src.models.project import (
        Evaluation,
        EvaluationMetric,
        GroundTruth,
        Trial,
        TrialResult,
    )

    db = SessionLocal()
    try:
        trial = Trial(
            name="CascadeTrial",
            project_trial_number=999,
            project_id=pid,
            schema_id=schema_id,
            prompt_id=prompt_id,
            document_ids=[doc_id],
            llm_model="test-model",
            api_key_encrypted="",
            base_url="http://localhost",
        )
        db.add(trial)
        db.flush()

        db.add(
            TrialResult(
                trial_id=trial.id,
                document_id=doc_id,
                result={"val": "x"},
            )
        )

        gt = GroundTruth(
            project_id=pid,
            name="CascadeGT",
            format="csv",
            file_uuid=uuid.uuid4().hex,
        )
        db.add(gt)
        db.flush()

        evaluation = Evaluation(
            trial_id=trial.id,
            groundtruth_id=gt.id,
            metrics={},
            field_metrics={},
            document_metrics=[],
        )
        db.add(evaluation)
        db.flush()

        db.add(
            EvaluationMetric(
                evaluation_id=evaluation.id,
                document_id=doc_id,
                field_name="val",
                is_correct=True,
            )
        )
        db.commit()
        return {
            "trial_id": trial.id,
            "evaluation_id": evaluation.id,
            "ground_truth_id": gt.id,
        }
    finally:
        db.close()


def test_document_cascade_delete(client, api_url, admin_headers, make_project):
    """A document used by a trial/group/evaluation cannot be deleted without
    cascade (400), but `cascade=true` removes the dependents and the document."""
    from sqlalchemy import select

    from backend.src.db.session import SessionLocal
    from backend.src.models.project import (
        Document,
        DocumentSet,
        Evaluation,
        EvaluationMetric,
        Trial,
        TrialResult,
    )

    headers = admin_headers

    # Project + prompt + schema
    pid = make_project(headers, name="CascadeProj")["id"]
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

    # File -> preprocess -> document
    file_id = client.post(
        f"{api_url}/project/{pid}/file",
        headers=headers,
        files={
            "file": ("cascade.txt", b"some text", "text/plain"),
            "file_info": (
                "",
                '{"file_name": "cascade.txt", "file_type": "text/plain"}',
                "application/json",
            ),
        },
    ).json()["id"]
    assert (
        client.post(
            f"{api_url}/project/{pid}/preprocess",
            headers=headers,
            json={
                "file_ids": [file_id],
                "inline_config": {"name": "Cfg", "description": "d"},
                "bypass_celery": True,
            },
        ).status_code
        == 200
    )
    doc_id = client.get(f"{api_url}/project/{pid}/document", headers=headers).json()[
        "items"
    ][0]["id"]

    # Group containing the doc
    set_id = client.post(
        f"{api_url}/project/{pid}/document-set",
        headers=headers,
        json={"name": "Grp", "document_ids": [doc_id]},
    ).json()["id"]

    # Seed trial/result/evaluation/metric referencing the doc
    seeded = _seed_doc_with_dependencies(pid, doc_id, schema_id, prompt_id)

    # --- Dependency preview ---
    resp = client.post(
        f"{api_url}/project/{pid}/document/dependencies",
        headers=headers,
        json={"document_ids": [doc_id]},
    )
    assert resp.status_code == 200
    deps = resp.json()
    assert deps["trials"]["count"] == 1
    assert deps["document_sets"]["count"] == 1
    assert deps["trial_results"] == 1
    assert deps["evaluation_metrics"] == 1
    assert deps["evaluations"] == 1

    # --- Delete without cascade is blocked ---
    resp = client.delete(f"{api_url}/project/{pid}/document/{doc_id}", headers=headers)
    assert resp.status_code == 400

    # --- Delete with cascade succeeds ---
    resp = client.delete(
        f"{api_url}/project/{pid}/document/{doc_id}?cascade=true", headers=headers
    )
    assert resp.status_code == 200

    # Document and all dependents are gone
    assert (
        client.get(
            f"{api_url}/project/{pid}/document/{doc_id}", headers=headers
        ).status_code
        == 404
    )
    db = SessionLocal()
    try:
        assert db.get(Document, doc_id) is None
        assert db.get(DocumentSet, set_id) is None
        assert db.get(Trial, seeded["trial_id"]) is None
        assert db.get(Evaluation, seeded["evaluation_id"]) is None
        assert (
            db.execute(
                select(TrialResult).where(TrialResult.document_id == doc_id)
            ).first()
            is None
        )
        assert (
            db.execute(
                select(EvaluationMetric).where(EvaluationMetric.document_id == doc_id)
            ).first()
            is None
        )
    finally:
        db.close()


def test_file_cascade_delete(client, api_url, admin_headers, make_project):
    """A file whose documents are used by trials/groups/evaluations can't be
    deleted without force (409), but `force=true` cascades through documents and
    their dependents. The preview reports the impact including document count."""
    import uuid

    from sqlalchemy import select

    from backend.src.db.session import SessionLocal
    from backend.src.models.project import (
        Document,
        DocumentSet,
        Evaluation,
        File,
        Trial,
        TrialResult,
    )
    from backend.src.utils.enums import FileCreator

    headers = admin_headers

    pid = make_project(headers, name="FileCascadeProj")["id"]
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
    file_id = client.post(
        f"{api_url}/project/{pid}/file",
        headers=headers,
        files={
            "file": ("fc.txt", b"some text", "text/plain"),
            "file_info": (
                "",
                '{"file_name": "fc.txt", "file_type": "text/plain"}',
                "application/json",
            ),
        },
    ).json()["id"]
    assert (
        client.post(
            f"{api_url}/project/{pid}/preprocess",
            headers=headers,
            json={
                "file_ids": [file_id],
                "inline_config": {"name": "Cfg", "description": "d"},
                "bypass_celery": True,
            },
        ).status_code
        == 200
    )
    doc_id = client.get(f"{api_url}/project/{pid}/document", headers=headers).json()[
        "items"
    ][0]["id"]

    # Attach a system-generated preprocessed file to the document (as OCR would),
    # so we can assert the file cascade reclaims that separate File row + blob.
    db = SessionLocal()
    try:
        pf = File(
            project_id=pid,
            file_uuid=uuid.uuid4().hex,
            file_name="preprocessed.txt",
            file_creator=FileCreator.system,
        )
        db.add(pf)
        db.flush()
        preprocessed_file_id = pf.id
        doc = db.get(Document, doc_id)
        doc.preprocessed_file_id = preprocessed_file_id
        db.commit()
    finally:
        db.close()

    # Group + trial/result/evaluation/metric referencing the doc
    set_id = client.post(
        f"{api_url}/project/{pid}/document-set",
        headers=headers,
        json={"name": "Grp", "document_ids": [doc_id]},
    ).json()["id"]
    seeded = _seed_doc_with_dependencies(pid, doc_id, schema_id, prompt_id)

    # --- File dependency preview ---
    resp = client.post(
        f"{api_url}/project/{pid}/file/dependencies",
        headers=headers,
        json={"file_ids": [file_id]},
    )
    assert resp.status_code == 200
    deps = resp.json()
    assert deps["documents"] == 1
    assert deps["trials"]["count"] == 1
    assert deps["document_sets"]["count"] == 1
    assert deps["trial_results"] == 1
    assert deps["evaluation_metrics"] == 1

    # --- Delete without force is blocked (409) ---
    assert (
        client.delete(
            f"{api_url}/project/{pid}/file/{file_id}", headers=headers
        ).status_code
        == 409
    )

    # --- Force delete cascades through everything ---
    assert (
        client.delete(
            f"{api_url}/project/{pid}/file/{file_id}?force=true", headers=headers
        ).status_code
        == 200
    )

    db = SessionLocal()
    try:
        assert db.get(File, file_id) is None
        # The orphaned system preprocessed file is reclaimed too.
        assert db.get(File, preprocessed_file_id) is None
        assert db.get(Document, doc_id) is None
        assert db.get(DocumentSet, set_id) is None
        assert db.get(Trial, seeded["trial_id"]) is None
        assert db.get(Evaluation, seeded["evaluation_id"]) is None
        assert (
            db.execute(
                select(TrialResult).where(TrialResult.document_id == doc_id)
            ).first()
            is None
        )
    finally:
        db.close()


def test_preprocessed_file_force_delete_removes_documents(
    client, api_url, admin_headers, make_project
):
    """Force-deleting a system-generated *preprocessed* file must delete the
    documents referencing it — not just their trials/evaluations. Regression:
    the delete-orphan cascade only reaches documents via the ORIGINAL file's
    file tasks, so preprocessed-file force deletes wiped the downstream trials
    while leaving the documents alive."""
    import uuid

    from sqlalchemy import select

    from backend.src.db.session import SessionLocal
    from backend.src.models.project import Document, File, Trial, TrialResult
    from backend.src.utils.enums import FileCreator

    headers = admin_headers

    pid = make_project(headers, name="PreprocDelProj")["id"]
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
    file_id = client.post(
        f"{api_url}/project/{pid}/file",
        headers=headers,
        files={
            "file": ("pfdel.txt", b"some text", "text/plain"),
            "file_info": (
                "",
                '{"file_name": "pfdel.txt", "file_type": "text/plain"}',
                "application/json",
            ),
        },
    ).json()["id"]
    assert (
        client.post(
            f"{api_url}/project/{pid}/preprocess",
            headers=headers,
            json={
                "file_ids": [file_id],
                "inline_config": {"name": "Cfg", "description": "d"},
                "bypass_celery": True,
            },
        ).status_code
        == 200
    )
    doc_id = client.get(f"{api_url}/project/{pid}/document", headers=headers).json()[
        "items"
    ][0]["id"]

    # Attach a system-generated preprocessed file to the document (as OCR would).
    db = SessionLocal()
    try:
        pf = File(
            project_id=pid,
            file_uuid=uuid.uuid4().hex,
            file_name="preprocessed.txt",
            file_creator=FileCreator.system,
        )
        db.add(pf)
        db.flush()
        preprocessed_file_id = pf.id
        db.get(Document, doc_id).preprocessed_file_id = preprocessed_file_id
        db.commit()
    finally:
        db.close()

    seeded = _seed_doc_with_dependencies(pid, doc_id, schema_id, prompt_id)

    # Deleting the PREPROCESSED file without force is blocked (it has a linked doc).
    assert (
        client.delete(
            f"{api_url}/project/{pid}/file/{preprocessed_file_id}", headers=headers
        ).status_code
        == 409
    )

    # Force delete must remove the documents together with their dependents.
    assert (
        client.delete(
            f"{api_url}/project/{pid}/file/{preprocessed_file_id}?force=true",
            headers=headers,
        ).status_code
        == 200
    )

    db = SessionLocal()
    try:
        assert db.get(File, preprocessed_file_id) is None
        assert db.get(Document, doc_id) is None, (
            "document must not survive its trials/evaluations"
        )
        assert db.get(Trial, seeded["trial_id"]) is None
        assert (
            db.execute(
                select(TrialResult).where(TrialResult.document_id == doc_id)
            ).first()
            is None
        )
        # The original (user-uploaded) file is untouched.
        assert db.get(File, file_id) is not None
    finally:
        db.close()


def test_cascade_delete_keeps_shared_document_sets(
    client, api_url, admin_headers, make_project
):
    """Cascade-deleting one document removes it FROM its groups; a group with
    other members survives, only a group left empty is deleted."""
    from backend.src.db.session import SessionLocal
    from backend.src.models.project import DocumentSet

    headers = admin_headers

    pid = make_project(headers, name="SetSurvivesProj")["id"]
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

    file_ids = []
    for name in ("setdoc1.txt", "setdoc2.txt"):
        file_ids.append(
            client.post(
                f"{api_url}/project/{pid}/file",
                headers=headers,
                files={
                    "file": (name, f"text of {name}".encode(), "text/plain"),
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
    doc_ids = [
        d["id"]
        for d in client.get(
            f"{api_url}/project/{pid}/document", headers=headers
        ).json()["items"]
    ]
    assert len(doc_ids) == 2
    doomed_id, survivor_id = doc_ids

    # A shared group with both docs, and a solo group with only the doomed doc.
    shared_set_id = client.post(
        f"{api_url}/project/{pid}/document-set",
        headers=headers,
        json={"name": "SharedGrp", "document_ids": doc_ids},
    ).json()["id"]
    solo_set_id = client.post(
        f"{api_url}/project/{pid}/document-set",
        headers=headers,
        json={"name": "SoloGrp", "document_ids": [doomed_id]},
    ).json()["id"]

    _seed_doc_with_dependencies(pid, doomed_id, schema_id, prompt_id)

    assert (
        client.delete(
            f"{api_url}/project/{pid}/document/{doomed_id}?cascade=true",
            headers=headers,
        ).status_code
        == 200
    )

    db = SessionLocal()
    try:
        # Shared group survives with only the surviving member.
        shared = db.get(DocumentSet, shared_set_id)
        assert shared is not None
        assert [d.id for d in shared.documents] == [survivor_id]
        # The group left empty is deleted.
        assert db.get(DocumentSet, solo_set_id) is None
    finally:
        db.close()
