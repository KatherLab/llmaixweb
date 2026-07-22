"""API-level tests for ``routers/v1/endpoints/evaluations.py``.

These exercise the stored-evaluation read/compare/batch/errors/download/delete
endpoints. Producing a stored ``Evaluation`` requires the full extraction
pipeline (files → row-by-row preprocess → schema/prompt → ground truth +
mappings → trial → evaluate), so we reuse the proven helpers/constants from
``test_evaluation_pipeline`` and mock the LLM with the ground-truth-keyed fake.

The pipeline (real preprocessing of an 8-row CSV) is slow, so it runs **once**
per test and the resulting ids are reused across many assertions. A couple of
lightweight negative tests only need a bare project.
"""

import json

from .fake_llm import make_fake_openai
from .test_evaluation_pipeline import (
    _LLM_CREDS,
    _MEDICAL_SCHEMA_DEF,
    _MEDICAL_USER_PROMPT,
    _gt_completion_hook,
    _medical_mappings,
)

_GT_NAME = "reports_with_groundtruth.csv"
_GT_TYPE = "text/csv"
_CSV_FILE_METADATA = {
    "delimiter": ",",
    "encoding": "utf-8",
    "has_header": True,
    "text_columns": ["report"],
    "case_id_column": "id",
}


def _upload_groundtruth(
    client, api_url, headers, project_id, schema_id, files_base_path
):
    """Upload the GT file, set its id-column, and map all fields. Returns gt_id."""
    gt_path = files_base_path / _GT_NAME
    with open(gt_path, "rb") as gt_file:
        gt_id = client.post(
            f"{api_url}/project/{project_id}/groundtruth",
            headers=headers,
            files=[("file", (_GT_NAME, gt_file, _GT_TYPE))],
            data={"format": "csv"},
        ).json()["id"]
    r = client.put(
        f"{api_url}/project/{project_id}/groundtruth/{gt_id}/id-column",
        headers=headers,
        json={"id_column": "id"},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"{api_url}/project/{project_id}/groundtruth/{gt_id}/schema/{schema_id}/mapping",
        headers=headers,
        json=_medical_mappings(schema_id),
    )
    assert r.status_code == 200, r.text
    return gt_id


def _build_evaluated_pipeline(client, api_url, headers, files_base_path):
    """Run the full pipeline once and return a dict of the created ids + the
    first evaluation payload (from the trial ``/evaluate`` endpoint)."""
    gt_path = files_base_path / _GT_NAME

    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "EvalAPI"}
    ).json()["id"]

    # Upload the report file row-by-row → one document per report.
    with open(gt_path, "rb") as f:
        file_id = client.post(
            f"{api_url}/project/{project_id}/file",
            headers=headers,
            files={"file": (_GT_NAME, f, _GT_TYPE)},
            data={
                "file_info": json.dumps(
                    {
                        "file_name": _GT_NAME,
                        "file_type": _GT_TYPE,
                        "preprocessing_strategy": "row_by_row",
                        "file_metadata": _CSV_FILE_METADATA,
                    }
                )
            },
        ).json()["id"]

    r = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": [file_id],
            "inline_config": {"name": "row-by-row", "description": "per report"},
            "bypass_celery": True,
        },
    )
    assert r.status_code == 200, r.text

    docs = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()
    doc_ids = [d["id"] for d in docs["items"]]
    assert doc_ids, "No documents created"

    prompt_id = client.post(
        f"{api_url}/project/{project_id}/prompt",
        headers=headers,
        json={
            "name": "EvalPrompt",
            "system_prompt": "",
            "user_prompt": _MEDICAL_USER_PROMPT,
            "project_id": project_id,
        },
    ).json()["id"]
    schema_id = client.post(
        f"{api_url}/project/{project_id}/schema",
        headers=headers,
        json={"schema_name": "EvalSchema", "schema_definition": _MEDICAL_SCHEMA_DEF},
    ).json()["id"]

    gt_id = _upload_groundtruth(
        client, api_url, headers, project_id, schema_id, files_base_path
    )

    trial_id = client.post(
        f"{api_url}/project/{project_id}/trial",
        headers=headers,
        json={
            "schema_id": schema_id,
            "prompt_id": prompt_id,
            "document_ids": doc_ids,
            "bypass_celery": True,
            **_LLM_CREDS,
        },
    ).json()["id"]

    r = client.post(
        f"{api_url}/project/{project_id}/trial/{trial_id}/evaluate",
        headers=headers,
        params={"groundtruth_id": gt_id},
    )
    assert r.status_code == 200, r.text
    evaluation = r.json()

    return {
        "project_id": project_id,
        "schema_id": schema_id,
        "trial_id": trial_id,
        "groundtruth_id": gt_id,
        "doc_ids": doc_ids,
        "evaluation": evaluation,
    }


def test_evaluations_api_endpoints(
    client, api_url, files_base_path, admin_headers, user_headers, monkeypatch
):
    """One full pipeline run, then exercise every read/compare/batch/download
    /errors/delete endpoint plus authz negatives against the produced ids."""
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai(
            completion_hook=_gt_completion_hook(files_base_path / _GT_NAME)
        ),
    )
    headers = admin_headers

    ctx = _build_evaluated_pipeline(client, api_url, headers, files_base_path)
    project_id = ctx["project_id"]
    schema_id = ctx["schema_id"]
    trial_id = ctx["trial_id"]
    gt_id = ctx["groundtruth_id"]
    doc_ids = ctx["doc_ids"]
    eval1 = ctx["evaluation"]
    eval1_id = eval1["id"]

    assert eval1["trial_id"] == trial_id
    assert eval1["groundtruth_id"] == gt_id

    # --- LIST -----------------------------------------------------------
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation",
        headers=headers,
        params={"groundtruth_id": gt_id},
    )
    assert r.status_code == 200, r.text
    listing = r.json()
    assert isinstance(listing, list)
    ids_in_list = [item["id"] for item in listing]
    assert eval1_id in ids_in_list
    first = next(i for i in listing if i["id"] == eval1_id)
    assert first["trial_id"] == trial_id
    assert first["groundtruth_id"] == gt_id
    # document_count is derived from overall metrics total_documents.
    assert first["document_count"] == len(doc_ids)

    # List with a nonexistent ground truth → 404.
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation",
        headers=headers,
        params={"groundtruth_id": 999999},
    )
    assert r.status_code == 404

    # --- DETAIL ---------------------------------------------------------
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/{eval1_id}", headers=headers
    )
    assert r.status_code == 200, r.text
    detail = r.json()
    assert detail["id"] == eval1_id
    assert detail["trial_id"] == trial_id
    assert detail["groundtruth_id"] == gt_id
    assert detail["model"] == _LLM_CREDS["llm_model"]
    assert detail["document_count"] == len(doc_ids)
    assert isinstance(detail["fields"], dict) and detail["fields"]
    assert isinstance(detail["documents"], list) and detail["documents"]
    # _enrich_document_metrics adds field_details + a resolved document_name.
    for d in detail["documents"]:
        assert "field_details" in d

    # Nonexistent evaluation → 404.
    r = client.get(f"{api_url}/project/{project_id}/evaluation/999999", headers=headers)
    assert r.status_code == 404

    # --- PER-DOCUMENT ---------------------------------------------------
    doc_id = doc_ids[0]
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/{eval1_id}/document/{doc_id}",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    doc_detail = r.json()
    assert doc_detail["document_id"] == doc_id
    assert doc_detail["total_fields"] == len(_medical_mappings(schema_id))
    assert isinstance(doc_detail["field_details"], dict)

    # Document not part of the evaluation → 404.
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/{eval1_id}/document/999999",
        headers=headers,
    )
    assert r.status_code == 404

    # --- ERRORS ---------------------------------------------------------
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/{eval1_id}/errors",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)
    # Filter params are accepted (near-perfect eval → likely empty list).
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/{eval1_id}/errors",
        headers=headers,
        params={"field_name": "cough", "limit": 10},
    )
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)

    # --- DOWNLOAD (csv / xlsx / zip) -----------------------------------
    r = client.get(
        f"{api_url}/project/{project_id}/evaluations/download",
        headers=headers,
        params={"evaluation_ids": [eval1_id], "format": "csv"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert b"Evaluation ID" in r.content

    r = client.get(
        f"{api_url}/project/{project_id}/evaluations/download",
        headers=headers,
        params={"evaluation_ids": [eval1_id], "format": "xlsx"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert r.content[:2] == b"PK"  # xlsx is a zip container

    r = client.get(
        f"{api_url}/project/{project_id}/evaluations/download",
        headers=headers,
        params={
            "evaluation_ids": [eval1_id],
            "format": "zip",
            "include_field_details": True,
            "include_errors": True,
        },
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/zip")

    # No evaluation_ids → 400.
    r = client.get(
        f"{api_url}/project/{project_id}/evaluations/download",
        headers=headers,
        params={"evaluation_ids": [""], "format": "csv"},
    )
    assert r.status_code == 400

    # --- COMPARE (needs >= 2 evals: evaluate the same trial vs a 2nd GT) --
    gt2_id = _upload_groundtruth(
        client, api_url, headers, project_id, schema_id, files_base_path
    )
    r = client.post(
        f"{api_url}/project/{project_id}/trial/{trial_id}/evaluate",
        headers=headers,
        params={"groundtruth_id": gt2_id},
    )
    assert r.status_code == 200, r.text
    eval2_id = r.json()["id"]
    assert eval2_id != eval1_id

    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/compare",
        headers=headers,
        params={"evaluation_ids": [eval1_id, eval2_id]},
    )
    assert r.status_code == 200, r.text
    comparison = r.json()
    assert len(comparison["evaluations"]) == 2
    compared_ids = {e["id"] for e in comparison["evaluations"]}
    assert compared_ids == {eval1_id, eval2_id}
    assert "accuracy" in comparison["overall_comparison"]
    assert comparison["field_comparison"]
    assert comparison["model_comparison"]

    # Compare with no valid ids → 404.
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/compare",
        headers=headers,
        params={"evaluation_ids": [999999]},
    )
    assert r.status_code == 404

    # --- BATCH ----------------------------------------------------------
    # Cached (force_recalculate=False): should reuse the existing evaluation id.
    r = client.post(
        f"{api_url}/project/{project_id}/evaluation/batch",
        headers=headers,
        json={
            "trial_ids": [trial_id],
            "groundtruth_id": gt_id,
            "force_recalculate": False,
        },
    )
    assert r.status_code == 200, r.text
    batch = r.json()
    assert isinstance(batch, list) and len(batch) == 1
    assert batch[0]["id"] == eval1_id
    assert batch[0]["trial_id"] == trial_id

    # force_recalculate=True: deletes the cached row and returns a *fresh* eval.
    r = client.post(
        f"{api_url}/project/{project_id}/evaluation/batch",
        headers=headers,
        json={
            "trial_ids": [trial_id],
            "groundtruth_id": gt_id,
            "force_recalculate": True,
        },
    )
    assert r.status_code == 200, r.text
    fresh = r.json()[0]
    assert fresh["id"] != eval1_id
    assert fresh["trial_id"] == trial_id
    eval1_id = fresh["id"]  # eval1_id was deleted by the recalculation

    # Batch with an unknown trial only → all failed → 400.
    r = client.post(
        f"{api_url}/project/{project_id}/evaluation/batch",
        headers=headers,
        json={"trial_ids": [999999], "groundtruth_id": gt_id},
    )
    assert r.status_code == 400

    # Batch with an unknown ground truth → 404.
    r = client.post(
        f"{api_url}/project/{project_id}/evaluation/batch",
        headers=headers,
        json={"trial_ids": [trial_id], "groundtruth_id": 999999},
    )
    assert r.status_code == 404

    # --- AUTHZ NEGATIVES (another user hitting the admin's project) -----
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/{eval1_id}",
        headers=user_headers,
    )
    assert r.status_code in (403, 404)
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation",
        headers=user_headers,
        params={"groundtruth_id": gt_id},
    )
    assert r.status_code in (403, 404)
    r = client.delete(
        f"{api_url}/project/{project_id}/evaluation/{eval1_id}",
        headers=user_headers,
    )
    assert r.status_code in (403, 404)

    # --- DELETE ---------------------------------------------------------
    r = client.delete(
        f"{api_url}/project/{project_id}/evaluation/{eval2_id}", headers=headers
    )
    assert r.status_code == 204, r.text
    # Gone now.
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/{eval2_id}", headers=headers
    )
    assert r.status_code == 404
    # Deleting again → 404.
    r = client.delete(
        f"{api_url}/project/{project_id}/evaluation/{eval2_id}", headers=headers
    )
    assert r.status_code == 404


def test_evaluation_cross_project_idor_and_errors(
    client, api_url, files_base_path, admin_headers, monkeypatch
):
    """Cross-project IDOR + errors-enrichment/filtering.

    Builds one real evaluation with a *fixed wrong* fake LLM (guarantees
    per-field errors), then:

    1. Confirms every by-id endpoint scopes the evaluation to the trial's
       project: requesting the eval under a *different* project the caller
       owns returns 404 ``evaluation_not_found_for_project`` (never the row),
       and a cross-project DELETE does not remove it.
    2. Exercises the errors endpoint enrichment (document_name + context) and
       the field_name / error_type / limit filter branches, which the near
       perfect pipeline in ``test_evaluations_api_endpoints`` can't reach.
    """
    # Fixed answer that will disagree with most ground-truth rows → real errors.
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai(
            {
                "shortness of breath": False,
                "chest pain": False,
                "leg pain or swelling": False,
                "heart palpitations": False,
                "cough": False,
                "dizziness": False,
                "location": "unknown",
                "side": "left",
            }
        ),
    )
    headers = admin_headers

    ctx = _build_evaluated_pipeline(client, api_url, headers, files_base_path)
    project_id = ctx["project_id"]
    eval_id = ctx["evaluation"]["id"]
    doc_id = ctx["doc_ids"][0]

    # A second project owned by the SAME caller — the evaluation is not reachable
    # through it because its trial lives in `project_id`.
    other_pid = client.post(
        f"{api_url}/project", headers=headers, json={"name": "EvalIDOROther"}
    ).json()["id"]

    expected = "evaluations.evaluation_not_found_for_project"

    r = client.get(
        f"{api_url}/project/{other_pid}/evaluation/{eval_id}", headers=headers
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["code"] == expected

    r = client.get(
        f"{api_url}/project/{other_pid}/evaluation/{eval_id}/errors", headers=headers
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["code"] == expected

    r = client.get(
        f"{api_url}/project/{other_pid}/evaluation/{eval_id}/document/{doc_id}",
        headers=headers,
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["code"] == expected

    r = client.delete(
        f"{api_url}/project/{other_pid}/evaluation/{eval_id}", headers=headers
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["code"] == expected

    # The failed cross-project DELETE must not have removed the row: it's still
    # readable under its own project.
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/{eval_id}", headers=headers
    )
    assert r.status_code == 200, r.text

    # --- ERRORS enrichment + filtering (correct project) -----------------
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/{eval_id}/errors", headers=headers
    )
    assert r.status_code == 200, r.text
    errors = r.json()
    assert isinstance(errors, list)
    assert errors, "fixed-wrong fake should have produced field errors"
    for e in errors:
        # Enrichment: document name resolved from the original file, plus a
        # text context snippet (both come from the batch doc-info join).
        assert e["document_name"] == _GT_NAME
        assert "context" in e and isinstance(e["context"], str) and e["context"]
        assert e["error_type"]

    # field_name filter → only that field's errors come back.
    target_field = errors[0]["field_name"]
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/{eval_id}/errors",
        headers=headers,
        params={"field_name": target_field},
    )
    assert r.status_code == 200, r.text
    filtered = r.json()
    assert filtered
    assert all(e["field_name"] == target_field for e in filtered)

    # error_type filter → only that error type comes back.
    target_type = errors[0]["error_type"]
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/{eval_id}/errors",
        headers=headers,
        params={"error_type": target_type},
    )
    assert r.status_code == 200, r.text
    typed = r.json()
    assert typed
    assert all(e["error_type"] == target_type for e in typed)

    # limit caps the number of returned rows.
    r = client.get(
        f"{api_url}/project/{project_id}/evaluation/{eval_id}/errors",
        headers=headers,
        params={"limit": 1},
    )
    assert r.status_code == 200, r.text
    assert len(r.json()) <= 1


def test_evaluation_batch_caps_and_compare_download_caps(
    client, api_url, admin_headers, make_project
):
    """The three request-size caps are enforced before any heavy work.

    Each cap is checked before the project lookup, so these need no real
    evaluation — only that the endpoint rejects an oversized request with the
    documented 400 code.
    """
    project = make_project(admin_headers, name="EvalCaps")
    pid = project["id"]

    # compare: > 10 evaluation ids → 400 too_many_compare.
    r = client.get(
        f"{api_url}/project/{pid}/evaluation/compare",
        headers=admin_headers,
        params={"evaluation_ids": list(range(1, 12))},
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["code"] == "evaluations.too_many_compare"

    # download: > 50 evaluation ids → 400 too_many_download.
    r = client.get(
        f"{api_url}/project/{pid}/evaluations/download",
        headers=admin_headers,
        params={"evaluation_ids": [str(i) for i in range(1, 52)], "format": "csv"},
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["code"] == "evaluations.too_many_download"

    # batch: > 200 trial ids → 400 too_many_trials.
    r = client.post(
        f"{api_url}/project/{pid}/evaluation/batch",
        headers=admin_headers,
        json={"trial_ids": list(range(1, 202)), "groundtruth_id": 1},
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["code"] == "evaluations.too_many_trials"


def test_download_evaluation_ids_comma_and_repeated_forms(
    client, api_url, admin_headers, make_project
):
    """The download endpoint parses both the repeated-param and the legacy
    comma-joined single-param forms, splitting on commas so each id counts
    individually (this is what makes multi-eval exports work).
    """
    project = make_project(admin_headers, name="EvalDownloadParse")
    pid = project["id"]

    # Comma-joined single param of unknown-but-valid ids → parses past the 400
    # gate to a 404 (no such evaluations in this project).
    r = client.get(
        f"{api_url}/project/{pid}/evaluations/download",
        headers=admin_headers,
        params={"evaluation_ids": "999998,999999", "format": "csv"},
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["code"] == "evaluations.no_evaluations_found"

    # A single comma-joined param with 51 ids is split to 51 and trips the
    # per-request cap — proving commas are counted individually, not as one id.
    r = client.get(
        f"{api_url}/project/{pid}/evaluations/download",
        headers=admin_headers,
        params={
            "evaluation_ids": ",".join(str(i) for i in range(1, 52)),
            "format": "csv",
        },
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["code"] == "evaluations.too_many_download"


def test_compare_too_many_ids_before_project_check(client, api_url, admin_headers):
    """The compare cap fires before the project lookup (defense-in-depth):
    an oversized request is rejected 400 even for a project id that doesn't
    exist, rather than leaking a 404."""
    r = client.get(
        f"{api_url}/project/999999/evaluation/compare",
        headers=admin_headers,
        params={"evaluation_ids": list(range(1, 12))},
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["code"] == "evaluations.too_many_compare"


def test_evaluation_read_endpoints_unknown_project(client, api_url, admin_headers):
    """Endpoints on a nonexistent project should 404 (project lookup first)."""
    r = client.get(
        f"{api_url}/project/999999/evaluation",
        headers=admin_headers,
        params={"groundtruth_id": 1},
    )
    assert r.status_code == 404
    r = client.get(f"{api_url}/project/999999/evaluation/1", headers=admin_headers)
    assert r.status_code == 404
    r = client.get(
        f"{api_url}/project/999999/evaluation/1/errors", headers=admin_headers
    )
    assert r.status_code == 404


def test_evaluation_endpoints_require_auth(client, api_url):
    """Unauthenticated requests are rejected."""
    r = client.get(f"{api_url}/project/1/evaluation", params={"groundtruth_id": 1})
    assert r.status_code == 401


def test_download_unknown_evaluation_ids(client, api_url, admin_headers, make_project):
    """Downloading evaluation ids that do not belong to the project → 404."""
    project = make_project(admin_headers, name="EvalDownloadEmpty")
    r = client.get(
        f"{api_url}/project/{project['id']}/evaluations/download",
        headers=admin_headers,
        params={"evaluation_ids": [999999], "format": "csv"},
    )
    assert r.status_code == 404

    # Non-integer ids → 400 (parse failure).
    r = client.get(
        f"{api_url}/project/{project['id']}/evaluations/download",
        headers=admin_headers,
        params={"evaluation_ids": ["abc"], "format": "csv"},
    )
    assert r.status_code == 400
