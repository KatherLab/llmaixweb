"""End-to-end evaluation pipeline with a MOCKED LLM.

These used to skip under ``OPENAI_NO_API_CHECK``. The evaluation engine itself is
LLM-free (it compares stored ``TrialResult`` rows against parsed ground truth),
but producing those results requires a trial, which calls the LLM. So the two
full-pipeline tests install a *realistic* fake keyed to the ground-truth file:
for each document, the fake looks up the matching ground-truth row (by locating
the report text inside the prompt) and returns those exact field values — which
is what lets the ``accuracy > 0.9`` assertions hold offline. ``bypass_celery`` is
admin-only, so everything runs as ``admin@example.com``.

Complements ``test_evaluation_metrics.py`` / ``test_value_comparator.py`` (which
unit-test the metric + comparison logic directly).
"""

import json
import re

import pandas as pd

from .fake_llm import make_fake_openai

# Creds spread into every trial-create body; the client itself is mocked.
_LLM_CREDS = {
    "llm_model": "mock-model",
    "api_key": "test-key",
    "base_url": "http://localhost:11434/v1",
}

_BOOL_FIELDS = [
    "shortness of breath",
    "chest pain",
    "leg pain or swelling",
    "heart palpitations",
    "cough",
    "dizziness",
]
_STR_FIELDS = ["location", "side"]


def _norm(value) -> str:
    """Whitespace-insensitive, lowercased key for robust substring matching."""
    return re.sub(r"\s+", "", str(value)).lower()


def _load_gt_rows(path):
    """Return [(normalized_report, {field: typed_value})] for each ground-truth row."""
    if str(path).endswith(".xlsx"):
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.read_csv(path, dtype=str)
    rows = []
    for _, r in df.iterrows():
        fields = {f: str(r[f]).strip().lower() == "true" for f in _BOOL_FIELDS}
        fields.update({f: str(r[f]).strip() for f in _STR_FIELDS})
        rows.append((_norm(r["report"]), fields))
    return rows


def _gt_completion_hook(path):
    """Fake-LLM hook that returns the ground-truth row matching the prompt's report."""
    rows = _load_gt_rows(path)

    def hook(**kwargs):
        blob = _norm(
            " ".join(
                m.get("content", "")
                for m in kwargs.get("messages", [])
                if isinstance(m.get("content"), str)
            )
        )
        best = None
        for sig, fields in rows:
            if sig and sig in blob and (best is None or len(sig) > len(best[0])):
                best = (sig, fields)
        return json.dumps(best[1] if best else {})

    return hook


# Prompt + schema shared by the medical-report pipeline tests.
_MEDICAL_USER_PROMPT = """From the following medical report, extract the following information and return it in JSON format:

shortness of breath: true / false
chest pain: true / false
leg pain or swelling: true / false
heart palpitations: true / false
cough: true / false
dizziness: true / false
location: main / segmental / unknown
side: left / right / bilateral

This is the medical report:
{document_content}
"""

_MEDICAL_SCHEMA_DEF = {
    "type": "object",
    "properties": {
        "shortness of breath": {"type": "boolean"},
        "chest pain": {"type": "boolean"},
        "leg pain or swelling": {"type": "boolean"},
        "heart palpitations": {"type": "boolean"},
        "cough": {"type": "boolean"},
        "dizziness": {"type": "boolean"},
        "location": {"type": "string", "enum": ["main", "segmental", "unknown"]},
        "side": {"type": "string", "enum": ["left", "right", "bilateral"]},
    },
    "required": [
        "shortness of breath",
        "chest pain",
        "leg pain or swelling",
        "heart palpitations",
        "cough",
        "dizziness",
        "location",
        "side",
    ],
}

_MEDICAL_FIELDS = _BOOL_FIELDS + _STR_FIELDS


def _medical_mappings(schema_id):
    return [
        {
            "schema_field": field,
            "ground_truth_field": field,
            "schema_id": schema_id,
            "field_type": "string" if field in _STR_FIELDS else "boolean",
        }
        for field in _MEDICAL_FIELDS
    ]


def test_field_mapping_and_evaluation(client, api_url, files_base_path, admin_headers):
    headers = admin_headers
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "EvalTest"}
    ).json()["id"]

    # Prompt
    prompt_response = client.post(
        f"{api_url}/project/{project_id}/prompt",
        headers=headers,
        json={
            "name": "Prompt",
            "system_prompt": "",
            "user_prompt": _MEDICAL_USER_PROMPT,
            "project_id": project_id,
        },
    )
    assert prompt_response.status_code == 200

    # Schema
    schema_id = client.post(
        f"{api_url}/project/{project_id}/schema",
        headers=headers,
        json={"schema_name": "EvalSchema", "schema_definition": _MEDICAL_SCHEMA_DEF},
    ).json()["id"]

    # Upload ground truth (CSV)
    with open(files_base_path / "reports_with_groundtruth.csv", "rb") as gt_file:
        resp = client.post(
            f"{api_url}/project/{project_id}/groundtruth",
            headers=headers,
            files={"file": ("reports_with_groundtruth.csv", gt_file, "text/csv")},
            data={"format": "csv"},
        )
    assert resp.status_code == 200
    groundtruth_id = resp.json()["id"]

    # Set ID column
    resp = client.put(
        f"{api_url}/project/{project_id}/groundtruth/{groundtruth_id}/id-column",
        headers=headers,
        json={"id_column": "id"},
    )
    assert resp.status_code == 200

    # Create mapping for all fields
    resp = client.post(
        f"{api_url}/project/{project_id}/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping",
        headers=headers,
        json=_medical_mappings(schema_id),
    )
    assert resp.status_code == 200

    # Get mappings
    resp = client.get(
        f"{api_url}/project/{project_id}/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping",
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 8

    # Delete mapping
    resp = client.delete(
        f"{api_url}/project/{project_id}/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping",
        headers=headers,
    )
    assert resp.status_code == 200

    # Auto-map fields (should recreate mappings)
    resp = client.post(
        f"{api_url}/project/{project_id}/groundtruth/{groundtruth_id}/schema/{schema_id}/auto-map",
        headers=headers,
    )
    assert resp.status_code == 200

    # Check mapping status
    resp = client.get(
        f"{api_url}/project/{project_id}/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping/status",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["has_mappings"]

    # Clean up: Delete groundtruth
    resp = client.delete(
        f"{api_url}/project/{project_id}/groundtruth/{groundtruth_id}", headers=headers
    )
    assert resp.status_code == 200


def test_trial_download_and_error_endpoints(
    client, api_url, files_base_path, admin_headers, monkeypatch
):
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai(
            {
                "shortness of breath": True,
                "chest pain": True,
                "leg pain or swelling": False,
                "heart palpitations": False,
                "cough": False,
                "dizziness": False,
                "location": "main",
                "side": "left",
            }
        ),
    )
    headers = admin_headers

    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "DownloadTest"}
    ).json()["id"]

    # Prompt & schema (use the real schema and prompt!)
    prompt_id = client.post(
        f"{api_url}/project/{project_id}/prompt",
        headers=headers,
        json={
            "name": "Prompt",
            "system_prompt": "",
            "user_prompt": _MEDICAL_USER_PROMPT,
            "project_id": project_id,
        },
    ).json()["id"]

    schema_id = client.post(
        f"{api_url}/project/{project_id}/schema",
        headers=headers,
        json={"schema_name": "DL", "schema_definition": _MEDICAL_SCHEMA_DEF},
    ).json()["id"]

    # Upload PDF file and preprocess to get document
    with open(files_base_path / "9874562_text.pdf", "rb") as f:
        file_data = {
            "file": ("9874562.pdf", f, "application/pdf"),
            "file_info": (
                "",
                '{"file_name": "9874562_text.pdf", "file_type": "application/pdf"}',
                "application/json",
            ),
        }
        file_id = client.post(
            f"{api_url}/project/{project_id}/file", headers=headers, files=file_data
        ).json()["id"]

    client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": [file_id],
            "inline_config": {"name": "PDF Config", "description": "Config for PDF"},
            "bypass_celery": True,
        },
    )
    doc_id = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()["items"][0]["id"]

    # Create trial
    trial_id = client.post(
        f"{api_url}/project/{project_id}/trial",
        headers=headers,
        json={
            "schema_id": schema_id,
            "prompt_id": prompt_id,
            "document_ids": [doc_id],
            "bypass_celery": True,
            **_LLM_CREDS,
        },
    ).json()["id"]

    # Download trial results (json/csv)
    resp = client.get(
        f"{api_url}/project/{project_id}/trial/{trial_id}/download?format=json",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/zip")
    resp = client.get(
        f"{api_url}/project/{project_id}/trial/{trial_id}/download?format=csv",
        headers=headers,
    )
    assert resp.status_code == 200

    # Download files as zip
    resp = client.post(
        f"{api_url}/project/{project_id}/file/download-zip",
        headers=headers,
        json={"file_ids": [file_id], "include_metadata": True},
    )
    assert resp.status_code == 200

    # Download document set as zip
    set_id = client.post(
        f"{api_url}/project/{project_id}/document-set",
        headers=headers,
        json={"name": "Set1", "document_ids": [doc_id]},
    ).json()["id"]
    resp = client.post(
        f"{api_url}/project/{project_id}/document-set/{set_id}/download-all",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/zip")


def _run_full_pipeline(client, api_url, headers, files_base_path, gt_name, gt_format):
    """Shared driver for the CSV and XLSX full-pipeline evaluation tests."""
    gt_path = files_base_path / gt_name
    if gt_format == "csv":
        file_type = "text/csv"
        file_metadata = {
            "delimiter": ",",
            "encoding": "utf-8",
            "has_header": True,
            "text_columns": ["report"],
            "case_id_column": "id",
        }
    else:
        file_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        file_metadata = {
            "has_header": True,
            "text_columns": ["report"],
            "case_id_column": "id",
        }

    project_id = client.post(
        f"{api_url}/project",
        headers=headers,
        json={"name": f"EvalPipeline{gt_format.upper()}"},
    ).json()["id"]

    # Upload the report file (row-by-row → one document per report)
    with open(gt_path, "rb") as f:
        file_id = client.post(
            f"{api_url}/project/{project_id}/file",
            headers=headers,
            files={"file": (gt_name, f, file_type)},
            data={
                "file_info": json.dumps(
                    {
                        "file_name": gt_name,
                        "file_type": file_type,
                        "preprocessing_strategy": "row_by_row",
                        "file_metadata": file_metadata,
                    }
                )
            },
        ).json()["id"]

    r = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": [file_id],
            "inline_config": {
                "name": f"{gt_format.upper()} row-by-row",
                "description": "Process per report",
            },
            "bypass_celery": True,
        },
    )
    assert r.status_code == 200, r.text

    docs = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()
    assert docs["items"], "No documents created"
    assert docs["total"] == 8, f"Expected 8 docs, got {docs['total']}"
    doc_ids = [d["id"] for d in docs["items"]]
    doc_names = [d["document_name"] for d in docs["items"]]
    assert any(".pdf" in dn for dn in doc_names), doc_names

    # Prompt + schema
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

    # Ground truth + mappings
    with open(gt_path, "rb") as gt_file:
        groundtruth_id = client.post(
            f"{api_url}/project/{project_id}/groundtruth",
            headers=headers,
            files=[("file", (gt_name, gt_file, file_type))],
            data={"format": gt_format},
        ).json()["id"]
    r = client.put(
        f"{api_url}/project/{project_id}/groundtruth/{groundtruth_id}/id-column",
        headers=headers,
        json={"id_column": "id"},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"{api_url}/project/{project_id}/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping",
        headers=headers,
        json=_medical_mappings(schema_id),
    )
    assert r.status_code == 200, r.text

    # Trial (LLM extraction, mocked to return the matching ground-truth row)
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

    # Evaluate trial vs ground truth
    r = client.post(
        f"{api_url}/project/{project_id}/trial/{trial_id}/evaluate",
        headers=headers,
        params={"groundtruth_id": groundtruth_id},
    )
    assert r.status_code == 200, r.text
    eval_obj = r.json()

    assert eval_obj["trial_id"] == trial_id
    assert eval_obj["groundtruth_id"] == groundtruth_id
    assert "overall_metrics" in eval_obj
    assert "field_summaries" in eval_obj
    assert "document_summaries" in eval_obj
    assert isinstance(eval_obj["document_summaries"], list)
    returned_doc_ids = [doc["document_id"] for doc in eval_obj["document_summaries"]]
    assert set(returned_doc_ids) == set(doc_ids)
    for fs in eval_obj["field_summaries"]:
        assert "field_name" in fs
        assert "accuracy" in fs
        assert "error_count" in fs
        assert "sample_errors" in fs

    assert int(eval_obj["overall_metrics"]["total_documents"]) == len(doc_ids)
    assert float(eval_obj["overall_metrics"]["accuracy"]) > 0.9


def test_evaluation_full_pipeline(
    client, api_url, files_base_path, admin_headers, monkeypatch
):
    """Full pipeline driven by a CSV ground-truth file (row-by-row)."""
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai(
            completion_hook=_gt_completion_hook(
                files_base_path / "reports_with_groundtruth.csv"
            )
        ),
    )
    _run_full_pipeline(
        client,
        api_url,
        admin_headers,
        files_base_path,
        "reports_with_groundtruth.csv",
        "csv",
    )


def test_evaluation_full_pipeline_xlsx(
    client, api_url, files_base_path, admin_headers, monkeypatch
):
    """Same pipeline as the CSV test, driven by an XLSX ground-truth file."""
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai(
            completion_hook=_gt_completion_hook(
                files_base_path / "reports_with_groundtruth.xlsx"
            )
        ),
    )
    _run_full_pipeline(
        client,
        api_url,
        admin_headers,
        files_base_path,
        "reports_with_groundtruth.xlsx",
        "xlsx",
    )
