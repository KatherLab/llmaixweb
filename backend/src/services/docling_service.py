# backend/src/services/docling_service.py
"""Docling service for PDF-to-Markdown extraction with optional Tesseract OCR."""

from __future__ import annotations

import io
import logging
import os
import re
import tempfile
from enum import StrEnum
from pathlib import Path

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TesseractCliOcrOptions,
)
from docling.document_converter import (
    DocumentConverter,
    ImageFormatOption,
    PdfFormatOption,
)
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class DoclingServiceError(Exception):
    """Raised when Docling processing fails."""


class DoclingMode(StrEnum):
    """Supported Docling PDF processing modes."""

    NO_OCR = "no_ocr"
    TESSERACT_OCR = "tesseract_ocr"
    TESSERACT_FORCE_OCR = "tesseract_force_ocr"


class DoclingService:
    """Service that converts PDFs to Markdown using Docling.

    Modes:
    - NO_OCR:
        Use embedded/native PDF text only.
    - TESSERACT_OCR:
        Enable Tesseract OCR, but do not force full-page OCR.
        This is suitable for mixed PDFs.
    - TESSERACT_FORCE_OCR:
        Force full-page Tesseract OCR.
        This is suitable when the user explicitly selected force OCR.
    """

    def __init__(
        self,
        *,
        ocr_languages: list[str] | None = None,
        accelerator_device: str = "cpu",
    ):
        self.ocr_languages = ocr_languages or ["auto"]
        self.accelerator_device = accelerator_device
        self._converters: dict[DoclingMode, DocumentConverter] = {}

    def _get_accelerator_device(self) -> AcceleratorDevice:
        """Return Docling accelerator device from config string."""
        normalized = (self.accelerator_device or "cpu").lower()

        mapping = {
            "auto": AcceleratorDevice.AUTO,
            "cpu": AcceleratorDevice.CPU,
            "cuda": AcceleratorDevice.CUDA,
            "mps": AcceleratorDevice.MPS,
        }

        return mapping.get(normalized, AcceleratorDevice.CPU)

    def _get_converter(self, mode: DoclingMode) -> DocumentConverter:
        """Return a cached Docling converter for the requested mode."""
        if mode in self._converters:
            return self._converters[mode]

        artifacts_path = os.getenv("DOCLING_ARTIFACTS_PATH")
        pipeline_options = PdfPipelineOptions(
            artifacts_path=artifacts_path,
        )
        pipeline_options.accelerator_options = AcceleratorOptions(
            device=self._get_accelerator_device(),
        )

        if mode == DoclingMode.NO_OCR:
            pipeline_options.do_ocr = False

        elif mode == DoclingMode.TESSERACT_OCR:
            pipeline_options.do_ocr = True
            pipeline_options.ocr_options = TesseractCliOcrOptions(
                lang=self.ocr_languages,
                force_full_page_ocr=False,
            )

        elif mode == DoclingMode.TESSERACT_FORCE_OCR:
            pipeline_options.do_ocr = True
            pipeline_options.ocr_options = TesseractCliOcrOptions(
                lang=self.ocr_languages,
                force_full_page_ocr=True,
            )

        else:
            raise ValueError(f"Unsupported Docling mode: {mode}")

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                ),
                InputFormat.IMAGE: ImageFormatOption(
                    pipeline_options=pipeline_options,
                ),
            }
        )

        self._converters[mode] = converter
        return converter

    def has_embedded_text(
        self,
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

        page_indices = self._get_text_probe_page_indices(
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

            if self._has_useful_text("\n".join(text_parts), min_chars=min_chars):
                return True

        return False

    @staticmethod
    def _get_text_probe_page_indices(
        *,
        num_pages: int,
        max_pages_to_check: int,
    ) -> list[int]:
        """Return page indices for lightweight text probing."""
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

    @staticmethod
    def _has_useful_text(text: str, *, min_chars: int = 100) -> bool:
        """Return True if text contains enough non-artifact content."""
        if not text:
            return False

        cleaned = re.sub(r"[#*_`>\-|:\[\]\(\){}]+", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return len(cleaned) >= min_chars

    def process(
        self,
        file_content: bytes,
        *,
        mode: DoclingMode = DoclingMode.NO_OCR,
        suffix: str = ".pdf",
    ) -> str:
        """Convert a document to Markdown.

        Args:
            file_content: Raw document bytes.
            mode: Docling processing mode.
            suffix: File suffix used so Docling can infer the input format.

        Returns:
            Extracted document content as Markdown.

        Raises:
            DoclingServiceError: If conversion fails.
        """
        tmp_path: str | None = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            converter = self._get_converter(mode)
            result = converter.convert(tmp_path)
            return result.document.export_to_markdown()

        except Exception as e:
            raise DoclingServiceError(f"Docling conversion failed: {e}") from e

        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except OSError:
                    logger.warning("Failed to clean up temp file: %s", tmp_path)
