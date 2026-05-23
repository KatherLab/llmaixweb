"""Docling service for PDF-to-Markdown extraction without OCR."""

import io
import logging
import re
import tempfile
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class DoclingServiceError(Exception):
    """Raised when Docling processing fails."""


class DoclingService:
    """Service that converts PDFs to Markdown using Docling.

    OCR is disabled. This is intended for digitally born PDFs or PDFs with
    an embedded text layer. Scanned/image-only PDFs should fall back to an
    external OCR service.
    """

    def __init__(self):
        pipeline_options = PdfPipelineOptions()

        # Critical: do not run Docling OCR locally.
        pipeline_options.do_ocr = False

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                )
            }
        )

    def has_embedded_text(
        self,
        file_content: bytes,
        *,
        min_chars: int = 100,
        max_pages_to_check: int = 3,
    ) -> bool:
        """Return True if the PDF appears to contain useful embedded text.

        This is a lightweight pre-check using pypdf to decide whether to
        bother running the full Docling pipeline, or skip directly to OCR.
        """
        try:
            reader = PdfReader(io.BytesIO(file_content))
        except Exception:
            logger.warning(
                "Failed to read PDF for embedded-text pre-check", exc_info=True
            )
            return False

        text_parts: list[str] = []

        for page in reader.pages[:max_pages_to_check]:
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""

            if page_text:
                text_parts.append(page_text)

        return self._has_useful_text("\n".join(text_parts), min_chars=min_chars)

    @staticmethod
    def _has_useful_text(text: str, *, min_chars: int = 100) -> bool:
        """Return True if text contains enough non-artifact content."""
        if not text:
            return False

        cleaned = re.sub(r"[#*_`>\-|:\[\]\(\){}]+", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return len(cleaned) >= min_chars

    def process(self, file_content: bytes) -> str:
        """Convert a PDF document to Markdown.

        Args:
            file_content: Raw PDF file bytes.

        Returns:
            Extracted document content as Markdown.

        Raises:
            DoclingServiceError: If conversion fails.
        """
        tmp_path: str | None = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            result = self.converter.convert(tmp_path)
            return result.document.export_to_markdown()

        except Exception as e:
            raise DoclingServiceError(f"Docling conversion failed: {e}") from e

        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except OSError:
                    logger.warning("Failed to clean up temp file: %s", tmp_path)
