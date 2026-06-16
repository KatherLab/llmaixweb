# backend/src/services/mistral_ocr_service.py
"""Mistral OCR service for document text extraction."""

import logging
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
    """Service that sends documents to Mistral OCR API and returns markdown."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.mistral.ai",
        model: str = "mistral-ocr-latest",  # Default fallback, usually overridden by caller
    ):
        if not api_key:
            raise MistralOCRError("Mistral API key is required")
        self.api_key = api_key
        self.server_url = base_url
        self.model = model

    def process(self, file_content: bytes) -> MistralOCRResult:
        """Send file content to Mistral OCR API and return concatenated markdown."""
        # Detect document type from content bytes
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

        with Mistral(api_key=self.api_key, server_url=self.server_url) as mistral:
            # Upload document via files.upload API
            try:
                uploaded_pdf = mistral.files.upload(
                    file={
                        "file_name": f"document.{document_type}",
                        "content": file_content,
                    },
                    purpose="ocr",
                )
            except Exception as e:
                raise MistralOCRError(f"Failed to upload document: {e}")

            # Get signed URL
            try:
                signed_url = mistral.files.get_signed_url(file_id=uploaded_pdf.id)
            except Exception as e:
                raise MistralOCRError(f"Failed to get signed URL: {e}")

            # Process with OCR
            try:
                ocr_response = mistral.ocr.process(
                    model=self.model,
                    document={
                        "type": "document_url",
                        "document_url": signed_url.url,
                    },
                )
            except Exception as e:
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
