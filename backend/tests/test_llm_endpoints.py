"""API-level tests for the remaining `/project/llm/*` endpoints.

`/models` and `/test-connection` are already covered by ``test_llm.py``. This
module covers the rest of ``routers/v1/endpoints/llm.py``:

  * ``/test-model``            — model completion probe
  * ``/test-model-schema``     — structured-output probe (needs project+schema)
  * ``/test-vlm-image-support``— VLM image-support probe (different seam)

For each: mocked-success, incomplete-config short-circuit, SSRF / invalid-URL
rejection, and authz (unauthenticated + cross-user project access).

Seams:
  * ``/test-model`` + ``/test-model-schema`` build the OpenAI client via
    ``backend.src.utils.info_extraction.OpenAI`` → patched with the shared
    ``fake_llm.make_fake_openai`` fake.
  * ``/test-vlm-image-support`` calls ``test_remote_image_support`` (imported
    into the router namespace via ``from ... import``), so it is patched at its
    *bound* location: ``backend.src.routers.v1.endpoints.llm.test_remote_image_support``
    (patching the source module ``utils.helpers`` would NOT affect the already
    bound name — see the note in the report).
"""

import pytest

from backend.src.core import config

from .fake_llm import make_fake_openai

# localhost:11434/v1 passes the SSRF blocklist and (empty) ALLOWED_LLM_ENDPOINTS
# allowlist in the test config — same base URL the existing llm tests use.
_GOOD_BASE = "http://localhost:11434/v1"
_LLM_BODY = {
    "api_key": "test-key",
    "base_url": _GOOD_BASE,
    "llm_model": "mock-model",
}


@pytest.fixture
def _no_system_llm_defaults(monkeypatch):
    """Clear the system-wide OpenAI defaults so `incomplete_config` assertions
    hold regardless of the active env file. The CI env (`backend/tests/.env`)
    has no defaults, but `backend/.env.localtest` sets OPENAI_API_KEY/BASE/MODEL,
    which would otherwise satisfy `_resolve_creds` and skip the incomplete branch.
    """
    settings = config._get_settings()
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_API_BASE", None)
    monkeypatch.setattr(settings, "OPENAI_API_MODEL", None)


# Cloud instance-metadata endpoint — must be rejected by the SSRF guard.
_METADATA_BASE = "http://169.254.169.254/v1"
# Disallowed scheme — must also be rejected by validate_user_endpoint.
_BAD_SCHEME_BASE = "file:///etc/passwd"

_OPENAI_SEAM = "backend.src.utils.info_extraction.OpenAI"
_VLM_SEAM = "backend.src.routers.v1.endpoints.llm.test_remote_image_support"


# ---------------------------------------------------------------------------
# /test-model
# ---------------------------------------------------------------------------


def test_test_model_success(client, api_url, user_headers, monkeypatch):
    monkeypatch.setattr(_OPENAI_SEAM, make_fake_openai())
    resp = client.post(
        f"{api_url}/project/llm/test-model", headers=user_headers, json=_LLM_BODY
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("success") is True
    assert "message" in body


def test_test_model_incomplete_config(
    client, api_url, user_headers, monkeypatch, _no_system_llm_defaults
):
    """Omitting creds short-circuits before any client is built."""
    monkeypatch.setattr(_OPENAI_SEAM, make_fake_openai())
    # No api_key / base_url / model, and system defaults are cleared, so the
    # endpoint must report incomplete config.
    resp = client.post(
        f"{api_url}/project/llm/test-model", headers=user_headers, json={}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("success") is False
    assert body.get("error_type") == "incomplete_config"


def test_test_model_ssrf_metadata_rejected(client, api_url, user_headers, monkeypatch):
    """A cloud-metadata base_url is rejected without calling the provider."""

    # If the SSRF guard failed to block, the fake would raise (its create is
    # fine, but we assert we never reach it via the invalid_url shape).
    def _boom(*a, **k):
        raise AssertionError("provider client must not be built for a blocked URL")

    monkeypatch.setattr(_OPENAI_SEAM, _boom)
    resp = client.post(
        f"{api_url}/project/llm/test-model",
        headers=user_headers,
        json={**_LLM_BODY, "base_url": _METADATA_BASE},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("success") is False
    assert body.get("error_type") == "invalid_url"


def test_test_model_bad_scheme_rejected(client, api_url, user_headers, monkeypatch):
    monkeypatch.setattr(_OPENAI_SEAM, make_fake_openai())
    resp = client.post(
        f"{api_url}/project/llm/test-model",
        headers=user_headers,
        json={**_LLM_BODY, "base_url": _BAD_SCHEME_BASE},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json().get("error_type") == "invalid_url"


def test_test_model_unauthenticated(client, api_url):
    resp = client.post(f"{api_url}/project/llm/test-model", json=_LLM_BODY)
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# /test-model-schema
# ---------------------------------------------------------------------------


def test_test_model_schema_success(
    client, api_url, user_headers, make_project, make_schema, monkeypatch
):
    monkeypatch.setattr(_OPENAI_SEAM, make_fake_openai())
    project = make_project(user_headers, name="LLM Schema Test")
    schema = make_schema(user_headers, project["id"])
    resp = client.post(
        f"{api_url}/project/llm/test-model-schema",
        headers=user_headers,
        json={**_LLM_BODY, "project_id": project["id"], "schema_id": schema["id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("success") is True
    assert body.get("request_accepted") is True
    assert body.get("supports_structured_output") is True


def test_test_model_schema_incomplete_config(
    client, api_url, user_headers, make_project, monkeypatch, _no_system_llm_defaults
):
    monkeypatch.setattr(_OPENAI_SEAM, make_fake_openai())
    project = make_project(user_headers, name="LLM Schema Incomplete")
    # Missing api_key/base_url/model → incomplete_config (checked before schema).
    resp = client.post(
        f"{api_url}/project/llm/test-model-schema",
        headers=user_headers,
        json={"project_id": project["id"], "schema_id": 1},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("success") is False
    assert body.get("error_type") == "incomplete_config"


def test_test_model_schema_missing_schema_id(
    client, api_url, user_headers, make_project, monkeypatch
):
    monkeypatch.setattr(_OPENAI_SEAM, make_fake_openai())
    project = make_project(user_headers, name="LLM Schema Missing ID")
    resp = client.post(
        f"{api_url}/project/llm/test-model-schema",
        headers=user_headers,
        json={**_LLM_BODY, "project_id": project["id"]},  # schema_id omitted → None
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("success") is False
    assert body.get("error_type") == "missing_schema"


def test_test_model_schema_schema_not_found(
    client, api_url, user_headers, make_project, monkeypatch
):
    monkeypatch.setattr(_OPENAI_SEAM, make_fake_openai())
    project = make_project(user_headers, name="LLM Schema Not Found")
    resp = client.post(
        f"{api_url}/project/llm/test-model-schema",
        headers=user_headers,
        json={**_LLM_BODY, "project_id": project["id"], "schema_id": 999999},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("success") is False
    assert body.get("error_type") == "schema_not_found"


def test_test_model_schema_ssrf_rejected(
    client, api_url, user_headers, make_project, make_schema, monkeypatch
):
    """SSRF check runs before DB/project access."""

    def _boom(*a, **k):
        raise AssertionError("provider client must not be built for a blocked URL")

    monkeypatch.setattr(_OPENAI_SEAM, _boom)
    project = make_project(user_headers, name="LLM Schema SSRF")
    schema = make_schema(user_headers, project["id"])
    resp = client.post(
        f"{api_url}/project/llm/test-model-schema",
        headers=user_headers,
        json={
            **_LLM_BODY,
            "base_url": _METADATA_BASE,
            "project_id": project["id"],
            "schema_id": schema["id"],
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json().get("error_type") == "invalid_url"


def test_test_model_schema_project_not_found(
    client, api_url, user_headers, monkeypatch
):
    monkeypatch.setattr(_OPENAI_SEAM, make_fake_openai())
    resp = client.post(
        f"{api_url}/project/llm/test-model-schema",
        headers=user_headers,
        json={**_LLM_BODY, "project_id": 999999, "schema_id": 1},
    )
    assert resp.status_code == 404, resp.text


def test_test_model_schema_cross_user_forbidden(
    client, api_url, user_headers, login, make_project, make_schema, monkeypatch
):
    """Another user's project must not leak its schema (403)."""
    monkeypatch.setattr(_OPENAI_SEAM, make_fake_openai())
    owner_headers = login("another@example.com", "Anotherpassword1")
    project = make_project(owner_headers, name="LLM Schema Owned By Another")
    schema = make_schema(owner_headers, project["id"])
    # `user_headers` (test@example.com) is NOT the owner.
    resp = client.post(
        f"{api_url}/project/llm/test-model-schema",
        headers=user_headers,
        json={**_LLM_BODY, "project_id": project["id"], "schema_id": schema["id"]},
    )
    assert resp.status_code == 403, resp.text


def test_test_model_schema_unauthenticated(client, api_url):
    resp = client.post(
        f"{api_url}/project/llm/test-model-schema",
        json={**_LLM_BODY, "project_id": 1, "schema_id": 1},
    )
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# /test-vlm-image-support
# ---------------------------------------------------------------------------


def test_vlm_image_support_supported(client, api_url, user_headers, monkeypatch):
    monkeypatch.setattr(_VLM_SEAM, lambda **kw: True)
    resp = client.post(
        f"{api_url}/project/llm/test-vlm-image-support",
        headers=user_headers,
        json=_LLM_BODY,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("supported") is True
    assert "message" in body


def test_vlm_image_support_unsupported(client, api_url, user_headers, monkeypatch):
    monkeypatch.setattr(_VLM_SEAM, lambda **kw: False)
    resp = client.post(
        f"{api_url}/project/llm/test-vlm-image-support",
        headers=user_headers,
        json=_LLM_BODY,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("supported") is False


def test_vlm_image_support_appends_chat_completions(
    client, api_url, user_headers, monkeypatch
):
    """The base_url is normalized to end with /chat/completions before calling."""
    seen = {}

    def _spy(**kw):
        seen.update(kw)
        return True

    monkeypatch.setattr(_VLM_SEAM, _spy)
    resp = client.post(
        f"{api_url}/project/llm/test-vlm-image-support",
        headers=user_headers,
        json=_LLM_BODY,
    )
    assert resp.status_code == 200, resp.text
    assert seen.get("api_url") == _GOOD_BASE.rstrip("/") + "/chat/completions"
    assert seen.get("model") == "mock-model"


def test_vlm_image_support_error_is_sanitized(
    client, api_url, user_headers, monkeypatch
):
    """An upstream exception is captured as a category-only message + error id,
    never echoing the raw exception string (SSRF exfiltration guard)."""

    def _raise(**kw):
        raise RuntimeError("internal service secret leaked in body: TOPSECRET")

    monkeypatch.setattr(_VLM_SEAM, _raise)
    resp = client.post(
        f"{api_url}/project/llm/test-vlm-image-support",
        headers=user_headers,
        json=_LLM_BODY,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("supported") is False
    assert "TOPSECRET" not in body.get("message", "")
    assert body.get("error_id")


def test_vlm_image_support_incomplete_config(
    client, api_url, user_headers, monkeypatch, _no_system_llm_defaults
):
    def _boom(**kw):
        raise AssertionError("must not call provider when config incomplete")

    monkeypatch.setattr(_VLM_SEAM, _boom)
    # No model → incomplete config (uses the VLM's own shape: supported/message).
    resp = client.post(
        f"{api_url}/project/llm/test-vlm-image-support",
        headers=user_headers,
        json={"api_key": "test-key", "base_url": _GOOD_BASE},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("supported") is False
    assert "incomplete" in body.get("message", "").lower()


def test_vlm_image_support_ssrf_rejected(client, api_url, user_headers, monkeypatch):
    def _boom(**kw):
        raise AssertionError("must not call provider for a blocked URL")

    monkeypatch.setattr(_VLM_SEAM, _boom)
    resp = client.post(
        f"{api_url}/project/llm/test-vlm-image-support",
        headers=user_headers,
        json={**_LLM_BODY, "base_url": _METADATA_BASE},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("supported") is False
    assert "not allowed" in body.get("message", "").lower()


def test_vlm_image_support_unauthenticated(client, api_url):
    resp = client.post(f"{api_url}/project/llm/test-vlm-image-support", json=_LLM_BODY)
    assert resp.status_code == 401, resp.text
