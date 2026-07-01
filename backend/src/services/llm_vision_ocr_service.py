# backend/src/services/llm_vision_ocr_service.py
"""Vision LLM OCR service for document text extraction using chat completions.

Includes retry logic with exponential backoff for transient errors.
"""

import base64
import io
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

import httpx
from openai import OpenAI

from ..core.config import settings

logger = logging.getLogger(__name__)


class LLMVisionOCRError(Exception):
    """Raised when vision LLM OCR processing fails."""


@dataclass
class LLMVisionOCRResult:
    text: str
    pages: list[str] = field(default_factory=list)
    failed_pages: int = 0
    total_pages: int = 0
    errors: list[str] = field(default_factory=list)


class LLMVisionOCRService:
    """Service that converts PDF pages to images and sends to a vision LLM.

    Includes retry logic with exponential backoff for transient errors.
    """

    DEFAULT_PROMPT = (
        "Extract all text from this image and return it as clean markdown. "
        "Preserve the original structure, headings, lists, and formatting as much as possible."
    )

    # HTTP status codes that should trigger a retry
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "gpt-4o",
        prompt: Optional[str] = None,
        max_image_dim: int = 2048,
        max_concurrency: int = 3,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_backoff: float = 2.0,
    ):
        if not api_key:
            raise LLMVisionOCRError("Vision LLM API key is required")
        if not base_url:
            raise LLMVisionOCRError("Vision LLM base URL is required")
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=settings.LLM_REQUEST_TIMEOUT_SECONDS,
            # follow_redirects=False: a user-controlled endpoint can't 3xx the
            # request to a blocked internal/metadata address (SSRF). The base_url
            # is validated upstream (validate_user_endpoint), but that check only
            # blocks metadata IPs at validation time — this closes the
            # redirect/DNS-rebinding bypass at request time.
            http_client=httpx.Client(
                follow_redirects=False,
                timeout=settings.LLM_REQUEST_TIMEOUT_SECONDS,
            ),
        )
        self.model = model
        self.prompt = prompt or self.DEFAULT_PROMPT
        self.max_image_dim = max_image_dim
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.base_retry_delay = retry_delay
        self.retry_backoff = retry_backoff

    def close(self) -> None:
        """Close the underlying OpenAI/httpx client.

        The service is instantiated per file in the preprocessing pipeline and
        previously never closed, leaking an httpx connection pool per use. Safe
        to call when the client was already closed.
        """
        client = self.client
        self.client = None
        if client is not None:
            close = getattr(client, "close", None)
            if close is not None:
                try:
                    close()
                except Exception:
                    logger.debug(
                        "Error closing LLMVisionOCRService OpenAI client",
                        exc_info=True,
                    )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def _is_retryable_exception(self, exc: Exception) -> bool:
        """Check if an exception is retryable."""
        # Prefer the structured status code carried by the SDK exception
        # (OpenAI APIStatusError exposes `.status_code`). Matching status codes
        # as substrings of the error message is unsound: a message containing
        # "500" for any reason would match code 500.
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int) and status_code in self.RETRYABLE_STATUS_CODES:
            return True
        exc_str = str(exc).lower()
        # Check for common retryable error patterns
        retryable_patterns = [
            "timeout",
            "connection error",
            "temporary failure",
            "rate limit",
            "service unavailable",
            "gateway",
            "server error",
        ]
        return any(pattern in exc_str for pattern in retryable_patterns)

    def _execute_with_retry(
        self, func, operation_name: str, page_idx: Optional[int] = None
    ):
        """Execute a function with exponential backoff retry logic.

        Args:
            func: Function to execute (should raise exception on failure)
            operation_name: Human-readable name of the operation for logging
            page_idx: Optional page index for logging

        Returns:
            Result of func()

        Raises:
            LLMVisionOCRError: If all retries fail or error is not retryable
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                result = func()
                if attempt > 0:
                    page_info = (
                        f" (page {page_idx + 1})" if page_idx is not None else ""
                    )
                    logger.info(
                        "%s succeeded after %d retry attempts%s",
                        operation_name,
                        attempt,
                        page_info,
                    )
                return result

            except Exception as e:
                last_exception = e
                is_retryable = self._is_retryable_exception(e)

                if not is_retryable:
                    # Non-retryable error, fail immediately
                    page_info = (
                        f" on page {page_idx + 1}" if page_idx is not None else ""
                    )
                    raise LLMVisionOCRError(f"{operation_name}{page_info} failed: {e}")

                if attempt == self.max_retries:
                    # All retries exhausted
                    break

                # Calculate delay with exponential backoff + jitter
                delay = self.base_retry_delay * (self.retry_backoff**attempt)
                jitter = random.uniform(0, delay * 0.1)  # 10% jitter

                page_info = f" (page {page_idx + 1})" if page_idx is not None else ""
                logger.warning(
                    "%s failed%s (attempt %d/%d): %s. Retrying in %.1fs...",
                    operation_name,
                    page_info,
                    attempt + 1,
                    self.max_retries + 1,
                    e,
                    delay + jitter,
                )
                time.sleep(delay + jitter)

        # All retries exhausted
        page_info = f" on page {page_idx + 1}" if page_idx is not None else ""
        raise LLMVisionOCRError(
            f"{operation_name}{page_info} failed after {self.max_retries} retries: {last_exception}"
        )

    def process(self, file_content: bytes, is_pdf: bool = True) -> LLMVisionOCRResult:
        """Process file content with vision LLM.

        Args:
            file_content: Raw file bytes.
            is_pdf: If True, render pages as images via PyMuPDF.
                     If False, treat content as a single image.

        Returns:
            LLMVisionOCRResult with concatenated markdown.
        """
        if is_pdf:
            images = self._pdf_to_images(file_content)
        else:
            images = [file_content]

        if not images:
            raise LLMVisionOCRError("No images generated from document")

        pages = [""] * len(images)
        errors: list[str] = []
        with ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
            future_map = {
                executor.submit(self._process_single_image, img, i): i
                for i, img in enumerate(images)
            }
            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    pages[idx] = future.result()
                except Exception as e:
                    err_msg = str(e)
                    errors.append(err_msg)
                    logger.warning("Vision LLM failed on page %d: %s", idx, err_msg)

        failed_pages = len(errors)
        # If every page failed, raise so the caller marks the task as FAILED
        if failed_pages == len(images):
            raise LLMVisionOCRError(
                f"All {len(images)} page(s) failed during Vision LLM OCR. "
                f"First error: {errors[0]}"
            )

        # Otherwise return only successfully extracted pages
        successful = [p for p in pages if p]
        combined = "\n\n".join(successful)
        return LLMVisionOCRResult(
            text=combined.strip(),
            pages=successful,
            failed_pages=failed_pages,
            total_pages=len(images),
            errors=errors,
        )

    def _apply_exif_rotation(self, image_bytes: bytes) -> bytes:
        """Apply EXIF orientation correction and resize if needed.

        Args:
            image_bytes: Raw image bytes.

        Returns:
            Corrected and resized image bytes (PNG format).
        """
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes))

            # Apply EXIF orientation
            if settings.IMAGE_HANDLE_EXIF_ROTATION:
                try:
                    # ImageOps.exif_transpose handles rotation based on EXIF Orientation tag
                    from PIL import ImageOps

                    img = ImageOps.exif_transpose(img)
                except Exception as e:
                    logger.debug("EXIF transpose failed: %s", e)

            # Resize if exceeds max dimension
            max_dim = settings.IMAGE_MAX_DIMENSION
            width, height = img.size
            if width > max_dim or height > max_dim:
                # Calculate new size maintaining aspect ratio
                scale = max_dim / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(
                    "Resized image from %dx%d to %dx%d",
                    width,
                    height,
                    new_width,
                    new_height,
                )

            # Convert to PNG
            output = io.BytesIO()
            img.save(output, format="PNG")
            return output.getvalue()

        except ImportError:
            logger.warning("PIL not available, skipping EXIF rotation and resizing")
            return image_bytes
        except Exception as e:
            logger.warning("Image processing failed: %s", e)
            return image_bytes

    def _pdf_to_images(self, file_content: bytes) -> list[bytes]:
        """Render PDF pages as PNG images using PyMuPDF.

        Applies EXIF rotation and max dimension resizing if configured.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise LLMVisionOCRError("PyMuPDF (fitz) is required for PDF processing")

        images: list[bytes] = []
        doc = fitz.open(stream=file_content, filetype="pdf")
        try:
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Compute zoom to respect max_image_dim
                rect = page.rect
                max_side = max(rect.width, rect.height)
                zoom = min(self.max_image_dim / max_side, 4.0) if max_side > 0 else 1.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")

                # Apply EXIF rotation and resizing (for PDFs this mainly applies the max dimension)
                img_bytes = self._apply_exif_rotation(img_bytes)

                images.append(img_bytes)
        finally:
            # Always close the document — without this, a corrupt page or a
            # get_pixmap / _apply_exif_rotation failure leaks the fitz.Document
            # (memory + underlying handles) for the lifetime of the process.
            doc.close()
        return images

    def _process_single_image(self, image_bytes: bytes, page_idx: int) -> str:
        """Send a single image to the vision LLM and return the markdown text.

        Includes retry logic for transient errors.
        Applies EXIF rotation and max dimension resizing before processing.
        """
        # Apply EXIF rotation and resize if needed
        processed_image = self._apply_exif_rotation(image_bytes)

        base64_image = base64.b64encode(processed_image).decode("utf-8")
        data_url = f"data:image/png;base64,{base64_image}"

        def make_request():
            assert (
                self.client is not None
            )  # constructed in __init__; closed only after use
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                        ],
                    }
                ],
                max_tokens=4096,
            )

        try:
            response = self._execute_with_retry(
                make_request,
                "Vision LLM request",
                page_idx=page_idx,
            )
            text = response.choices[0].message.content or ""
            return text
        except LLMVisionOCRError as e:
            raise LLMVisionOCRError(
                f"Vision LLM request failed on page {page_idx + 1}: {e}"
            )
