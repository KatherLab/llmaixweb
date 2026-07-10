# backend/tests/test_config_secret_redaction.py
"""OCR credential redaction from PreprocessingConfiguration responses.

mistral_api_key / vision_api_key may be embedded in a configuration's
additional_settings (write-only from the UI). They must never be serialized back
to clients — not in API responses, not in the WebSocket broadcast. This guards
the response-schema field serializer + the shared redaction helper.
"""

from datetime import UTC, datetime

from backend.src.schemas.project import (
    PreprocessingConfiguration,
    redact_ocr_secrets,
)


def _config_with_secrets() -> PreprocessingConfiguration:
    return PreprocessingConfiguration(
        id=1,
        project_id=1,
        name="cfg",
        description=None,
        additional_settings={
            "ocr_engine": "llm_vision",
            "vision_base_url": "https://vision.example/v1",
            "vision_api_key": "VISION_SECRET",
            "mistral_api_key": "MISTRAL_SECRET",
        },
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_response_schema_redacts_secret_keys():
    dumped = _config_with_secrets().model_dump()["additional_settings"]
    assert "vision_api_key" not in dumped
    assert "mistral_api_key" not in dumped
    # Non-secret settings must survive untouched.
    assert dumped["ocr_engine"] == "llm_vision"
    assert dumped["vision_base_url"] == "https://vision.example/v1"


def test_response_schema_json_has_no_secret_values():
    j = _config_with_secrets().model_dump_json()
    assert "VISION_SECRET" not in j
    assert "MISTRAL_SECRET" not in j


def test_redact_helper_is_noop_without_secrets():
    settings = {"ocr_engine": "docling_tesseract", "force_ocr": True}
    assert redact_ocr_secrets(settings) == settings
    assert redact_ocr_secrets(None) is None
    assert redact_ocr_secrets({}) == {}
