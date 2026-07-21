"""Unit tests for ``backend/src/services/pdf_text_probe.py``.

Covers the two pure helpers (page-sampling math and the markdown-stripping
useful-text threshold) directly, plus ``has_embedded_text`` against the real
PDF fixtures (a text PDF and a scanned/no-text PDF) and a couple of patched
edge cases (empty/0-page, unreadable bytes).
"""

from pathlib import Path

from backend.src.services import pdf_text_probe
from backend.src.services.pdf_text_probe import (
    _get_text_probe_page_indices,
    _has_useful_text,
    has_embedded_text,
)

FILES = Path(__file__).parent / "files"


# --------------------------------------------------------------------------- #
# _get_text_probe_page_indices
# --------------------------------------------------------------------------- #
class TestPageProbeIndices:
    def test_zero_pages(self):
        assert _get_text_probe_page_indices(num_pages=0, max_pages_to_check=8) == []

    def test_negative_pages(self):
        assert _get_text_probe_page_indices(num_pages=-3, max_pages_to_check=8) == []

    def test_max_zero(self):
        assert _get_text_probe_page_indices(num_pages=5, max_pages_to_check=0) == []

    def test_max_negative(self):
        assert _get_text_probe_page_indices(num_pages=5, max_pages_to_check=-1) == []

    def test_small_pdf_all_pages(self):
        assert _get_text_probe_page_indices(num_pages=5, max_pages_to_check=8) == [
            0,
            1,
            2,
            3,
            4,
        ]

    def test_exact_boundary_all_pages(self):
        assert _get_text_probe_page_indices(num_pages=8, max_pages_to_check=8) == list(
            range(8)
        )

    def test_max_one_returns_first_page(self):
        assert _get_text_probe_page_indices(num_pages=10, max_pages_to_check=1) == [0]

    def test_evenly_spaced_sampling(self):
        idx = _get_text_probe_page_indices(num_pages=100, max_pages_to_check=8)
        assert idx == [0, 14, 28, 42, 57, 71, 85, 99]

    def test_sampling_always_includes_first_and_last(self):
        for n in (9, 17, 33, 250):
            idx = _get_text_probe_page_indices(num_pages=n, max_pages_to_check=8)
            assert idx[0] == 0
            assert idx[-1] == n - 1

    def test_sampling_is_sorted_and_deduped(self):
        idx = _get_text_probe_page_indices(num_pages=9, max_pages_to_check=8)
        assert idx == sorted(idx)
        assert len(idx) == len(set(idx))
        assert len(idx) <= 8


# --------------------------------------------------------------------------- #
# _has_useful_text
# --------------------------------------------------------------------------- #
class TestHasUsefulText:
    def test_empty_string_false(self):
        assert _has_useful_text("") is False

    def test_enough_plain_text_true(self):
        assert _has_useful_text("a" * 100) is True

    def test_just_under_threshold_false(self):
        assert _has_useful_text("a" * 99) is False

    def test_markdown_only_stripped_to_nothing(self):
        assert _has_useful_text("|---|---|\n| | |", min_chars=5) is False

    def test_custom_min_chars(self):
        assert _has_useful_text("hello", min_chars=5) is True
        assert _has_useful_text("hell", min_chars=5) is False

    def test_markdown_noise_removed_but_real_text_kept(self):
        assert _has_useful_text("## Hello **World** here", min_chars=5) is True

    def test_whitespace_collapsed(self):
        # Only markdown chars + whitespace -> cleaned to "" -> False.
        assert _has_useful_text("#  *  _  >  -  |  :  [](){}", min_chars=1) is False


# --------------------------------------------------------------------------- #
# has_embedded_text — real fixtures
# --------------------------------------------------------------------------- #
class TestHasEmbeddedTextFixtures:
    def test_text_pdf_true(self):
        content = (FILES / "9874562_text.pdf").read_bytes()
        assert has_embedded_text(content) is True

    def test_scanned_pdf_false(self):
        content = (FILES / "9874562_notext.pdf").read_bytes()
        assert has_embedded_text(content) is False

    def test_text_pdf_below_high_min_chars_is_false(self):
        # Force the threshold so high no page can satisfy it -> exercises the
        # final `return False` after all sampled pages are checked.
        content = (FILES / "9874562_text.pdf").read_bytes()
        assert has_embedded_text(content, min_chars=10_000_000) is False


# --------------------------------------------------------------------------- #
# has_embedded_text — edge cases
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
        assert has_embedded_text(b"not a pdf at all") is False

    def test_zero_pages_returns_false(self, monkeypatch):
        monkeypatch.setattr(
            pdf_text_probe, "PdfReader", lambda _stream: _FakeReader([])
        )
        assert has_embedded_text(b"anything") is False

    def test_page_extract_raises_is_swallowed(self, monkeypatch):
        class _BoomPage:
            def extract_text(self):
                raise RuntimeError("bad page")

        monkeypatch.setattr(
            pdf_text_probe, "PdfReader", lambda _stream: _FakeReader([_BoomPage()])
        )
        # The single page throws; no useful text accrues -> False.
        assert has_embedded_text(b"anything") is False

    def test_early_exit_on_useful_text(self, monkeypatch):
        pages = [_FakePage("word " * 50)] + [_FakePage("x")] * 20
        monkeypatch.setattr(
            pdf_text_probe, "PdfReader", lambda _stream: _FakeReader(pages)
        )
        assert has_embedded_text(b"anything", min_chars=50) is True

    def test_extract_returns_none_treated_as_empty(self, monkeypatch):
        monkeypatch.setattr(
            pdf_text_probe,
            "PdfReader",
            lambda _stream: _FakeReader([_FakePage(None)]),
        )
        assert has_embedded_text(b"anything") is False
