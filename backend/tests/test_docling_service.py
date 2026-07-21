"""Unit tests for ``backend/src/services/docling_service.py``.

Covers the pure/static helpers (accelerator-device mapping, page-sampling math,
the markdown-stripping useful-text threshold), the ``DoclingMode`` enum, and the
two public methods:

- ``has_embedded_text`` against the real PDF fixtures (a text PDF and a
  scanned/no-text PDF) plus a couple of patched edge cases.
- ``process`` with a patched converter (the real Docling ``DocumentConverter`` is
  heavy and would attempt model loading / real conversion), asserting the
  returned Markdown, temp-file cleanup, and error wrapping.

The converter *option branching* in ``_get_converter`` is verified by patching
``DocumentConverter`` so no models are loaded and no conversion runs.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from docling.datamodel.accelerator_options import AcceleratorDevice

from backend.src.services import docling_service as ds
from backend.src.services.docling_service import (
    DoclingMode,
    DoclingService,
    DoclingServiceError,
)

FILES = Path(__file__).parent / "files"


# --------------------------------------------------------------------------- #
# DoclingMode enum
# --------------------------------------------------------------------------- #
class TestDoclingMode:
    def test_values(self):
        assert DoclingMode.NO_OCR.value == "no_ocr"
        assert DoclingMode.TESSERACT_OCR.value == "tesseract_ocr"
        assert DoclingMode.TESSERACT_FORCE_OCR.value == "tesseract_force_ocr"

    def test_is_str_enum(self):
        # StrEnum members compare equal to their string value.
        assert DoclingMode.NO_OCR == "no_ocr"
        assert list(DoclingMode) == [
            DoclingMode.NO_OCR,
            DoclingMode.TESSERACT_OCR,
            DoclingMode.TESSERACT_FORCE_OCR,
        ]


# --------------------------------------------------------------------------- #
# _get_accelerator_device
# --------------------------------------------------------------------------- #
class TestGetAcceleratorDevice:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("cpu", AcceleratorDevice.CPU),
            ("auto", AcceleratorDevice.AUTO),
            ("cuda", AcceleratorDevice.CUDA),
            ("mps", AcceleratorDevice.MPS),
        ],
    )
    def test_known_devices(self, value, expected):
        assert (
            DoclingService(accelerator_device=value)._get_accelerator_device()
            == expected
        )

    def test_case_insensitive(self):
        assert (
            DoclingService(accelerator_device="CUDA")._get_accelerator_device()
            == AcceleratorDevice.CUDA
        )
        assert (
            DoclingService(accelerator_device="Mps")._get_accelerator_device()
            == AcceleratorDevice.MPS
        )

    def test_unknown_falls_back_to_cpu(self):
        assert (
            DoclingService(accelerator_device="weird")._get_accelerator_device()
            == AcceleratorDevice.CPU
        )

    def test_empty_string_falls_back_to_cpu(self):
        # Empty string -> ``(... or "cpu")`` -> CPU.
        assert (
            DoclingService(accelerator_device="")._get_accelerator_device()
            == AcceleratorDevice.CPU
        )

    def test_default_device_is_cpu(self):
        assert DoclingService()._get_accelerator_device() == AcceleratorDevice.CPU


# --------------------------------------------------------------------------- #
# __init__ defaults
# --------------------------------------------------------------------------- #
class TestInit:
    def test_default_languages(self):
        assert DoclingService().ocr_languages == ["auto"]

    def test_custom_languages(self):
        assert DoclingService(ocr_languages=["eng", "deu"]).ocr_languages == [
            "eng",
            "deu",
        ]

    def test_empty_languages_falls_back_to_auto(self):
        # Empty list is falsy -> defaults to ["auto"].
        assert DoclingService(ocr_languages=[]).ocr_languages == ["auto"]

    def test_converter_cache_starts_empty(self):
        assert DoclingService()._converters == {}


# --------------------------------------------------------------------------- #
# _get_text_probe_page_indices  (static, pure)
# --------------------------------------------------------------------------- #
class TestPageProbeIndices:
    def test_zero_pages(self):
        assert (
            DoclingService._get_text_probe_page_indices(
                num_pages=0, max_pages_to_check=8
            )
            == []
        )

    def test_negative_pages(self):
        assert (
            DoclingService._get_text_probe_page_indices(
                num_pages=-3, max_pages_to_check=8
            )
            == []
        )

    def test_max_zero(self):
        assert (
            DoclingService._get_text_probe_page_indices(
                num_pages=5, max_pages_to_check=0
            )
            == []
        )

    def test_max_negative(self):
        assert (
            DoclingService._get_text_probe_page_indices(
                num_pages=5, max_pages_to_check=-1
            )
            == []
        )

    def test_small_pdf_all_pages(self):
        assert DoclingService._get_text_probe_page_indices(
            num_pages=5, max_pages_to_check=8
        ) == [0, 1, 2, 3, 4]

    def test_exact_boundary_all_pages(self):
        assert DoclingService._get_text_probe_page_indices(
            num_pages=8, max_pages_to_check=8
        ) == list(range(8))

    def test_max_one_returns_first_page(self):
        assert DoclingService._get_text_probe_page_indices(
            num_pages=10, max_pages_to_check=1
        ) == [0]

    def test_evenly_spaced_sampling(self):
        idx = DoclingService._get_text_probe_page_indices(
            num_pages=100, max_pages_to_check=8
        )
        assert idx == [0, 14, 28, 42, 57, 71, 85, 99]

    def test_sampling_always_includes_first_and_last(self):
        for n in (9, 17, 33, 250):
            idx = DoclingService._get_text_probe_page_indices(
                num_pages=n, max_pages_to_check=8
            )
            assert idx[0] == 0
            assert idx[-1] == n - 1

    def test_sampling_is_sorted_and_deduped(self):
        idx = DoclingService._get_text_probe_page_indices(
            num_pages=9, max_pages_to_check=8
        )
        assert idx == sorted(idx)
        assert len(idx) == len(set(idx))
        assert len(idx) <= 8


# --------------------------------------------------------------------------- #
# _has_useful_text  (static, pure)
# --------------------------------------------------------------------------- #
class TestHasUsefulText:
    def test_empty_string_false(self):
        assert DoclingService._has_useful_text("") is False

    def test_enough_plain_text_true(self):
        assert DoclingService._has_useful_text("a" * 100) is True

    def test_just_under_threshold_false(self):
        assert DoclingService._has_useful_text("a" * 99) is False

    def test_markdown_only_stripped_to_nothing(self):
        assert DoclingService._has_useful_text("|---|---|\n| | |", min_chars=5) is False

    def test_custom_min_chars(self):
        assert DoclingService._has_useful_text("hello", min_chars=5) is True
        assert DoclingService._has_useful_text("hell", min_chars=5) is False

    def test_markdown_noise_removed_but_real_text_kept(self):
        assert (
            DoclingService._has_useful_text("## Hello **World** here", min_chars=5)
            is True
        )

    def test_whitespace_collapsed_markdown_only(self):
        # Only markdown chars + whitespace -> cleaned to "" -> False.
        assert (
            DoclingService._has_useful_text("#  *  _  >  -  |  :  [](){}", min_chars=1)
            is False
        )


# --------------------------------------------------------------------------- #
# has_embedded_text — real fixtures
# --------------------------------------------------------------------------- #
class TestHasEmbeddedTextFixtures:
    def test_text_pdf_true(self):
        content = (FILES / "9874562_text.pdf").read_bytes()
        assert DoclingService().has_embedded_text(content) is True

    def test_scanned_pdf_false(self):
        content = (FILES / "9874562_notext.pdf").read_bytes()
        assert DoclingService().has_embedded_text(content) is False

    def test_text_pdf_below_high_min_chars_is_false(self):
        # Force the threshold so high no page can satisfy it -> exercises the
        # final ``return False`` after all sampled pages are checked.
        content = (FILES / "9874562_text.pdf").read_bytes()
        assert (
            DoclingService().has_embedded_text(content, min_chars=10_000_000) is False
        )


# --------------------------------------------------------------------------- #
# has_embedded_text — edge cases (patched PdfReader)
# --------------------------------------------------------------------------- #
class _FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class _FakeReader:
    def __init__(self, pages):
        self.pages = pages


class TestHasEmbeddedTextEdges:
    def test_unreadable_bytes_returns_false(self):
        # PdfReader raises -> caught -> False.
        assert DoclingService().has_embedded_text(b"not a pdf at all") is False

    def test_zero_pages_returns_false(self, monkeypatch):
        monkeypatch.setattr(ds, "PdfReader", lambda _stream: _FakeReader([]))
        assert DoclingService().has_embedded_text(b"anything") is False

    def test_page_extract_raises_is_swallowed(self, monkeypatch):
        class _BoomPage:
            def extract_text(self):
                raise RuntimeError("bad page")

        monkeypatch.setattr(ds, "PdfReader", lambda _stream: _FakeReader([_BoomPage()]))
        # The single page throws; no useful text accrues -> False.
        assert DoclingService().has_embedded_text(b"anything") is False

    def test_early_exit_on_useful_text(self, monkeypatch):
        pages = [_FakePage("word " * 50)] + [_FakePage("x")] * 20
        monkeypatch.setattr(ds, "PdfReader", lambda _stream: _FakeReader(pages))
        assert DoclingService().has_embedded_text(b"anything", min_chars=50) is True

    def test_extract_returns_none_treated_as_empty(self, monkeypatch):
        monkeypatch.setattr(
            ds, "PdfReader", lambda _stream: _FakeReader([_FakePage(None)])
        )
        assert DoclingService().has_embedded_text(b"anything") is False


# --------------------------------------------------------------------------- #
# _get_converter — option branching (patched DocumentConverter, no models)
# --------------------------------------------------------------------------- #
class TestGetConverterBranching:
    def _capture(self, monkeypatch):
        """Patch DocumentConverter to capture the format_options it was built with."""
        captured = {}

        def fake_dc(*, format_options):
            captured["fmt"] = format_options
            return MagicMock(name="DocumentConverter")

        monkeypatch.setattr(ds, "DocumentConverter", fake_dc)
        return captured

    def _pdf_pipeline_options(self, captured):
        return captured["fmt"][ds.InputFormat.PDF].pipeline_options

    def test_no_ocr_disables_ocr(self, monkeypatch):
        captured = self._capture(monkeypatch)
        DoclingService()._get_converter(DoclingMode.NO_OCR)
        po = self._pdf_pipeline_options(captured)
        assert po.do_ocr is False

    def test_tesseract_ocr_enables_non_forced_ocr(self, monkeypatch):
        captured = self._capture(monkeypatch)
        DoclingService(ocr_languages=["eng"])._get_converter(DoclingMode.TESSERACT_OCR)
        po = self._pdf_pipeline_options(captured)
        assert po.do_ocr is True
        assert po.ocr_options.force_full_page_ocr is False
        assert po.ocr_options.lang == ["eng"]

    def test_tesseract_force_ocr_forces_full_page(self, monkeypatch):
        captured = self._capture(monkeypatch)
        DoclingService(ocr_languages=["deu"])._get_converter(
            DoclingMode.TESSERACT_FORCE_OCR
        )
        po = self._pdf_pipeline_options(captured)
        assert po.do_ocr is True
        assert po.ocr_options.force_full_page_ocr is True
        assert po.ocr_options.lang == ["deu"]

    def test_image_format_option_registered(self, monkeypatch):
        captured = self._capture(monkeypatch)
        DoclingService()._get_converter(DoclingMode.NO_OCR)
        assert ds.InputFormat.IMAGE in captured["fmt"]

    def test_converter_is_cached_per_mode(self, monkeypatch):
        self._capture(monkeypatch)
        svc = DoclingService()
        first = svc._get_converter(DoclingMode.NO_OCR)
        second = svc._get_converter(DoclingMode.NO_OCR)
        assert first is second
        assert svc._converters[DoclingMode.NO_OCR] is first

    def test_unsupported_mode_raises_value_error(self, monkeypatch):
        self._capture(monkeypatch)
        with pytest.raises(ValueError, match="Unsupported Docling mode"):
            DoclingService()._get_converter("bogus_mode")  # type: ignore[arg-type]

    def test_artifacts_path_env_is_passed(self, monkeypatch):
        captured = self._capture(monkeypatch)
        monkeypatch.setenv("DOCLING_ARTIFACTS_PATH", "/tmp/some-artifacts")
        DoclingService()._get_converter(DoclingMode.NO_OCR)
        po = self._pdf_pipeline_options(captured)
        assert str(po.artifacts_path) == "/tmp/some-artifacts"


# --------------------------------------------------------------------------- #
# process — patched converter (no real conversion / model loading)
# --------------------------------------------------------------------------- #
class TestProcess:
    def _stub_converter(self, service, markdown, *, capture_paths=None):
        """Replace service._get_converter with one returning a mock converter."""
        mock_converter = MagicMock(name="converter")

        def convert(path):
            if capture_paths is not None:
                capture_paths.append(path)
            result = MagicMock()
            result.document.export_to_markdown.return_value = markdown
            return result

        mock_converter.convert.side_effect = convert
        service._get_converter = lambda mode: mock_converter  # type: ignore[method-assign]
        return mock_converter

    def test_returns_exported_markdown(self):
        svc = DoclingService()
        self._stub_converter(svc, "# Hello Markdown")
        assert svc.process(b"pdf-bytes") == "# Hello Markdown"

    def test_temp_file_written_and_cleaned_up(self):
        svc = DoclingService()
        paths: list[str] = []
        self._stub_converter(svc, "ok", capture_paths=paths)

        result = svc.process(b"content-here", suffix=".pdf")

        assert result == "ok"
        assert len(paths) == 1
        tmp_path = paths[0]
        # The temp file existed during conversion but is removed afterwards.
        assert tmp_path.endswith(".pdf")
        assert not os.path.exists(tmp_path)

    def test_suffix_is_applied_to_temp_file(self):
        svc = DoclingService()
        paths: list[str] = []
        self._stub_converter(svc, "ok", capture_paths=paths)
        svc.process(b"img-bytes", suffix=".png")
        assert paths[0].endswith(".png")

    def test_content_is_written_to_temp_file(self):
        svc = DoclingService()
        written: dict[str, bytes] = {}

        def convert(path):
            written["bytes"] = Path(path).read_bytes()
            result = MagicMock()
            result.document.export_to_markdown.return_value = "ok"
            return result

        mock_converter = MagicMock()
        mock_converter.convert.side_effect = convert
        svc._get_converter = lambda mode: mock_converter  # type: ignore[method-assign]

        svc.process(b"the-real-bytes")
        assert written["bytes"] == b"the-real-bytes"

    def test_conversion_error_wrapped_in_service_error(self):
        svc = DoclingService()
        mock_converter = MagicMock()
        mock_converter.convert.side_effect = RuntimeError("boom")
        svc._get_converter = lambda mode: mock_converter  # type: ignore[method-assign]

        with pytest.raises(DoclingServiceError, match="Docling conversion failed"):
            svc.process(b"pdf-bytes")

    def test_temp_file_cleaned_up_even_on_error(self):
        svc = DoclingService()
        paths: list[str] = []

        def convert(path):
            paths.append(path)
            raise RuntimeError("boom")

        mock_converter = MagicMock()
        mock_converter.convert.side_effect = convert
        svc._get_converter = lambda mode: mock_converter  # type: ignore[method-assign]

        with pytest.raises(DoclingServiceError):
            svc.process(b"pdf-bytes")

        assert len(paths) == 1
        # ``finally`` block removes the temp file despite the failure.
        assert not os.path.exists(paths[0])

    def test_original_exception_chained(self):
        svc = DoclingService()
        original = ValueError("root cause")
        mock_converter = MagicMock()
        mock_converter.convert.side_effect = original
        svc._get_converter = lambda mode: mock_converter  # type: ignore[method-assign]

        with pytest.raises(DoclingServiceError) as exc_info:
            svc.process(b"pdf-bytes")
        assert exc_info.value.__cause__ is original

    def test_mode_is_forwarded_to_get_converter(self):
        svc = DoclingService()
        seen_modes: list[DoclingMode] = []

        def get_converter(mode):
            seen_modes.append(mode)
            mock_converter = MagicMock()
            mock_converter.convert.return_value.document.export_to_markdown.return_value = "ok"
            return mock_converter

        svc._get_converter = get_converter  # type: ignore[method-assign]
        svc.process(b"pdf-bytes", mode=DoclingMode.TESSERACT_FORCE_OCR)
        assert seen_modes == [DoclingMode.TESSERACT_FORCE_OCR]
