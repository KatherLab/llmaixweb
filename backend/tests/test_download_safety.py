# backend/tests/test_download_safety.py
"""Unit tests for the download-safety helpers: ZIP arcname sanitization
(zip-slip) and Content-Disposition filename encoding (header injection).
Both wrap user-controlled file names, so the hostile inputs here are the
point — no fixtures or DB needed.
"""

import io
import zipfile

from ..src.utils.helpers import content_disposition
from ..src.utils.streaming_zip import iter_zip, sanitize_arcname


class TestSanitizeArcname:
    def test_plain_name_unchanged(self):
        assert sanitize_arcname("report.pdf") == "report.pdf"

    def test_intentional_nesting_preserved(self):
        assert sanitize_arcname("files/abc_report.pdf") == "files/abc_report.pdf"
        assert sanitize_arcname("docs/42.json") == "docs/42.json"

    def test_traversal_stripped(self):
        assert sanitize_arcname("../../etc/cron.d/x") == "etc/cron.d/x"
        assert sanitize_arcname("files/../../evil.sh") == "files/evil.sh"

    def test_absolute_and_backslash_paths(self):
        assert sanitize_arcname("/etc/passwd") == "etc/passwd"
        assert sanitize_arcname("..\\..\\win\\evil.exe") == "win/evil.exe"
        assert sanitize_arcname("C:\\Users\\x.txt") == "C_/Users/x.txt"

    def test_dot_components_and_nul_dropped(self):
        assert sanitize_arcname("./a/./b") == "a/b"
        assert sanitize_arcname("a\x00b.txt") == "ab.txt"

    def test_never_empty(self):
        assert sanitize_arcname("") == "file"
        assert sanitize_arcname("../..") == "file"

    def test_iter_zip_applies_sanitization(self):
        data = b"".join(iter_zip([("../../evil.txt", b"payload")]))
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            assert zf.namelist() == ["evil.txt"]
            assert zf.read("evil.txt") == b"payload"

    def test_iter_zip_chunked_entry_round_trips(self):
        """An entry given as an iterable of chunks (streamed CSV) must produce
        a valid archive whose member equals the concatenated chunks, alongside
        plain bytes entries."""
        chunks = [b"col_a,col_b\r\n", b"1,hello\r\n", b"2,world\r\n"]
        data = b"".join(
            iter_zip(
                [
                    ("files/source.bin", b"rawbytes"),
                    ("results.csv", iter(chunks)),
                ]
            )
        )
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            assert zf.testzip() is None
            assert zf.namelist() == ["files/source.bin", "results.csv"]
            assert zf.read("files/source.bin") == b"rawbytes"
            assert zf.read("results.csv") == b"".join(chunks)

    def test_iter_zip_chunked_entry_sanitizes_name(self):
        data = b"".join(iter_zip([("../../evil.csv", iter([b"a,b\r\n"]))]))
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            assert zf.namelist() == ["evil.csv"]


class TestContentDisposition:
    def test_plain_filename(self):
        value = content_disposition("report.pdf")
        assert (
            value == "attachment; filename=\"report.pdf\"; filename*=UTF-8''report.pdf"
        )

    def test_quotes_and_crlf_neutralized(self):
        hostile = 'x".exe";\r\nX-Evil: 1'
        value = content_disposition(hostile)
        assert '"' not in value.replace('filename="', "").replace('"; filename*', "")
        assert "\r" not in value and "\n" not in value

    def test_non_ascii_percent_encoded(self):
        value = content_disposition("bericht ärztlich.pdf")
        assert value.isascii()
        assert "%C3%A4" in value

    def test_inline_disposition(self):
        assert content_disposition("a.png", "inline").startswith("inline; ")

    def test_empty_falls_back(self):
        assert "download" in content_disposition("")
