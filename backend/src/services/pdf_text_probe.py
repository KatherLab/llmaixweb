# backend/src/services/pdf_text_probe.py
"""Lightweight PDF embedded text detection using pypdf.

This module provides a standalone function for checking if a PDF
contains useful embedded text, without requiring Docling imports.
This allows the main preprocessing pipeline to make routing decisions
before calling docling-serve.
"""

import io
import logging
import re

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def has_embedded_text(
    file_content: bytes,
    *,
    min_chars: int = 100,
    max_pages_to_check: int = 8,
) -> bool:
    """Return True if the PDF appears to contain useful embedded text.

    This is a lightweight pre-check using pypdf.

    For small PDFs, all pages are checked.
    For larger PDFs, evenly spaced pages are sampled.
    The method exits early once enough useful text is found.

    Args:
        file_content: Raw PDF file bytes.
        min_chars: Minimum number of cleaned characters to consider text useful.
        max_pages_to_check: Maximum number of pages to sample.

    Returns:
        True if useful embedded text is detected, False otherwise.
    """
    try:
        reader = PdfReader(io.BytesIO(file_content))
    except Exception:
        logger.warning(
            "Failed to read PDF for embedded-text pre-check",
            exc_info=True,
        )
        return False

    num_pages = len(reader.pages)
    if num_pages == 0:
        return False

    page_indices = _get_text_probe_page_indices(
        num_pages=num_pages,
        max_pages_to_check=max_pages_to_check,
    )

    text_parts: list[str] = []

    for idx in page_indices:
        try:
            page_text = reader.pages[idx].extract_text() or ""
        except Exception:
            page_text = ""

        if page_text:
            text_parts.append(page_text)

        if _has_useful_text("\n".join(text_parts), min_chars=min_chars):
            return True

    return False


def _get_text_probe_page_indices(
    *,
    num_pages: int,
    max_pages_to_check: int,
) -> list[int]:
    """Return page indices for lightweight text probing.

    For small PDFs, all pages are checked.
    For larger PDFs, evenly spaced pages are sampled.

    Args:
        num_pages: Total number of pages in the PDF.
        max_pages_to_check: Maximum number of pages to sample.

    Returns:
        List of page indices to check.
    """
    if num_pages <= 0:
        return []

    if max_pages_to_check <= 0:
        return []

    if num_pages <= max_pages_to_check:
        return list(range(num_pages))

    if max_pages_to_check == 1:
        return [0]

    return sorted(
        {
            round(i * (num_pages - 1) / (max_pages_to_check - 1))
            for i in range(max_pages_to_check)
        }
    )


def _has_useful_text(text: str, *, min_chars: int = 100) -> bool:
    """Return True if text contains enough non-artifact content.

    Strips common Markdown/table syntax to avoid accepting page
    artifacts or formatting noise as useful content.

    Args:
        text: Text content to check.
        min_chars: Minimum number of cleaned characters required.

    Returns:
        True if text contains useful content, False otherwise.
    """
    if not text:
        return False

    cleaned = re.sub(r"[#*_`>\-|:\[\]\(\){}]+", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return len(cleaned) >= min_chars
