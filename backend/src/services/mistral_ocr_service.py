# backend/src/services/mistral_ocr_service.py
"""Mistral OCR service for document text extraction with retry logic."""

import logging
import time
from dataclasses import dataclass, field

from mistralai.client import Mistral

logger = logging.getLogger(__name__)


class MistralOCRError(Exception):
    """Raised when Mistral OCR processing fails."""


@dataclass
class MistralOCRResult:
    text: str
    pages: list[str] = field(default_factory=list)


class MistralOCRService:
    """Service that sends documents to Mistral OCR API and returns markdown.

    Includes retry logic with exponential backoff for transient errors.
    """

    # HTTP status codes that should trigger a retry
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.mistral.ai",
        model: str = "mistral-ocr-latest",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_backoff: float = 2.0,
    ):
        if not api_key:
            raise MistralOCRError("Mistral API key is required")
        self.api_key = api_key
        self.server_url = base_url
        self.model = model
        self.max_retries = max_retries
        self.base_retry_delay = retry_delay
        self.retry_backoff = retry_backoff

    def _is_retryable_exception(self, exc: Exception) -> bool:
        """Check if an exception is retryable."""
        exc_str = str(exc).lower()
        # Check for retryable HTTP status codes in error message
        for status in self.RETRYABLE_STATUS_CODES:
            if str(status) in exc_str or f"{status}".lower() in exc_str:
                return True
        # Check for common retryable error patterns
        retryable_patterns = [
            "timeout",
            "connection error",
            "temporary failure",
            "rate limit",
            "service unavailable",
            "gateway",
        ]
        return any(pattern in exc_str for pattern in retryable_patterns)

    def _execute_with_retry(self, func, operation_name: str):
        """Execute a function with exponential backoff retry logic.

        Args:
            func: Function to execute (should raise exception on failure)
            operation_name: Human-readable name of the operation for logging

        Returns:
            Result of func()

        Raises:
            MistralOCRError: If all retries fail or error is not retryable
        """
        last_exception = None
        last_retryable = False

        for attempt in range(self.max_retries + 1):
            try:
                result = func()
                if attempt > 0:
                    logger.info(
                        "%s succeeded after %d retry attempts",
                        operation_name,
                        attempt,
                    )
                return result

            except Exception as e:
                last_exception = e
                last_retryable = self._is_retryable_exception(e)

                if not last_retryable:
                    # Non-retryable error, fail immediately
                    raise MistralOCRError(f"{operation_name} failed: {e}")

                if attempt == self.max_retries:
                    # All retries exhausted
                    break

                # Calculate delay with exponential backoff + jitter
                delay = self.base_retry_delay * (self.retry_backoff**attempt)
                import random

                jitter = random.uniform(0, delay * 0.1)  # 10% jitter

                logger.warning(
                    "%s failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    operation_name,
                    attempt + 1,
                    self.max_retries + 1,
                    e,
                    delay + jitter,
                )
                time.sleep(delay + jitter)

        # All retries exhausted
        raise MistralOCRError(
            f"{operation_name} failed after {self.max_retries} retries: {last_exception}"
        )

    def process(self, file_content: bytes) -> MistralOCRResult:
        """Send file content to Mistral OCR API and return concatenated markdown.

        Includes retry logic for transient errors.
        """
        # Detect document type from content bytes
        document_type: str
        try:
            import magic

            mime_type = magic.from_buffer(file_content, mime=True)
            if mime_type == "application/pdf":
                document_type = "pdf"
            elif mime_type.startswith("image/"):
                document_type = "image"
            else:
                raise MistralOCRError(f"Unsupported file type: {mime_type}")
        except ImportError:
            # Fallback: detect by file signature bytes
            if file_content[:4] == b"%PDF":
                document_type = "pdf"
            elif file_content[:8] == b"\x89PNG\r\n\x1a\n" or file_content[:2] in (
                b"\xff\xd8",
                b"BM",
            ):
                document_type = "image"
            else:
                document_type = "pdf"

        # Helper functions for each API call
        def upload_document():
            with Mistral(api_key=self.api_key, server_url=self.server_url) as mistral:
                return mistral.files.upload(
                    file={
                        "file_name": f"document.{document_type}",
                        "content": file_content,
                    },
                    purpose="ocr",
                )

        def get_signed_url(file_id: str):
            with Mistral(api_key=self.api_key, server_url=self.server_url) as mistral:
                return mistral.files.get_signed_url(file_id=file_id)

        def process_ocr(document_url: str):
            with Mistral(api_key=self.api_key, server_url=self.server_url) as mistral:
                return mistral.ocr.process(
                    model=self.model,
                    document={
                        "type": "document_url",
                        "document_url": document_url,
                    },
                )

        # Execute upload with retry
        try:
            uploaded_pdf = self._execute_with_retry(upload_document, "Document upload")
        except MistralOCRError as e:
            raise MistralOCRError(f"Failed to upload document: {e}")

        # Execute signed URL request with retry
        try:
            signed_url = self._execute_with_retry(
                lambda: get_signed_url(uploaded_pdf.id),
                "Signed URL request",
            )
        except MistralOCRError as e:
            raise MistralOCRError(f"Failed to get signed URL: {e}")

        # Execute OCR processing with retry
        try:
            ocr_response = self._execute_with_retry(
                lambda: process_ocr(signed_url.url),
                "OCR processing",
            )
        except MistralOCRError as e:
            raise MistralOCRError(f"Mistral OCR processing failed: {e}")

        # Concatenate markdown from all pages
        all_text = ""
        pages = []
        if ocr_response.pages:
            for page in ocr_response.pages:
                page_text = page.markdown or ""
                pages.append(page_text)
                all_text += page_text + "\n\n"
        else:
            # Some responses return a single markdown field
            all_text = getattr(ocr_response, "markdown", "") or ""

        return MistralOCRResult(text=all_text.strip(), pages=[p for p in pages if p])
