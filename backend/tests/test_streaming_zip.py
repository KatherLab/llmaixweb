# backend/tests/test_streaming_zip.py
"""Pure-unit tests for backend/src/utils/streaming_zip.py.

test_download_safety.py already covers sanitize_arcname + iter_zip basics and
name sanitization; this module targets the GAPS:
  * StreamingZipSink.write/tell/drain/flush/seek semantics
  * seek() raising io.UnsupportedOperation for non-noop seeks
  * round-tripping a produced archive back through zipfile.ZipFile
"""

import io
import zipfile

import pytest

from backend.src.utils.streaming_zip import StreamingZipSink, iter_zip


class TestStreamingZipSinkWriteTell:
    def test_write_accumulates_and_tell_advances(self):
        s = StreamingZipSink()
        assert s.tell() == 0
        s.write(b"abc")
        assert s.tell() == 3
        s.write(b"de")
        assert s.tell() == 5

    def test_write_empty_is_noop(self):
        s = StreamingZipSink()
        s.write(b"")
        s.write(None)  # falsy -> ignored, no crash
        assert s.tell() == 0
        assert s.drain() == b""

    def test_write_accepts_bytearray_and_memoryview(self):
        s = StreamingZipSink()
        s.write(bytearray(b"ab"))
        s.write(memoryview(b"cd"))
        assert s.tell() == 4
        assert s.drain() == b"abcd"


class TestStreamingZipSinkDrain:
    def test_drain_returns_and_clears_chunks(self):
        s = StreamingZipSink()
        s.write(b"hello")
        assert s.drain() == b"hello"
        # chunks cleared, but the position (offset) is NOT rewound.
        assert s.drain() == b""
        assert s.tell() == 5

    def test_drain_empty(self):
        assert StreamingZipSink().drain() == b""

    def test_drain_concatenates_in_order(self):
        s = StreamingZipSink()
        s.write(b"1")
        s.write(b"2")
        s.write(b"3")
        assert s.drain() == b"123"

    def test_tell_survives_drain_then_more_writes(self):
        s = StreamingZipSink()
        s.write(b"aaaa")
        s.drain()
        s.write(b"bb")
        assert s.tell() == 6
        assert s.drain() == b"bb"


class TestStreamingZipSinkSeek:
    def test_noop_seek_to_current_allowed(self):
        s = StreamingZipSink()
        s.write(b"xyz")
        # whence=1 (SEEK_CUR), offset 0 -> returns current position, no error.
        assert s.seek(0, 1) == 3

    def test_noop_seek_on_empty(self):
        assert StreamingZipSink().seek(0, 1) == 0

    @pytest.mark.parametrize(
        "offset,whence",
        [
            (0, 0),  # SEEK_SET even to 0 is not the whitelisted no-op
            (5, 0),
            (5, 1),  # non-zero SEEK_CUR
            (-1, 1),
            (0, 2),  # SEEK_END
            (0, io.SEEK_END),
        ],
    )
    def test_non_noop_seek_raises(self, offset, whence):
        s = StreamingZipSink()
        s.write(b"data")
        with pytest.raises(io.UnsupportedOperation):
            s.seek(offset, whence)

    def test_seek_default_whence_is_set_and_raises(self):
        # default whence=0 -> even offset 0 is refused
        with pytest.raises(io.UnsupportedOperation):
            StreamingZipSink().seek(0)


class TestStreamingZipSinkFlush:
    def test_flush_is_noop_and_returns_none(self):
        s = StreamingZipSink()
        s.write(b"x")
        assert s.flush() is None
        # flush must not touch buffered data or position
        assert s.tell() == 1
        assert s.drain() == b"x"


class TestIterZipRoundTrip:
    def test_multi_entry_bytes_round_trip(self):
        entries = [
            ("a.txt", b"alpha"),
            ("dir/b.txt", b"beta"),
            ("dir/sub/c.bin", b"\x00\x01\x02\x03"),
        ]
        blob = b"".join(iter_zip(entries))
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            assert zf.testzip() is None
            assert zf.namelist() == ["a.txt", "dir/b.txt", "dir/sub/c.bin"]
            assert zf.read("a.txt") == b"alpha"
            assert zf.read("dir/b.txt") == b"beta"
            assert zf.read("dir/sub/c.bin") == b"\x00\x01\x02\x03"

    def test_bytearray_and_memoryview_entries_round_trip(self):
        entries = [
            ("ba.txt", bytearray(b"byte-array")),
            ("mv.txt", memoryview(b"mem-view")),
        ]
        blob = b"".join(iter_zip(entries))
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            assert zf.testzip() is None
            assert zf.read("ba.txt") == b"byte-array"
            assert zf.read("mv.txt") == b"mem-view"

    def test_chunked_entry_uses_data_descriptor_and_round_trips(self):
        # A streamed (iterable-of-chunks) member exercises the zf.open() path
        # with a forward-only sink -> zipfile emits a data descriptor.
        chunks = [b"row1\n", b"row2\n", b"row3\n"]
        entries = [
            ("plain.bin", b"P"),
            ("stream.csv", iter(chunks)),
        ]
        blob = b"".join(iter_zip(entries))
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            assert zf.testzip() is None
            assert zf.namelist() == ["plain.bin", "stream.csv"]
            assert zf.read("plain.bin") == b"P"
            assert zf.read("stream.csv") == b"".join(chunks)

    def test_empty_chunk_iterable_produces_empty_member(self):
        blob = b"".join(iter_zip([("empty.csv", iter([]))]))
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            assert zf.namelist() == ["empty.csv"]
            assert zf.read("empty.csv") == b""

    def test_empty_entries_produces_valid_empty_archive(self):
        blob = b"".join(iter_zip([]))
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            assert zf.namelist() == []

    def test_stream_is_lazy_over_a_generator_of_entries(self):
        consumed = []

        def gen():
            for name, payload in [("x.txt", b"one"), ("y.txt", b"two")]:
                consumed.append(name)
                yield name, payload

        blob = b"".join(iter_zip(gen()))
        assert consumed == ["x.txt", "y.txt"]
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            assert zf.read("x.txt") == b"one"
            assert zf.read("y.txt") == b"two"
