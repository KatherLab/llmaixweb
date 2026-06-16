# backend/src/services/docling_serve_client.py
"""HTTP client for calling docling-serve API.

This module provides a lightweight HTTP client for interacting with
a separate docling-serve instance. This allows the main FastAPI/Celery
app to avoid importing or initializing Docling directly, reducing
memory usage and avoiding duplicate model loading in Celery workers.

The client uses multipart/form-data requests to /v1/convert/file,
which is more memory-efficient than base64-encoded JSON payloads.

Fallback behavior (only when DOCLING_LOCAL_FALLBACK=true):
- If docling-serve is unavailable (connection error), falls back to local Docling.
- This is useful for local testing and development.
"""

import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


class DoclingServeError(Exception):
    """Raised when docling-serve API call fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
        endpoint: str | None = None,
        filename: str | None = None,
        ocr_mode: str | None = None,
    ):
        self.status_code = status_code
        self.response_body = response_body
        self.endpoint = endpoint
        self.filename = filename
        self.ocr_mode = ocr_mode

        error_parts = [message]
        if status_code:
            error_parts.append(f"HTTP {status_code}")
        if endpoint:
            error_parts.append(f"Endpoint: {endpoint}")
        if filename:
            error_parts.append(f"File: {filename}")
        if ocr_mode:
            error_parts.append(f"OCR mode: {ocr_mode}")
        if response_body:
            excerpt = response_body[:200] if len(response_body) > 200 else response_body
            error_parts.append(f"Response: {excerpt}")

        super().__init__(" | ".join(error_parts))


@dataclass
class DoclingServeResult:
    """Result from docling-serve conversion."""

    text: str
    raw_response: dict | None = None
    warnings: list[str] = field(default_factory=list)


class DoclingServeClient:
    """HTTP client for docling-serve API.

    Args:
        base_url: Base URL of docling-serve instance.
        timeout_seconds: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        default_ocr_langs: Default OCR languages for Tesseract.
    """

    def __init__(
        self,
        base_url: str,
        timeout_seconds: int = 600,
        max_retries: int = 1,
        default_ocr_langs: list[str] | str | None = None,
    ):
        if not base_url:
            raise DoclingServeError("docling-serve base URL is required")

        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        # Default to "auto" for automatic language detection
        self.default_ocr_langs = default_ocr_langs or "auto"

        self._client = httpx.Client(timeout=timeout_seconds)

    def convert_pdf_no_ocr(
        self,
        file_content: bytes,
        filename: str,
    ) -> DoclingServeResult:
        """Convert PDF using embedded text only (no OCR).

        Args:
            file_content: Raw PDF file bytes.
            filename: Original filename (for logging).

        Returns:
            DoclingServeResult with extracted Markdown.

        Raises:
            DoclingServeError: If conversion fails.
        """
        return self._convert(
            file_content=file_content,
            filename=filename,
            mime_type="application/pdf",
            from_formats=["pdf"],
            do_ocr=False,
            force_ocr=False,
        )

    def convert_pdf_tesseract(
        self,
        file_content: bytes,
        filename: str,
        *,
        force_ocr: bool = False,
        ocr_langs: list[str] | str | None = None,
    ) -> DoclingServeResult:
        """Convert PDF using Tesseract OCR.

        Args:
            file_content: Raw PDF file bytes.
            filename: Original filename (for logging).
            force_ocr: If True, force full-page OCR even if embedded text exists.
            ocr_langs: OCR languages (defaults to instance default). Use "auto" for automatic detection.

        Returns:
            DoclingServeResult with extracted Markdown.

        Raises:
            DoclingServeError: If conversion fails.
        """
        return self._convert(
            file_content=file_content,
            filename=filename,
            mime_type="application/pdf",
            from_formats=["pdf"],
            do_ocr=True,
            force_ocr=force_ocr,
            ocr_engine="tesseract",
            ocr_langs=ocr_langs if ocr_langs is not None else self.default_ocr_langs,
        )

    def convert_image_tesseract(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        *,
        ocr_langs: list[str] | str | None = None,
    ) -> DoclingServeResult:
        """Convert image using Tesseract OCR.

        Args:
            file_content: Raw image file bytes.
            filename: Original filename (for logging).
            mime_type: MIME type of the image (image/png, image/jpeg, etc.).
            ocr_langs: OCR languages (defaults to instance default). Use "auto" for automatic detection.

        Returns:
            DoclingServeResult with extracted Markdown.

        Raises:
            DoclingServeError: If conversion fails.
        """
        return self._convert(
            file_content=file_content,
            filename=filename,
            mime_type=mime_type,
            from_formats=["image"],
            do_ocr=True,
            force_ocr=True,
            ocr_engine="tesseract",
            ocr_langs=ocr_langs if ocr_langs is not None else self.default_ocr_langs,
        )

    def _convert(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        from_formats: list[str],
        do_ocr: bool,
        force_ocr: bool,
        ocr_engine: str | None = None,
        ocr_langs: list[str] | str | None = None,
    ) -> DoclingServeResult:
        """Send conversion request to docling-serve.

        Uses multipart/form-data to /v1/convert/file endpoint.

        Args:
            file_content: Raw file bytes.
            filename: Original filename.
            mime_type: MIME type of the file.
            from_formats: Input formats (e.g., ["pdf"], ["image"]).
            do_ocr: Whether to enable OCR.
            force_ocr: Whether to force full-page OCR.
            ocr_engine: OCR engine name (e.g., "tesseract").
            ocr_langs: OCR languages.

        Returns:
            DoclingServeResult with extracted Markdown.

        Raises:
            DoclingServeError: If conversion fails.
        """
        endpoint = f"{self.base_url}/v1/convert/file"

        # Build multipart form data
        files = {
            "files": (filename, file_content, mime_type),
        }

        # Note: from_formats and to_formats should be comma-separated strings,
        # not lists, for multipart form data
        data = {
            "from_formats": ",".join(from_formats)
            if isinstance(from_formats, list)
            else from_formats,
            "to_formats": "md",
            "do_ocr": str(do_ocr).lower(),
            "force_ocr": str(force_ocr).lower(),
            "table_mode": "fast",
            "abort_on_error": "false",
        }

        # Only set image_export_mode when OCR is disabled.
        # When do_ocr=true, docling-serve needs to export images for OCR,
        # so we let it use its default behavior (omitting the parameter).
        if not do_ocr:
            data["image_export_mode"] = "placeholder"

        # Add OCR-specific fields if OCR is enabled
        if do_ocr:
            if ocr_engine:
                data["ocr_preset"] = ocr_engine
            if ocr_langs:
                # Encode list as comma-separated string for multipart form.
                # If ocr_langs is "auto", omit the parameter to let Tesseract use system default.
                if isinstance(ocr_langs, list):
                    data["ocr_lang"] = ",".join(ocr_langs)
                elif ocr_langs.lower() != "auto":
                    data["ocr_lang"] = ocr_langs

        last_error: DoclingServeError | None = None

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    "Calling docling-serve: %s (attempt %d/%d, OCR=%s, force=%s)",
                    endpoint,
                    attempt + 1,
                    self.max_retries + 1,
                    do_ocr,
                    force_ocr,
                )

                response = self._client.post(endpoint, files=files, data=data)

                if response.status_code != 200:
                    raise DoclingServeError(
                        "docling-serve returned error",
                        status_code=response.status_code,
                        response_body=response.text[:500],
                        endpoint=endpoint,
                        filename=filename,
                        ocr_mode=f"do_ocr={do_ocr}, force_ocr={force_ocr}",
                    )

                response_json = response.json()
                text = _extract_markdown(response_json)

                warnings = _extract_warnings(response_json)

                return DoclingServeResult(
                    text=text,
                    raw_response=response_json,
                    warnings=warnings,
                )

            except httpx.TimeoutException as e:
                last_error = DoclingServeError(
                    f"docling-serve request timed out after {self.timeout_seconds}s",
                    endpoint=endpoint,
                    filename=filename,
                    ocr_mode=f"do_ocr={do_ocr}, force_ocr={force_ocr}",
                )
                logger.warning("docling-serve timeout: %s", e)

            except httpx.RequestError as e:
                # Connection error - check if we should fall back to local Docling
                # Import settings here to avoid circular imports
                from ..core.config import settings

                if settings.DOCLING_LOCAL_FALLBACK:
                    logger.info(
                        "docling-serve unavailable, falling back to local Docling: %s",
                        e,
                    )
                    return _convert_with_local_docling(
                        file_content=file_content,
                        filename=filename,
                        mime_type=mime_type,
                        from_formats=from_formats,
                        do_ocr=do_ocr,
                        force_ocr=force_ocr,
                        ocr_engine=ocr_engine,
                        ocr_langs=ocr_langs,
                    )
                else:
                    last_error = DoclingServeError(
                        f"docling-serve request failed: {e}",
                        endpoint=endpoint,
                        filename=filename,
                        ocr_mode=f"do_ocr={do_ocr}, force_ocr={force_ocr}",
                    )
                    logger.warning("docling-serve request error: %s", e)

            except DoclingServeError as e:
                last_error = e
                logger.warning("docling-serve error (attempt %d): %s", attempt + 1, e)

        # All retries exhausted
        raise last_error or DoclingServeError(
            "docling-serve conversion failed after all retries",
            endpoint=endpoint,
            filename=filename,
        )

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def _convert_with_local_docling(
    file_content: bytes,
    filename: str,
    mime_type: str,
    from_formats: list[str],
    do_ocr: bool,
    force_ocr: bool,
    ocr_engine: str | None = None,
    ocr_langs: list[str] | None = None,
) -> DoclingServeResult:
    """Fallback: convert using local Docling installation.

    This is only used when DOCLING_LOCAL_FALLBACK=true and docling-serve is unavailable.
    Useful for local testing and development.

    Args:
        file_content: Raw file bytes.
        filename: Original filename.
        mime_type: MIME type of the file.
        from_formats: Input formats (e.g., ["pdf"], ["image"]).
        do_ocr: Whether to enable OCR.
        force_ocr: Whether to force full-page OCR.
        ocr_engine: OCR engine name (e.g., "tesseract").
        ocr_langs: OCR languages.

    Returns:
        DoclingServeResult with extracted Markdown.

    Raises:
        DoclingServeError: If local conversion fails.
    """
    try:
        from docling.datamodel.accelerator_options import (
            AcceleratorDevice,
            AcceleratorOptions,
        )
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
    except ImportError:
        raise DoclingServeError(
            "Local Docling fallback enabled but docling package not installed. "
            "Set DOCLING_LOCAL_FALLBACK=false or install docling."
        )

    import tempfile
    from pathlib import Path

    # Determine Docling mode based on OCR settings
    is_pdf = "pdf" in from_formats
    is_image = "image" in from_formats

    # Build pipeline options
    pipeline_options = PdfPipelineOptions(do_ocr=do_ocr)
    pipeline_options.accelerator_options = AcceleratorOptions(
        device=AcceleratorDevice.CPU
    )

    if do_ocr and ocr_engine == "tesseract":
        pipeline_options.ocr_options = TesseractCliOcrOptions(
            lang=ocr_langs or ["eng"],
            force_full_page_ocr=force_ocr,
        )

    # Build format options
    format_options = {}
    if is_pdf:
        format_options[InputFormat.PDF] = PdfFormatOption(
            pipeline_options=pipeline_options
        )
    if is_image:
        format_options[InputFormat.IMAGE] = ImageFormatOption(
            pipeline_options=pipeline_options
        )

    if not format_options:
        raise DoclingServeError(f"No format options for from_formats: {from_formats}")

    converter = DocumentConverter(format_options=format_options)

    # Write to temp file and convert
    suffix = Path(filename).suffix or (".pdf" if is_pdf else ".bin")
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        result = converter.convert(tmp_path)
        markdown = result.document.export_to_markdown()

        return DoclingServeResult(text=markdown, raw_response=None, warnings=[])

    except Exception as e:
        raise DoclingServeError(f"Local Docling conversion failed: {e}")
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass


def _extract_markdown(response_json: dict) -> str:
    """Extract Markdown text from docling-serve response.

    The exact response schema may vary depending on docling-serve version.
    This function tries multiple common field names and structures.

    Expected response format (docling-serve v1):
    {
        "document": {
            "md_content": "...",  # or "markdown"
            ...
        },
        "status": "success",
        "processing_time": 1.23,
        ...
    }

    Args:
        response_json: Parsed JSON response from docling-serve.

    Returns:
        Extracted Markdown text.

    Raises:
        DoclingServeError: If no Markdown can be extracted.
    """
    candidates: list[str] = []

    # Try top-level fields first
    for key in ["md_content", "markdown", "text", "content"]:
        value = response_json.get(key)
        if isinstance(value, str):
            candidates.append(value.strip())

    # Try nested "document" object (singular) - common in docling-serve
    document = response_json.get("document")
    if isinstance(document, dict):
        for key in ["md_content", "markdown", "text", "content"]:
            value = document.get(key)
            if isinstance(value, str):
                candidates.append(value.strip())

        # Also check nested output formats within document
        output = document.get("output") or document.get("outputs")
        if isinstance(output, dict):
            for key in ["md", "markdown", "text"]:
                value = output.get(key)
                if isinstance(value, str):
                    candidates.append(value.strip())

    # Try nested document list fields
    for list_key in ["documents", "results", "converted_documents", "output"]:
        items = response_json.get(list_key)
        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue

            # Check for direct markdown field
            for key in ["md_content", "markdown", "text", "content"]:
                value = item.get(key)
                if isinstance(value, str):
                    candidates.append(value.strip())

            # Check for nested output formats
            output = item.get("output") or item.get("outputs")
            if isinstance(output, dict):
                for key in ["md", "markdown", "text"]:
                    value = output.get(key)
                    if isinstance(value, str):
                        candidates.append(value.strip())

    # Join all found candidates
    text = "\n\n".join(c.strip() for c in candidates if c and c.strip()).strip()

    if not text:
        available_keys = list(response_json.keys())
        raise DoclingServeError(
            f"Could not extract Markdown from docling-serve response. "
            f"Available keys: {available_keys}"
        )

    return text


def _extract_warnings(response_json: dict) -> list[str]:
    """Extract warnings from docling-serve response.

    Args:
        response_json: Parsed JSON response from docling-serve.

    Returns:
        List of warning messages (may be empty).
    """
    warnings: list[str] = []

    # Check for top-level warnings
    warnings_data = response_json.get("warnings", [])
    if isinstance(warnings_data, list):
        for w in warnings_data:
            if isinstance(w, str):
                warnings.append(w)
            elif isinstance(w, dict) and "message" in w:
                warnings.append(w["message"])

    # Check for per-document warnings
    for list_key in ["documents", "results", "converted_documents"]:
        items = response_json.get(list_key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            item_warnings = item.get("warnings", [])
            if isinstance(item_warnings, list):
                for w in item_warnings:
                    if isinstance(w, str):
                        warnings.append(w)
                    elif isinstance(w, dict) and "message" in w:
                        warnings.append(w["message"])

    return warnings
