"""LLM router + provider-facing tests.

The model-listing / connection-test endpoints (`/project/llm/*`) call out to an
OpenAI-compatible provider. In CI there is no provider, so the outbound call is
stubbed at its single seam — the module-level ``backend.src.utils.info_extraction.OpenAI``
symbol — via the shared ``fake_llm.make_fake_openai`` helper. That lets the
endpoint code run for real (auth, SSRF/allowlist validation, response shaping)
while the network call is deterministic and offline.

The two ``test_llm_json_schema_*`` tests are different: they exercise a *real*
LLM's ``response_format=json_schema`` adherence, which is a property of the
provider, not of our code. Mocking them would make their assertions vacuous, so
they stay gated behind ``OPENAI_NO_API_CHECK`` and only run against a live API.
"""

import pytest

from .fake_llm import make_fake_openai

# A localhost base URL that passes the SSRF + ALLOWED_LLM_ENDPOINTS checks in the
# test config (same one the trial tests use). The endpoints require api_key +
# base_url to be present before they build the (mocked) client, so both are sent
# explicitly rather than relying on the unset system defaults.
_LLM_BODY = {"api_key": "test-key", "base_url": "http://localhost:11434/v1"}


def test_get_available_llm_models(client, api_url, user_headers, monkeypatch):
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai(models=("gpt-4o-mini", "gpt-4o")),
    )
    resp = client.post(
        f"{api_url}/project/llm/models", headers=user_headers, json=_LLM_BODY
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("success") is True
    models = data.get("models")
    assert isinstance(models, list) and len(models) > 0


def test_test_llm_connection(client, api_url, user_headers, monkeypatch):
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai(),
    )
    resp = client.post(
        f"{api_url}/project/llm/test-connection", headers=user_headers, json=_LLM_BODY
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("success") in (True, "success")


def test_llm_json_schema_enforcement():
    """Test that the LLM respects JSON schema constraints via response_format.

    This is a minimal standalone test that:
    1. Directly initializes an OpenAI client with the test config
    2. Defines a simple JSON schema with specific field types
    3. Sends a minimal prompt that doesn't describe the full structure
    4. Verifies the LLM returns valid JSON matching the schema

    This tests whether the JSON schema enforcement (via response_format)
    is working correctly, independent of prompt engineering.
    """
    from openai import OpenAI

    from backend.src.core.config import settings

    if settings.OPENAI_NO_API_CHECK:
        pytest.skip("Skipping LLM models test due to OPENAI_NO_API_CHECK setting")

    # Initialize OpenAI client directly
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
    )

    # Define a schema with specific types
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "active": {"type": "boolean"},
            "score": {"type": "number"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["name", "age", "active", "score", "tags"],
    }

    # Minimal prompt - doesn't describe field structure
    document_text = """John Smith is 35 years old. He is currently active in the project.
    His performance score is 4.5 out of 5. His skills include Python, Machine Learning, and Data Analysis."""

    messages = [
        {
            "role": "system",
            "content": "Extract person information from the text and return as JSON.",
        },
        {"role": "user", "content": f"Text: {document_text}"},
    ]

    # Call with json_schema response format
    response = client.chat.completions.create(
        model=settings.OPENAI_API_MODEL,
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "person_schema",
                "schema": schema,
            },
        },
    )

    # Check finish reason
    finish_reason = response.choices[0].finish_reason
    assert finish_reason == "stop", f"Model did not finish cleanly: {finish_reason}"

    # Parse and validate response
    import json

    result = json.loads(response.choices[0].message.content)

    # Verify structure - all required fields must be present
    assert "name" in result, "Missing required field: name"
    assert "age" in result, "Missing required field: age"
    assert "active" in result, "Missing required field: active"
    assert "score" in result, "Missing required field: score"
    assert "tags" in result, "Missing required field: tags"

    # Verify types
    assert isinstance(result["name"], str), (
        f"'name' should be string, got {type(result['name'])}"
    )
    assert isinstance(result["age"], int), (
        f"'age' should be integer, got {type(result['age'])}"
    )
    assert isinstance(result["active"], bool), (
        f"'active' should be boolean, got {type(result['active'])}"
    )
    assert isinstance(result["score"], (int, float)), (
        f"'score' should be number, got {type(result['score'])}"
    )
    assert isinstance(result["tags"], list), (
        f"'tags' should be array, got {type(result['tags'])}"
    )

    # Verify values are reasonable
    assert result["age"] > 0 and result["age"] < 150, (
        f"Age seems invalid: {result['age']}"
    )
    assert result["active"] is True, f"Expected active=True, got {result['active']}"
    assert len(result["tags"]) > 0, "Tags array should not be empty"

    print(f"JSON schema enforcement test passed! Result: {result}")


def test_llm_json_schema_with_minimal_data():
    """Test LLM structured output when document has minimal/ambiguous data.

    This test verifies how the LLM handles extraction when the source text
    doesn't contain all the information needed for the schema fields.
    """
    from openai import OpenAI

    from backend.src.core.config import settings

    if settings.OPENAI_NO_API_CHECK:
        pytest.skip("Skipping LLM models test due to OPENAI_NO_API_CHECK setting")

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
    )

    # Schema requiring fields that may not be in the text
    schema = {
        "type": "object",
        "properties": {
            "patient": {"type": "string"},
            "diagnosis": {"type": "string"},
            "location": {"type": "string"},
        },
        "required": ["patient", "diagnosis", "location"],
    }

    # Minimal text - similar to the row-by-row CSV preprocessing
    # Only contains diagnosis and location, NOT the patient name
    document_text = "Flu Leipzig"

    messages = [
        {
            "role": "system",
            "content": "Extract the requested information from the text.",
        },
        {"role": "user", "content": f"Text: {document_text}"},
    ]

    response = client.chat.completions.create(
        model=settings.OPENAI_API_MODEL,
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "medical_schema",
                "schema": schema,
            },
        },
    )

    finish_reason = response.choices[0].finish_reason
    assert finish_reason == "stop", f"Model did not finish cleanly: {finish_reason}"

    import json

    result = json.loads(response.choices[0].message.content)

    # Verify structure
    assert "patient" in result, "Missing required field: patient"
    assert "diagnosis" in result, "Missing required field: diagnosis"
    assert "location" in result, "Missing required field: location"

    print(f"Minimal data test result: {result}")
    # Note: The LLM may hallucinate or return null/empty for missing fields
    # This test documents the actual behavior
