# backend/tests/test_mistral_ocr_service.py
"""Unit tests for ``services/mistral_ocr_service.py``.

The real Mistral SDK is never hit: ``mistral_ocr_service.Mistral`` (the class
bound in the module) is patched with a ``MagicMock`` whose context-manager
``__enter__`` yields a stub client. The service opens a fresh
``with Mistral(...) as mistral:`` block for each of its three API calls
(``files.upload`` -> ``files.get_signed_url`` -> ``ocr.process``); because
calling a ``MagicMock`` returns the same ``return_value`` every time, all three
blocks share a single stub client which we shape via SimpleNamespace return
values.

``time.sleep`` is patched module-wide (autouse) so retry backoff is instant.

``python-magic`` is NOT installed in this environment, so ``process`` naturally
takes the byte-signature fallback branch for MIME sniffing. The magic-available
branch is exercised by injecting a fake ``magic`` module into ``sys.modules``.

Coverage targets: ``__init__`` guard, ``_is_retryable_exception`` (status-code
and message-pattern paths), ``_execute_with_retry`` (success-after-retry,
non-retryable fail-fast, exhaustion), ``process`` happy path + call sequence +
single-``markdown`` fallback, and both MIME-sniff branches.
"""

import sys
import types
from unittest import mock

import pytest

from backend.src.services import mistral_ocr_service as mod
from backend.src.services.mistral_ocr_service import (
    MistralOCRError,
    MistralOCRResult,
    MistralOCRService,
)


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _instant_sleep():
    """Make retry backoff instant for every test."""
    with mock.patch.object(mod.time, "sleep") as sleep:
        yield sleep


def _make_service(**kwargs):
    params = dict(api_key="test-key", max_retries=2, retry_delay=0.01)
    params.update(kwargs)
    return MistralOCRService(**params)


def _status_exc(code):
    """Build an SDK-shaped exception carrying a ``.status_code`` attribute."""
    exc = Exception(f"HTTP {code}")
    exc.status_code = code
    return exc


def _configure_client(
    mistral_cls,
    *,
    upload_id="file-abc",
    signed_url="https://signed/doc",
    pages=None,
    markdown=None,
):
    """Shape the shared stub client reachable through the patched Mistral class.

    Returns the stub client mock (``ctx``) so tests can assert call args.
    """
    ctx = mistral_cls.return_value.__enter__.return_value
    ctx.files.upload.return_value = types.SimpleNamespace(id=upload_id)
    ctx.files.get_signed_url.return_value = types.SimpleNamespace(url=signed_url)
    if pages is None and markdown is not None:
        ocr_pages = []
    elif pages is None:
        ocr_pages = [
            types.SimpleNamespace(markdown="Page 1"),
            types.SimpleNamespace(markdown="Page 2"),
        ]
    else:
        ocr_pages = pages
    ctx.ocr.process.return_value = types.SimpleNamespace(
        pages=ocr_pages, markdown=markdown
    )
    return ctx


# --------------------------------------------------------------------------- #
# __init__
# --------------------------------------------------------------------------- #
class TestInit:
    def test_missing_api_key_raises(self):
        with pytest.raises(MistralOCRError):
            MistralOCRService(api_key="")

    def test_defaults_and_overrides(self):
        svc = MistralOCRService(
            api_key="k",
            base_url="https://custom.example",
            model="my-ocr",
            max_retries=5,
            retry_delay=2.0,
            retry_backoff=3.0,
        )
        assert svc.api_key == "k"
        assert svc.server_url == "https://custom.example"
        assert svc.model == "my-ocr"
        assert svc.max_retries == 5
        assert svc.base_retry_delay == 2.0
        assert svc.retry_backoff == 3.0


# --------------------------------------------------------------------------- #
# _is_retryable_exception
# --------------------------------------------------------------------------- #
class TestIsRetryable:
    @pytest.mark.parametrize("code", sorted(MistralOCRService.RETRYABLE_STATUS_CODES))
    def test_retryable_status_codes(self, code):
        svc = _make_service()
        assert svc._is_retryable_exception(_status_exc(code)) is True

    @pytest.mark.parametrize("code", [400, 401, 403, 404, 422])
    def test_non_retryable_status_codes(self, code):
        svc = _make_service()
        # A bare status-code exception with a message that has no retryable
        # keyword must be classified as non-retryable.
        exc = Exception("bad request")
        exc.status_code = code
        assert svc._is_retryable_exception(exc) is False

    def test_plain_value_error_not_retryable(self):
        svc = _make_service()
        assert svc._is_retryable_exception(ValueError("schema mismatch")) is False

    @pytest.mark.parametrize(
        "message",
        [
            "Connection timeout while reading",
            "connection error: reset by peer",
            "temporary failure in name resolution",
            "rate limit exceeded",
            "503 service unavailable",
            "502 bad gateway",
        ],
    )
    def test_retryable_message_patterns(self, message):
        svc = _make_service()
        assert svc._is_retryable_exception(Exception(message)) is True

    def test_non_int_status_code_falls_back_to_message(self):
        svc = _make_service()
        exc = Exception("some opaque failure")
        exc.status_code = "not-an-int"
        assert svc._is_retryable_exception(exc) is False


# --------------------------------------------------------------------------- #
# _execute_with_retry
# --------------------------------------------------------------------------- #
class TestExecuteWithRetry:
    def test_success_first_try(self):
        svc = _make_service()
        func = mock.Mock(return_value="ok")
        assert svc._execute_with_retry(func, "op") == "ok"
        assert func.call_count == 1

    def test_retryable_then_succeeds(self):
        svc = _make_service(max_retries=3)
        calls = {"n": 0}

        def func():
            calls["n"] += 1
            if calls["n"] <= 2:
                raise _status_exc(503)
            return "recovered"

        assert svc._execute_with_retry(func, "op") == "recovered"
        assert calls["n"] == 3  # failed twice, succeeded on the third

    def test_non_retryable_fails_immediately(self):
        svc = _make_service(max_retries=3)
        func = mock.Mock(side_effect=_status_exc(400))
        with pytest.raises(MistralOCRError):
            svc._execute_with_retry(func, "op")
        # No retries for a non-retryable error.
        assert func.call_count == 1

    def test_exhaustion_raises_after_max_retries(self):
        svc = _make_service(max_retries=2)
        func = mock.Mock(side_effect=_status_exc(500))
        with pytest.raises(MistralOCRError) as ei:
            svc._execute_with_retry(func, "op")
        # max_retries + 1 total attempts.
        assert func.call_count == 3
        assert "after 2 retries" in str(ei.value)

    def test_backoff_sleeps_between_attempts(self, _instant_sleep):
        svc = _make_service(max_retries=2)
        func = mock.Mock(side_effect=_status_exc(500))
        with pytest.raises(MistralOCRError):
            svc._execute_with_retry(func, "op")
        # Slept once after attempt 0 and once after attempt 1 (not after the
        # final exhausted attempt).
        assert _instant_sleep.call_count == 2


# --------------------------------------------------------------------------- #
# process — happy path + call sequence
# --------------------------------------------------------------------------- #
class TestProcessHappyPath:
    def test_returns_concatenated_pages_and_call_sequence(self):
        svc = _make_service()
        with mock.patch.object(mod, "Mistral") as mistral_cls:
            ctx = _configure_client(mistral_cls)
            result = svc.process(b"%PDF-1.7 body")

        assert isinstance(result, MistralOCRResult)
        assert result.text == "Page 1\n\nPage 2"
        assert result.pages == ["Page 1", "Page 2"]

        # upload -> get_signed_url(file_id=...) -> ocr.process(document_url=...)
        ctx.files.upload.assert_called_once()
        ctx.files.get_signed_url.assert_called_once_with(file_id="file-abc")
        _, ocr_kwargs = ctx.ocr.process.call_args
        assert ocr_kwargs["model"] == svc.model
        assert ocr_kwargs["document"] == {
            "type": "document_url",
            "document_url": "https://signed/doc",
        }

    def test_empty_pages_uses_single_markdown_field(self):
        svc = _make_service()
        with mock.patch.object(mod, "Mistral") as mistral_cls:
            _configure_client(mistral_cls, pages=[], markdown="whole doc markdown")
            result = svc.process(b"%PDF-1.7 body")
        assert result.text == "whole doc markdown"
        assert result.pages == []

    def test_page_with_none_markdown_is_filtered(self):
        svc = _make_service()
        pages = [
            types.SimpleNamespace(markdown="Real"),
            types.SimpleNamespace(markdown=None),
        ]
        with mock.patch.object(mod, "Mistral") as mistral_cls:
            _configure_client(mistral_cls, pages=pages)
            result = svc.process(b"%PDF-1.7 body")
        # None markdown becomes "" then is filtered out of pages, but its blank
        # slot still contributes to the concatenation before strip().
        assert result.pages == ["Real"]
        assert result.text == "Real"

    def test_upload_failure_wrapped(self):
        svc = _make_service(max_retries=0)
        with mock.patch.object(mod, "Mistral") as mistral_cls:
            ctx = mistral_cls.return_value.__enter__.return_value
            ctx.files.upload.side_effect = _status_exc(500)
            with pytest.raises(MistralOCRError) as ei:
                svc.process(b"%PDF-1.7 body")
        assert "Failed to upload document" in str(ei.value)


# --------------------------------------------------------------------------- #
# MIME sniffing — byte-signature fallback (magic unavailable)
# --------------------------------------------------------------------------- #
class TestMimeFallback:
    """``magic`` is not installed here, so ``process`` uses the byte-signature
    fallback. We read back the detected type via the ``file_name`` extension
    passed to ``files.upload`` (``document.<type>``).
    """

    def _detected_type(self, content):
        svc = _make_service()
        with mock.patch.object(mod, "Mistral") as mistral_cls:
            ctx = _configure_client(mistral_cls)
            svc.process(content)
        _, upload_kwargs = ctx.files.upload.call_args
        return upload_kwargs["file"]["file_name"]

    def test_magic_is_actually_absent(self):
        # Guards the assumption behind this class: if python-magic ever gets
        # installed, these fallback assertions would silently exercise the
        # magic-available branch instead of the byte-signature fallback.
        import importlib.util

        assert importlib.util.find_spec("magic") is None

    def test_pdf_signature(self):
        assert self._detected_type(b"%PDF-1.5 ...") == "document.pdf"

    def test_png_signature(self):
        assert self._detected_type(b"\x89PNG\r\n\x1a\n rest") == "document.image"

    def test_jpeg_signature(self):
        assert self._detected_type(b"\xff\xd8\xff\xe0 rest") == "document.image"

    def test_bmp_signature(self):
        assert self._detected_type(b"BM rest of bitmap") == "document.image"

    def test_unknown_defaults_to_pdf(self):
        assert self._detected_type(b"just some plain text bytes") == "document.pdf"


# --------------------------------------------------------------------------- #
# MIME sniffing — magic-available branch (fake module injected)
# --------------------------------------------------------------------------- #
class TestMimeWithMagic:
    @pytest.fixture
    def fake_magic(self):
        fake = types.ModuleType("magic")
        fake._mime = "application/pdf"

        def from_buffer(buf, mime=True):
            return fake._mime

        fake.from_buffer = from_buffer
        sys.modules["magic"] = fake
        try:
            yield fake
        finally:
            del sys.modules["magic"]

    def _detected_type(self, content):
        svc = _make_service()
        with mock.patch.object(mod, "Mistral") as mistral_cls:
            ctx = _configure_client(mistral_cls)
            svc.process(content)
        _, upload_kwargs = ctx.files.upload.call_args
        return upload_kwargs["file"]["file_name"]

    def test_magic_pdf(self, fake_magic):
        fake_magic._mime = "application/pdf"
        assert self._detected_type(b"anything") == "document.pdf"

    def test_magic_image(self, fake_magic):
        fake_magic._mime = "image/png"
        assert self._detected_type(b"anything") == "document.image"

    def test_magic_unsupported_raises(self, fake_magic):
        fake_magic._mime = "text/plain"
        svc = _make_service()
        with mock.patch.object(mod, "Mistral"):
            with pytest.raises(MistralOCRError) as ei:
                svc.process(b"anything")
        assert "Unsupported file type" in str(ei.value)
