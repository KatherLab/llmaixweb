"""Unit tests for ``LLMVisionOCRService``.

The service eagerly builds an ``OpenAI`` client in ``__init__`` and renders
PDF pages with PyMuPDF. Both are network / heavy-native seams, so we:

* construct the real service (the ``OpenAI(...)`` build is offline — no request
  is made at construction time) and then overwrite ``service.client`` with a
  ``MagicMock`` whose ``.chat.completions.create(...)`` returns a fake
  completion shaped like ``response.choices[0].message.content``;
* patch ``service._pdf_to_images`` (or use ``is_pdf=False``) so PyMuPDF/fitz is
  never exercised;
* patch the module-level ``time.sleep`` so retry backoff is instant.

The ``_apply_exif_rotation`` tests use real in-memory PIL images and are skipped
if Pillow is unavailable.
"""

import io
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.src.services import llm_vision_ocr_service as mod
from backend.src.services.llm_vision_ocr_service import (
    LLMVisionOCRError,
    LLMVisionOCRResult,
    LLMVisionOCRService,
)

try:
    from PIL import Image

    _PIL_AVAILABLE = True
except ImportError:  # pragma: no cover - PIL is a hard dependency in this repo
    _PIL_AVAILABLE = False


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _make_completion(content):
    """Build an object shaped like an OpenAI chat completion response."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _make_service(**kwargs):
    """Construct a service with a mocked client (no real network client used)."""
    params = {
        "api_key": "test-key",
        "base_url": "http://localhost:11434/v1",
        "model": "gpt-4o",
        "max_concurrency": 1,
        "max_retries": 3,
    }
    params.update(kwargs)
    service = LLMVisionOCRService(**params)
    # Overwrite the eagerly-built OpenAI client with a mock.
    service.client = MagicMock()
    return service


def _status_exc(status_code, message="boom"):
    """An exception carrying a structured ``status_code`` like the OpenAI SDK."""
    exc = RuntimeError(message)
    exc.status_code = status_code
    return exc


def _tiny_png_bytes(size=(8, 8), color=(200, 30, 30)):
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Construction / validation
# --------------------------------------------------------------------------- #
def test_init_requires_api_key():
    with pytest.raises(LLMVisionOCRError):
        LLMVisionOCRService(api_key="", base_url="http://localhost/v1")


def test_init_requires_base_url():
    with pytest.raises(LLMVisionOCRError):
        LLMVisionOCRService(api_key="k", base_url="")


def test_close_is_idempotent_and_nulls_client():
    service = _make_service()
    client = service.client
    service.close()
    assert service.client is None
    client.close.assert_called_once()
    # Second close is safe (no client to close).
    service.close()
    assert service.client is None


def test_context_manager_closes():
    with _make_service() as service:
        assert service.client is not None
        inner = service.client
    assert service.client is None
    inner.close.assert_called_once()


# --------------------------------------------------------------------------- #
# _is_retryable_exception
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("code", [429, 500, 502, 503, 504])
def test_is_retryable_status_codes(code):
    service = _make_service()
    assert service._is_retryable_exception(_status_exc(code)) is True


@pytest.mark.parametrize("code", [400, 401, 403, 404, 422])
def test_non_retryable_status_codes(code):
    service = _make_service()
    # message deliberately free of retryable substrings
    assert service._is_retryable_exception(_status_exc(code, "invalid input")) is False


@pytest.mark.parametrize(
    "message",
    [
        "Request timeout",
        "Connection error while calling API",
        "temporary failure in name resolution",
        "rate limit exceeded",
        "503 service unavailable",
        "bad gateway",
        "internal server error",
    ],
)
def test_retryable_message_patterns(message):
    service = _make_service()
    assert service._is_retryable_exception(RuntimeError(message)) is True


def test_non_retryable_plain_exception():
    service = _make_service()
    assert service._is_retryable_exception(ValueError("totally broken")) is False


# --------------------------------------------------------------------------- #
# _execute_with_retry
# --------------------------------------------------------------------------- #
def test_execute_with_retry_succeeds_first_try():
    service = _make_service()
    assert service._execute_with_retry(lambda: "ok", "op") == "ok"


def test_execute_with_retry_recovers_after_retryable(monkeypatch):
    monkeypatch.setattr(mod.time, "sleep", lambda _s: None)
    service = _make_service(max_retries=3)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise _status_exc(503, "service unavailable")
        return "recovered"

    assert service._execute_with_retry(flaky, "op", page_idx=0) == "recovered"
    assert calls["n"] == 3


def test_execute_with_retry_exhausts_and_raises(monkeypatch):
    sleeps = []
    monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
    service = _make_service(max_retries=2)

    def always_retryable():
        raise _status_exc(500, "server error")

    with pytest.raises(LLMVisionOCRError) as exc_info:
        service._execute_with_retry(always_retryable, "op")
    assert "after 2 retries" in str(exc_info.value)
    # Slept once per retry (not after the final failed attempt).
    assert len(sleeps) == 2


def test_execute_with_retry_non_retryable_fails_immediately(monkeypatch):
    slept = []
    monkeypatch.setattr(mod.time, "sleep", lambda s: slept.append(s))
    service = _make_service(max_retries=5)
    calls = {"n": 0}

    def non_retryable():
        calls["n"] += 1
        raise ValueError("permanent failure")

    with pytest.raises(LLMVisionOCRError):
        service._execute_with_retry(non_retryable, "op", page_idx=1)
    assert calls["n"] == 1  # no retries
    assert slept == []  # never slept


# --------------------------------------------------------------------------- #
# process()
# --------------------------------------------------------------------------- #
def test_process_multipage_happy_path(monkeypatch):
    service = _make_service(max_concurrency=1)
    monkeypatch.setattr(
        service, "_pdf_to_images", lambda content: [b"img0", b"img1", b"img2"]
    )
    service.client.chat.completions.create.side_effect = [
        _make_completion("Page A"),
        _make_completion("Page B"),
        _make_completion("Page C"),
    ]

    result = service.process(b"%PDF-fake", is_pdf=True)

    assert isinstance(result, LLMVisionOCRResult)
    assert result.total_pages == 3
    assert result.failed_pages == 0
    assert result.errors == []
    assert result.pages == ["Page A", "Page B", "Page C"]
    assert result.text == "Page A\n\nPage B\n\nPage C"


def test_process_single_image_not_pdf(monkeypatch):
    """is_pdf=False must skip _pdf_to_images entirely and process one image."""
    service = _make_service(max_concurrency=1)

    def _boom(_content):
        raise AssertionError("_pdf_to_images must not be called for is_pdf=False")

    monkeypatch.setattr(service, "_pdf_to_images", _boom)
    service.client.chat.completions.create.return_value = _make_completion("# Title")

    png = _tiny_png_bytes() if _PIL_AVAILABLE else b"not-an-image"
    result = service.process(png, is_pdf=False)

    assert result.total_pages == 1
    assert result.failed_pages == 0
    assert result.text == "# Title"


def test_process_partial_failure_returns_result(monkeypatch):
    """One non-retryable page failure is recorded; the trial still returns."""
    monkeypatch.setattr(mod.time, "sleep", lambda _s: None)
    service = _make_service(max_concurrency=1)
    monkeypatch.setattr(service, "_pdf_to_images", lambda content: [b"a", b"b", b"c"])
    service.client.chat.completions.create.side_effect = [
        _make_completion("first"),
        ValueError("permanent decode failure"),  # non-retryable
        _make_completion("third"),
    ]

    result = service.process(b"pdf", is_pdf=True)

    assert result.total_pages == 3
    assert result.failed_pages == 1
    assert len(result.errors) == 1
    # Only the successful pages survive, in page order.
    assert result.pages == ["first", "third"]
    assert result.text == "first\n\nthird"


def test_process_all_pages_fail_raises(monkeypatch):
    monkeypatch.setattr(mod.time, "sleep", lambda _s: None)
    service = _make_service(max_concurrency=1)
    monkeypatch.setattr(service, "_pdf_to_images", lambda content: [b"a", b"b"])
    service.client.chat.completions.create.side_effect = ValueError("hard fail")

    with pytest.raises(LLMVisionOCRError) as exc_info:
        service.process(b"pdf", is_pdf=True)
    assert "All 2 page(s) failed" in str(exc_info.value)


def test_process_no_images_raises(monkeypatch):
    service = _make_service()
    monkeypatch.setattr(service, "_pdf_to_images", lambda content: [])
    with pytest.raises(LLMVisionOCRError) as exc_info:
        service.process(b"pdf", is_pdf=True)
    assert "No images generated" in str(exc_info.value)


def test_process_empty_content_returned_from_model(monkeypatch):
    """A None message content is coerced to '' by _process_single_image."""
    service = _make_service(max_concurrency=1)
    monkeypatch.setattr(service, "_pdf_to_images", lambda content: [b"a"])
    service.client.chat.completions.create.return_value = _make_completion(None)

    result = service.process(b"pdf", is_pdf=True)
    # The page produced empty text: no failure, but no surviving page text.
    assert result.failed_pages == 0
    assert result.total_pages == 1
    assert result.pages == []
    assert result.text == ""


# --------------------------------------------------------------------------- #
# _apply_exif_rotation  (real PIL images)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not _PIL_AVAILABLE, reason="Pillow not installed")
def test_apply_exif_rotation_passthrough_returns_png():
    service = _make_service()
    out = service._apply_exif_rotation(_tiny_png_bytes(size=(10, 10)))
    assert isinstance(out, bytes) and len(out) > 0
    img = Image.open(io.BytesIO(out))
    assert img.format == "PNG"
    assert img.size == (10, 10)


@pytest.mark.skipif(not _PIL_AVAILABLE, reason="Pillow not installed")
def test_apply_exif_rotation_resizes_when_over_max_dim(monkeypatch):
    # Force a tiny max dimension so a modest image is downscaled. `settings` is
    # a proxy with no __dict__; patch the real settings object it forwards to.
    from backend.src.core import config

    monkeypatch.setattr(config._get_settings(), "IMAGE_MAX_DIMENSION", 50)
    service = _make_service()
    out = service._apply_exif_rotation(_tiny_png_bytes(size=(200, 100)))
    img = Image.open(io.BytesIO(out))
    assert img.format == "PNG"
    assert max(img.size) <= 50
    # Aspect ratio (2:1) preserved.
    assert img.size == (50, 25)


@pytest.mark.skipif(not _PIL_AVAILABLE, reason="Pillow not installed")
def test_apply_exif_rotation_no_resize_within_max_dim(monkeypatch):
    from backend.src.core import config

    monkeypatch.setattr(config._get_settings(), "IMAGE_MAX_DIMENSION", 4096)
    service = _make_service()
    out = service._apply_exif_rotation(_tiny_png_bytes(size=(64, 32)))
    img = Image.open(io.BytesIO(out))
    assert img.size == (64, 32)


def test_apply_exif_rotation_invalid_bytes_returned_unchanged():
    """Non-image bytes hit the broad except and are returned as-is."""
    service = _make_service()
    garbage = b"this is not an image"
    assert service._apply_exif_rotation(garbage) == garbage
