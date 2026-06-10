# backend/src/services/llm_vision_ocr_service.py
"""Vision LLM OCR service for document text extraction using chat completions."""

import base64
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

from openai import OpenAI

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
    """Service that converts PDF pages to images and sends to a vision LLM."""

    DEFAULT_PROMPT = (
        "Extract all text from this image and return it as clean markdown. "
        "Preserve the original structure, headings, lists, and formatting as much as possible."
    )

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "gpt-4o",
        prompt: Optional[str] = None,
        max_image_dim: int = 2048,
        max_concurrency: int = 3,
    ):
        if not api_key:
            raise LLMVisionOCRError("Vision LLM API key is required")
        if not base_url:
            raise LLMVisionOCRError("Vision LLM base URL is required")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.prompt = prompt or self.DEFAULT_PROMPT
        self.max_image_dim = max_image_dim
        self.max_concurrency = max_concurrency

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

    def _pdf_to_images(self, file_content: bytes) -> list[bytes]:
        """Render PDF pages as PNG images using PyMuPDF."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise LLMVisionOCRError("PyMuPDF (fitz) is required for PDF processing")

        images: list[bytes] = []
        doc = fitz.open(stream=file_content, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Compute zoom to respect max_image_dim
            rect = page.rect
            max_side = max(rect.width, rect.height)
            zoom = min(self.max_image_dim / max_side, 4.0) if max_side > 0 else 1.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            images.append(img_bytes)
        doc.close()
        return images

    def _process_single_image(self, image_bytes: bytes, page_idx: int) -> str:
        """Send a single image to the vision LLM and return the markdown text."""
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/png;base64,{base64_image}"

        try:
            response = self.client.chat.completions.create(
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
            text = response.choices[0].message.content or ""
            return text
        except Exception as e:
            raise LLMVisionOCRError(
                f"Vision LLM request failed on page {page_idx + 1}: {e}"
            )
