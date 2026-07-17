"""Forward-only streaming ZIP construction.

``zipfile.ZipFile`` in write mode only calls ``write()``/``tell()`` on its
output object (it records offsets from ``tell()`` and writes the central
directory on ``close()`` without seeking back). That lets us drain the bytes it
produces incrementally and stream them to the client, so a large archive
(thousands of documents, or embedded original files) is never buffered entirely
in memory before the first byte ships.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable, Iterator
from typing import Any, cast


def sanitize_arcname(name: str) -> str:
    """Neutralize path traversal in a ZIP member name (zip-slip).

    Member names often embed user-controlled file names (``files/{uuid}_{name}``),
    so a name like ``../../etc/cron.d/x`` would otherwise escape the extraction
    directory on permissive unzip tools. Intentional forward-slash nesting is
    preserved; ``..``/``.``/empty components, backslashes, drive-letter colons
    and NUL bytes are stripped.
    """
    parts: list[str] = []
    for comp in str(name).replace("\\", "/").split("/"):
        comp = comp.replace("\x00", "").replace(":", "_").strip()
        if not comp or comp in {".", ".."}:
            continue
        parts.append(comp)
    return "/".join(parts) or "file"


class StreamingZipSink:
    """A forward-only, file-like sink for :class:`zipfile.ZipFile`."""

    def __init__(self) -> None:
        self._chunks: list[bytes] = []
        self._pos = 0

    def write(self, data) -> None:
        if data:
            b = bytes(data)
            self._chunks.append(b)
            self._pos += len(b)

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = 0) -> int:
        # zipfile only uses tell() in write mode; allow the no-op seek-to-current
        # it occasionally issues, and refuse anything else rather than corrupt.
        if whence == 1 and offset == 0:
            return self._pos
        raise io.UnsupportedOperation("forward-only stream does not support seek")

    def flush(self) -> None:  # pragma: no cover - zipfile calls this
        pass

    def drain(self) -> bytes:
        if not self._chunks:
            return b""
        data = b"".join(self._chunks)
        self._chunks.clear()
        return data


def iter_zip(entries: Iterable[tuple[str, bytes]]) -> Iterator[bytes]:
    """Yield a ZIP byte-stream for ``(arcname, data)`` entries.

    ``entries`` is consumed lazily, so a producer that reads each file's bytes
    from storage on demand keeps at most one entry's payload in memory at a
    time. The archive's own compression buffers are drained after every entry.
    """
    sink = StreamingZipSink()
    zf = zipfile.ZipFile(cast(Any, sink), "w", zipfile.ZIP_DEFLATED)
    try:
        for arcname, data in entries:
            zf.writestr(sanitize_arcname(arcname), data)
            chunk = sink.drain()
            if chunk:
                yield chunk
        zf.close()  # writes the central directory
        tail = sink.drain()
        if tail:
            yield tail
    finally:
        zf.close()
