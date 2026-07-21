# backend/tests/test_docling_serve_client.py
"""Unit tests for backend/src/services/docling_serve_client.py.

Two layers, no real network:

1. Pure dict parsers ``_extract_markdown`` / ``_extract_warnings`` — exercised
   with hand-built response-dict fixtures covering every response shape / branch
   (top-level fields, nested ``document``, ``document.output``, list keys with
   direct + nested output, missing keys, malformed warnings). Zero mocking.

2. The public ``convert_*`` methods and ``_convert`` HTTP path — the constructed
   client's internal ``httpx.Client`` (``client._client``) is replaced with a
   ``MagicMock`` whose ``.post(...)`` returns a fake response, so we can assert
   the multipart ``data``/``files`` assembly, the success/error/retry branches,
   and the rich ``DoclingServeError`` attributes without any I/O. ``time.sleep``
   is patched so retry backoff is instant.
"""

from unittest.mock import MagicMock

import httpx
import pytest

from backend.src.services.docling_serve_client import (
    DoclingServeClient,
    DoclingServeError,
    DoclingServeResult,
    _extract_markdown,
    _extract_warnings,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
class FakeResponse:
    """Minimal stand-in for httpx.Response used by ``_convert``."""

    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text
        self.headers = {}

    def json(self):
        return self._json

    def raise_for_status(self):
        pass


def make_client(**kwargs) -> DoclingServeClient:
    """Build a client and swap its httpx client for a MagicMock."""
    client = DoclingServeClient("http://docling.local", **kwargs)
    client._client = MagicMock()
    return client


# --------------------------------------------------------------------------- #
# _extract_markdown
# --------------------------------------------------------------------------- #
class TestExtractMarkdown:
    def test_top_level_md_content(self):
        assert _extract_markdown({"md_content": "  # Hello  "}) == "# Hello"

    @pytest.mark.parametrize("key", ["markdown", "text", "content"])
    def test_top_level_alternate_keys(self, key):
        assert _extract_markdown({key: "body"}) == "body"

    def test_nested_document_md_content(self):
        resp = {"document": {"md_content": "nested md"}, "status": "success"}
        assert _extract_markdown(resp) == "nested md"

    @pytest.mark.parametrize("key", ["md_content", "markdown", "text", "content"])
    def test_nested_document_alternate_keys(self, key):
        assert _extract_markdown({"document": {key: "docval"}}) == "docval"

    @pytest.mark.parametrize("out_key", ["output", "outputs"])
    @pytest.mark.parametrize("md_key", ["md", "markdown", "text"])
    def test_document_output_dict(self, out_key, md_key):
        resp = {"document": {out_key: {md_key: "from output"}}}
        assert _extract_markdown(resp) == "from output"

    @pytest.mark.parametrize(
        "list_key", ["documents", "results", "converted_documents", "output"]
    )
    def test_list_key_direct_field(self, list_key):
        resp = {list_key: [{"md_content": "list md"}]}
        assert _extract_markdown(resp) == "list md"

    def test_list_key_nested_output(self):
        resp = {"results": [{"output": {"md": "deep md"}}]}
        assert _extract_markdown(resp) == "deep md"

    def test_list_key_outputs_alias(self):
        resp = {"documents": [{"outputs": {"markdown": "outs"}}]}
        assert _extract_markdown(resp) == "outs"

    def test_multiple_candidates_joined_with_blank_line(self):
        # top-level md_content + nested document md_content both collected.
        resp = {"md_content": "first", "document": {"md_content": "second"}}
        assert _extract_markdown(resp) == "first\n\nsecond"

    def test_non_string_values_ignored(self):
        # numeric / dict / list values must not become candidates.
        resp = {"md_content": 123, "document": {"md_content": "real"}}
        assert _extract_markdown(resp) == "real"

    def test_empty_strings_filtered_then_raises(self):
        with pytest.raises(DoclingServeError) as exc:
            _extract_markdown({"md_content": "   ", "markdown": ""})
        assert "Could not extract Markdown" in str(exc.value)

    def test_missing_keys_raises_with_available_keys(self):
        with pytest.raises(DoclingServeError) as exc:
            _extract_markdown({"status": "success", "processing_time": 1.0})
        msg = str(exc.value)
        assert "Available keys" in msg
        assert "status" in msg

    def test_document_not_dict_ignored(self):
        # document present but a string -> falls through to error.
        with pytest.raises(DoclingServeError):
            _extract_markdown({"document": "not-a-dict"})

    def test_list_items_non_dict_ignored(self):
        resp = {"results": ["str-item", 5, {"md_content": "ok"}]}
        assert _extract_markdown(resp) == "ok"


# --------------------------------------------------------------------------- #
# _extract_warnings
# --------------------------------------------------------------------------- #
class TestExtractWarnings:
    def test_absent_warnings(self):
        assert _extract_warnings({"md_content": "x"}) == []

    def test_top_level_string_warnings(self):
        assert _extract_warnings({"warnings": ["w1", "w2"]}) == ["w1", "w2"]

    def test_top_level_dict_warning_with_message(self):
        assert _extract_warnings({"warnings": [{"message": "boom"}]}) == ["boom"]

    def test_dict_warning_without_message_ignored(self):
        assert _extract_warnings({"warnings": [{"code": 1}]}) == []

    def test_warnings_not_a_list_ignored(self):
        assert _extract_warnings({"warnings": "oops"}) == []

    def test_mixed_string_and_dict(self):
        resp = {"warnings": ["a", {"message": "b"}, {"nope": 1}, 42]}
        assert _extract_warnings(resp) == ["a", "b"]

    @pytest.mark.parametrize(
        "list_key", ["documents", "results", "converted_documents"]
    )
    def test_per_document_warnings(self, list_key):
        resp = {list_key: [{"warnings": ["dw", {"message": "dm"}]}]}
        assert _extract_warnings(resp) == ["dw", "dm"]

    def test_per_document_non_dict_items_skipped(self):
        resp = {"documents": ["x", {"warnings": ["ok"]}]}
        assert _extract_warnings(resp) == ["ok"]

    def test_top_level_and_per_document_combined(self):
        resp = {
            "warnings": ["top"],
            "results": [{"warnings": ["perdoc"]}],
        }
        assert _extract_warnings(resp) == ["top", "perdoc"]

    def test_output_list_key_not_scanned_for_warnings(self):
        # "output" is a markdown list-key but NOT a warnings list-key.
        assert _extract_warnings({"output": [{"warnings": ["ignored"]}]}) == []


# --------------------------------------------------------------------------- #
# Constructor / lifecycle
# --------------------------------------------------------------------------- #
class TestConstructor:
    def test_empty_base_url_raises(self):
        with pytest.raises(DoclingServeError):
            DoclingServeClient("")

    def test_base_url_trailing_slash_stripped(self):
        c = DoclingServeClient("http://x.local/")
        assert c.base_url == "http://x.local"
        c.close()

    def test_default_ocr_langs_defaults_to_auto(self):
        c = DoclingServeClient("http://x.local")
        assert c.default_ocr_langs == "auto"
        c.close()

    def test_explicit_default_ocr_langs_preserved(self):
        c = DoclingServeClient("http://x.local", default_ocr_langs=["deu"])
        assert c.default_ocr_langs == ["deu"]
        c.close()

    def test_context_manager_closes_client(self):
        c = DoclingServeClient("http://x.local")
        c._client = MagicMock()
        with c as ctx:
            assert ctx is c
        c._client.close.assert_called_once()

    def test_close_delegates(self):
        c = make_client()
        c.close()
        c._client.close.assert_called_once()


# --------------------------------------------------------------------------- #
# Multipart assembly (per method)
# --------------------------------------------------------------------------- #
class TestMultipartAssembly:
    def _post_kwargs(self, client):
        args, kwargs = client._client.post.call_args
        return args, kwargs

    def test_convert_pdf_no_ocr_form(self):
        client = make_client()
        client._client.post.return_value = FakeResponse(json_data={"md_content": "ok"})
        result = client.convert_pdf_no_ocr(b"PDFDATA", "doc.pdf")

        assert isinstance(result, DoclingServeResult)
        assert result.text == "ok"

        args, kwargs = self._post_kwargs(client)
        assert args[0] == "http://docling.local/v1/convert/file"
        data = kwargs["data"]
        files = kwargs["files"]

        assert data["do_ocr"] == "false"
        assert data["force_ocr"] == "false"
        assert data["from_formats"] == "pdf"
        assert data["to_formats"] == "md"
        assert data["table_mode"] == "fast"
        assert data["abort_on_error"] == "false"
        # image_export_mode only present when OCR disabled
        assert data["image_export_mode"] == "placeholder"
        # No OCR fields when do_ocr is false
        assert "ocr_preset" not in data
        assert "ocr_lang" not in data
        # File tuple: (filename, content, mime)
        assert files["files"] == ("doc.pdf", b"PDFDATA", "application/pdf")

    def test_convert_pdf_tesseract_default_auto_omits_lang(self):
        client = make_client()
        client._client.post.return_value = FakeResponse(json_data={"md_content": "ok"})
        client.convert_pdf_tesseract(b"X", "d.pdf")

        _, kwargs = self._post_kwargs(client)
        data = kwargs["data"]
        assert data["do_ocr"] == "true"
        assert data["force_ocr"] == "false"
        assert data["ocr_preset"] == "tesseract"
        # default_ocr_langs == "auto" -> omitted
        assert "ocr_lang" not in data
        # image_export_mode omitted when OCR enabled
        assert "image_export_mode" not in data

    def test_convert_pdf_tesseract_force_ocr_flag(self):
        client = make_client()
        client._client.post.return_value = FakeResponse(json_data={"md_content": "ok"})
        client.convert_pdf_tesseract(b"X", "d.pdf", force_ocr=True)
        _, kwargs = self._post_kwargs(client)
        assert kwargs["data"]["force_ocr"] == "true"

    def test_convert_pdf_tesseract_list_langs_joined(self):
        client = make_client()
        client._client.post.return_value = FakeResponse(json_data={"md_content": "ok"})
        client.convert_pdf_tesseract(b"X", "d.pdf", ocr_langs=["deu", "eng"])
        _, kwargs = self._post_kwargs(client)
        assert kwargs["data"]["ocr_lang"] == "deu,eng"

    def test_convert_pdf_tesseract_string_lang_set(self):
        client = make_client()
        client._client.post.return_value = FakeResponse(json_data={"md_content": "ok"})
        client.convert_pdf_tesseract(b"X", "d.pdf", ocr_langs="fra")
        _, kwargs = self._post_kwargs(client)
        assert kwargs["data"]["ocr_lang"] == "fra"

    def test_convert_pdf_tesseract_auto_string_case_insensitive_omitted(self):
        client = make_client()
        client._client.post.return_value = FakeResponse(json_data={"md_content": "ok"})
        client.convert_pdf_tesseract(b"X", "d.pdf", ocr_langs="AUTO")
        _, kwargs = self._post_kwargs(client)
        assert "ocr_lang" not in kwargs["data"]

    def test_convert_image_tesseract_form(self):
        client = make_client(default_ocr_langs=["eng"])
        client._client.post.return_value = FakeResponse(
            json_data={"md_content": "img text"}
        )
        result = client.convert_image_tesseract(b"IMG", "p.png", "image/png")

        assert result.text == "img text"
        args, kwargs = self._post_kwargs(client)
        data = kwargs["data"]
        assert data["from_formats"] == "image"
        assert data["do_ocr"] == "true"
        assert data["force_ocr"] == "true"
        assert data["ocr_preset"] == "tesseract"
        assert data["ocr_lang"] == "eng"
        assert kwargs["files"]["files"] == ("p.png", b"IMG", "image/png")


# --------------------------------------------------------------------------- #
# Response / warnings on the success path
# --------------------------------------------------------------------------- #
class TestSuccessPath:
    def test_result_carries_raw_and_warnings(self):
        client = make_client()
        payload = {"md_content": "hello", "warnings": ["slow"]}
        client._client.post.return_value = FakeResponse(json_data=payload)

        result = client.convert_pdf_no_ocr(b"x", "f.pdf")
        assert result.text == "hello"
        assert result.raw_response == payload
        assert result.warnings == ["slow"]


# --------------------------------------------------------------------------- #
# Error / retry branches
# --------------------------------------------------------------------------- #
class TestErrorBranches:
    def test_non_200_raises_rich_error(self):
        client = make_client(max_retries=0)
        client._client.post.return_value = FakeResponse(
            status_code=503, text="upstream down"
        )
        with pytest.raises(DoclingServeError) as exc:
            client.convert_pdf_no_ocr(b"x", "err.pdf")

        e = exc.value
        assert e.status_code == 503
        assert e.endpoint == "http://docling.local/v1/convert/file"
        assert e.filename == "err.pdf"
        assert e.ocr_mode == "do_ocr=False, force_ocr=False"
        assert "upstream down" in e.response_body
        # single attempt when max_retries=0
        assert client._client.post.call_count == 1

    def test_timeout_retries_then_raises(self, monkeypatch):
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)
        client = make_client(max_retries=1)
        client._client.post.side_effect = httpx.TimeoutException("t/o")

        with pytest.raises(DoclingServeError) as exc:
            client.convert_pdf_tesseract(b"x", "slow.pdf")

        assert "timed out" in str(exc.value)
        # max_retries=1 -> 2 attempts total
        assert client._client.post.call_count == 2

    def test_timeout_then_success(self, monkeypatch):
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)
        client = make_client(max_retries=1)
        client._client.post.side_effect = [
            httpx.TimeoutException("t/o"),
            FakeResponse(json_data={"md_content": "recovered"}),
        ]
        result = client.convert_pdf_no_ocr(b"x", "f.pdf")
        assert result.text == "recovered"
        assert client._client.post.call_count == 2

    def test_request_error_no_fallback_raises(self, monkeypatch):
        # Ensure the local-docling fallback branch stays off so no heavy import.
        # `settings` is a proxy with no __dict__; patch the real settings object.
        from backend.src.core import config

        monkeypatch.setattr(
            config._get_settings(), "DOCLING_LOCAL_FALLBACK", False, raising=False
        )

        client = make_client(max_retries=0)
        client._client.post.side_effect = httpx.ConnectError("refused")

        with pytest.raises(DoclingServeError) as exc:
            client.convert_pdf_no_ocr(b"x", "f.pdf")

        e = exc.value
        assert "request failed" in str(e)
        assert e.filename == "f.pdf"
        assert e.endpoint == "http://docling.local/v1/convert/file"

    def test_error_response_missing_markdown_raises(self):
        client = make_client(max_retries=0)
        client._client.post.return_value = FakeResponse(
            json_data={"status": "success"}  # no markdown fields
        )
        with pytest.raises(DoclingServeError) as exc:
            client.convert_pdf_no_ocr(b"x", "f.pdf")
        assert "Could not extract Markdown" in str(exc.value)


# --------------------------------------------------------------------------- #
# DoclingServeError message formatting
# --------------------------------------------------------------------------- #
class TestDoclingServeError:
    def test_message_assembles_all_parts(self):
        e = DoclingServeError(
            "base",
            status_code=500,
            response_body="body",
            endpoint="/ep",
            filename="f.pdf",
            ocr_mode="do_ocr=True",
        )
        s = str(e)
        assert "base" in s
        assert "HTTP 500" in s
        assert "Endpoint: /ep" in s
        assert "File: f.pdf" in s
        assert "OCR mode: do_ocr=True" in s
        assert "Response: body" in s

    def test_long_response_body_truncated(self):
        e = DoclingServeError("m", response_body="A" * 500)
        # excerpt is first 200 chars
        assert "A" * 200 in str(e)
        assert "A" * 201 not in str(e)

    def test_minimal_message(self):
        assert str(DoclingServeError("just a message")) == "just a message"
