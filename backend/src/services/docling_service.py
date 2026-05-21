"""Docling service for text-only PDF extraction (no OCR)."""

import logging
import tempfile
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

logger = logging.getLogger(__name__)


class DoclingServiceError(Exception):
    """Raised when Docling processing fails."""


class DoclingService:
    """Service that extracts text from PDFs using Docling DocumentConverter.

    This performs text extraction only — no OCR is applied.
    """

    def __init__(self):
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def process(self, file_content: bytes) -> str:
        """Extract markdown text from a PDF document.

        Args:
            file_content: Raw PDF file bytes.

        Returns:
            Document text as markdown.
        """
        # Write bytes to a temporary file (Docling requires a file path)
        suffix = ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            result = self.converter.convert(tmp_path)
            markdown_text = result.document.export_to_markdown()
            return markdown_text
        except Exception as e:
            raise DoclingServiceError(f"Docling conversion failed: {e}")
        finally:
            # Clean up temp file
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                logger.warning("Failed to clean up temp file: %s", tmp_path)
