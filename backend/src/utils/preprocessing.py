# backend/src/utils/preprocessing.py

import datetime
import io
import logging
from typing import List

import pandas as pd
from openai import OpenAI
from sqlalchemy.orm import Session

from .. import models
from ..core.config import settings
from ..dependencies import get_file
from .helpers import _make_aware

logger = logging.getLogger(__name__)


class PreprocessingPipeline:
    """Flexible preprocessing pipeline for different file types."""

    MAX_ROWS_PER_FILE = 100000  # Fail-safe limit
    BATCH_SIZE = 1000  # Process documents in batches

    def __init__(
        self,
        db: Session,
        task_id: int,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.db = db
        self.task = db.get(models.PreprocessingTask, task_id)
        self.config = self.task.configuration
        self.cancelled = False
        self.client = None
        self._docling_serve_client = None

        # Store API credentials in task metadata if custom ones provided
        if api_key and base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            # Store in task metadata for audit
            if not self.task.task_metadata:
                self.task.task_metadata = {}
            self.task.task_metadata["custom_api_used"] = True
            self.task.task_metadata["api_base_url"] = base_url
            self.db.commit()
        elif settings.OPENAI_API_KEY and settings.OPENAI_API_BASE:
            self.client = OpenAI(
                api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_API_BASE
            )

    def check_cancelled(self):
        """Check if task has been cancelled."""
        self.db.refresh(self.task)
        if self.task.is_cancelled:
            self.cancelled = True
            return True
        return False

    def process(self):
        """Main processing method."""

        # ───── mark task as running ──────────────────────────────────────────
        self.task.status = models.PreprocessingStatus.IN_PROGRESS
        self.task.started_at = datetime.datetime.now(datetime.UTC)
        self.db.commit()

        try:
            # ───── process every file task ──────────────────────────────────
            for file_task in self.task.file_tasks:
                if self.check_cancelled():
                    break

                # skip tasks that were already completed/failed in a re‑run
                if file_task.status != models.PreprocessingStatus.PENDING:
                    continue

                self._process_file_task(file_task)

                # update overall counters for the UI
                self.task.processed_files = sum(
                    1
                    for ft in self.task.file_tasks
                    if ft.status == models.PreprocessingStatus.COMPLETED
                )
                self.task.failed_files = sum(
                    1
                    for ft in self.task.file_tasks
                    if ft.status == models.PreprocessingStatus.FAILED
                )
                self.db.commit()

            # ───── after the loop: fail anything still unfinished ───────────
            unfinished = 0
            for ft in self.task.file_tasks:
                if ft.status in (
                    models.PreprocessingStatus.PENDING,
                    models.PreprocessingStatus.IN_PROGRESS,
                ):
                    unfinished += 1
                    ft.status = models.PreprocessingStatus.FAILED
                    ft.error_message = (
                        "Processing did not complete (worker shut down or crashed)."
                    )

            # refresh counters after auto‑failing those tasks
            self.db.commit()
            total = len(self.task.file_tasks)
            completed = sum(
                1
                for ft in self.task.file_tasks
                if ft.status == models.PreprocessingStatus.COMPLETED
            )
            failed = total - completed  # everything else is FAILED now

            # ───── final status / message ───────────────────────────────────
            if self.cancelled:
                # leave status/message set by the cancel workflow
                pass
            elif completed == total:
                self.task.status = models.PreprocessingStatus.COMPLETED
                self.task.message = "Processing completed successfully."
            elif failed == total:
                self.task.status = models.PreprocessingStatus.FAILED
                self.task.message = "All files failed to preprocess."
                logger.warning(
                    "All files failed to preprocess for task %s", self.task.id
                )
            else:
                self.task.status = models.PreprocessingStatus.FAILED
                self.task.message = (
                    f"{completed} of {total} files processed successfully, "
                    f"{failed} failed."
                )

            self.task.completed_at = datetime.datetime.now(datetime.UTC)

        except Exception as e:
            # any unhandled exception ⇒ whole preprocessing task failed
            self.task.status = models.PreprocessingStatus.FAILED
            self.task.message = f"Processing failed: {str(e)}"

        # ───── persist final state ──────────────────────────────────────────
        self.db.commit()

    def _validate_csv_metadata(self, file: models.File) -> None:
        """Validate CSV/XLSX file metadata before processing."""
        strategy = file.preprocessing_strategy
        if not strategy:
            raise ValueError(f"No preprocessing strategy set for file {file.file_name}")

        if strategy == models.PreprocessingStrategy.ROW_BY_ROW:
            if not file.file_metadata:
                raise ValueError(
                    f"No file_metadata found for row-by-row processing of {file.file_name}"
                )

            text_columns = file.file_metadata.get("text_columns", [])
            if not text_columns:
                raise ValueError(
                    f"No text_columns specified in file_metadata for {file.file_name}"
                )

    def _get_docling_serve_client(self):
        """Lazily initialise and return the docling-serve HTTP client."""
        if self._docling_serve_client is None:
            from ..services.docling_serve_client import DoclingServeClient

            additional = self.config.additional_settings or {}

            base_url = settings.DOCLING_SERVE_URL
            timeout = settings.DOCLING_SERVE_TIMEOUT_SECONDS
            max_retries = settings.DOCLING_SERVE_MAX_RETRIES

            # OCR languages from settings or additional_settings
            ocr_langs = additional.get("docling_ocr_languages")
            if ocr_langs is None:
                ocr_langs = list(settings.DOCLING_DEFAULT_OCR_LANGS)
            elif isinstance(ocr_langs, str):
                if ocr_langs.lower() == "auto":
                    ocr_langs = ["deu", "eng"]  # fallback from "auto"
                else:
                    ocr_langs = [ocr_langs]

            self._docling_serve_client = DoclingServeClient(
                base_url=base_url,
                timeout_seconds=timeout,
                max_retries=max_retries,
                default_ocr_langs=ocr_langs,
            )

        return self._docling_serve_client

    def _has_useful_extracted_text(self, text: str, min_chars: int = 100) -> bool:
        """Return True if extracted Markdown contains enough real text.

        Strips common Markdown/table syntax to avoid accepting page
        artifacts or formatting noise as useful content.
        """
        import re

        if not text:
            return False

        # Remove common Markdown/table syntax and collapse whitespace.
        cleaned = re.sub(r"[#*_`>\-|:\[\](){}]+", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return len(cleaned) >= min_chars

    def _check_duplicate_case_ids(self, file: models.File, df: pd.DataFrame) -> None:
        """Check for duplicate case IDs before processing."""
        if file.preprocessing_strategy != models.PreprocessingStrategy.ROW_BY_ROW:
            return

        case_id_column = file.file_metadata.get("case_id_column")
        if not case_id_column:
            return

        if case_id_column not in df.columns:
            raise ValueError(
                f"Case ID column '{case_id_column}' not found in file {file.file_name}"
            )

        # Check for duplicates in the case_id column
        duplicates = df[case_id_column].duplicated()
        if duplicates.any():
            duplicate_values = df[case_id_column][duplicates].unique()
            raise ValueError(
                f"Duplicate case IDs found in column '{case_id_column}': {duplicate_values[:10]}... "
                f"File: {file.file_name}"
            )

    def _process_file_task(self, file_task: models.FilePreprocessingTask):
        """Process a single file task."""
        file_task.status = models.PreprocessingStatus.IN_PROGRESS
        file_task.started_at = datetime.datetime.now(datetime.UTC)
        file_task.file_name = file_task.file.file_name
        self.db.commit()

        try:
            file = file_task.file

            # Route to appropriate processor based on file type
            if file.file_type in [
                models.FileType.TEXT_CSV,
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ]:
                documents = self._process_table_file(file, file_task)
            elif file.file_type in [models.FileType.TEXT_PLAIN]:
                documents = self._process_text_file(file, file_task)
            else:
                # PDF/Image files — route by OCR engine
                documents = self._route_pdf_image(file, file_task)

            file_task.document_count = len(documents)
            file_task.status = models.PreprocessingStatus.COMPLETED
            file_task.completed_at = datetime.datetime.now(datetime.UTC)

            # Calculate processing time
            if file_task.started_at:
                processing_time = (
                    _make_aware(datetime.datetime.now())
                    - _make_aware(file_task.started_at)
                ).total_seconds()
                file_task.processing_time = round(processing_time, 2)

        except Exception as e:
            file_task.status = models.PreprocessingStatus.FAILED
            logger.error(
                "Error processing file %s: %s",
                file_task.file.file_name,
                e,
                exc_info=True,
            )
            file_task.error_message = str(e)
            file_task.completed_at = datetime.datetime.now(datetime.UTC)

        self.db.commit()

    def _route_pdf_image(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document]:
        """Route PDF/image file through docling-serve with extraction mode routing.

        Extraction modes:
        - auto:
            PDF with embedded text: docling-serve, do_ocr=false
            PDF without embedded text: docling-serve, do_ocr=true (Tesseract)
            Image: docling-serve, do_ocr=true (Tesseract)
        - fast_local_ocr:
            All files: docling-serve with Tesseract OCR
        - high_accuracy_remote:
            PDF with embedded text: docling-serve, do_ocr=false
            PDF/image needing OCR: Mistral OCR or Vision LLM (if enabled)
        - force_ocr:
            All files: docling-serve with Tesseract force OCR

        Backwards compatibility:
        - ocr_engine="ocrmypdf" or "tesseract" -> treated as extraction_mode="auto"
        """
        additional = self.config.additional_settings or {}

        # Support both new extraction_mode and legacy ocr_engine settings
        extraction_mode = additional.get("extraction_mode", "auto")
        force_ocr = additional.get("force_ocr", False)
        remote_fallback = additional.get("remote_ocr_fallback", False)

        # Backwards compatibility: map legacy ocr_engine values to extraction_mode
        ocr_engine = additional.get("ocr_engine", None)
        if ocr_engine and extraction_mode == "auto":
            if ocr_engine in {"ocrmypdf", "docling_tesseract", "tesseract"}:
                extraction_mode = "auto"  # Use local Tesseract via docling-serve
            elif ocr_engine == "mistral_ocr":
                extraction_mode = "high_accuracy_remote"
                remote_fallback = True
            elif ocr_engine == "llm_vision":
                extraction_mode = "high_accuracy_remote"
                remote_fallback = True

        is_pdf = file.file_type == models.FileType.APPLICATION_PDF
        is_image = file.file_type in [
            models.FileType.IMAGE_PNG,
            models.FileType.IMAGE_JPEG,
            "image/png",
            "image/jpeg",
            "image/jpg",
        ]

        if is_pdf:
            return self._process_pdf(
                file,
                file_task,
                extraction_mode,
                force_ocr,
                remote_fallback,
                ocr_engine,
            )

        if is_image:
            return self._process_image(
                file,
                file_task,
                extraction_mode,
                force_ocr,
                remote_fallback,
                ocr_engine,
            )

        raise ValueError(f"Unsupported file type for OCR/extraction: {file.file_type}")

    def _process_pdf(
        self,
        file: models.File,
        file_task: models.FilePreprocessingTask,
        extraction_mode: str,
        force_ocr: bool,
        remote_fallback: bool,
        ocr_engine: str | None = None,
    ) -> List[models.Document]:
        """Process a PDF file through docling-serve with extraction mode routing.

        Args:
            file: The file model.
            file_task: The file preprocessing task.
            extraction_mode: One of "auto", "fast_local_ocr", "high_accuracy_remote", "force_ocr".
            force_ocr: If True, skip embedded text check and force OCR.
            remote_fallback: If True, use Mistral/Vision for high_accuracy_remote mode.
            ocr_engine: Original OCR engine setting (mistral_ocr, llm_vision, etc.).

        Returns:
            List of created Document objects.
        """
        # Get quality thresholds from settings
        min_chars_pdf = settings.DOCLING_MIN_EXTRACTED_CHARS_PDF

        # Force OCR mode - always use Tesseract with force_ocr=True
        if extraction_mode == "force_ocr" or force_ocr:
            return self._process_with_docling_serve_tesseract(
                file,
                file_task,
                force_full_page_ocr=True,
            )

        # Fast local OCR - always use Tesseract
        if extraction_mode == "fast_local_ocr":
            return self._process_with_docling_serve_tesseract(
                file,
                file_task,
                force_full_page_ocr=False,
            )

        # Auto mode - check for embedded text first
        if extraction_mode == "auto":
            file_content = get_file(file.file_uuid)

            # Use local pypdf probe (no Docling import needed)
            from ..services.pdf_text_probe import has_embedded_text

            has_text = has_embedded_text(
                file_content,
                min_chars=min_chars_pdf,
                max_pages_to_check=8,
            )

            if has_text and not force_ocr:
                # Use docling-serve without OCR
                return self._process_with_docling_serve_no_ocr(file, file_task)
            else:
                # Use docling-serve with Tesseract OCR
                return self._process_with_docling_serve_tesseract(
                    file,
                    file_task,
                    force_full_page_ocr=False,
                )

        # High accuracy remote mode - use remote OCR only if enabled and needed
        if extraction_mode == "high_accuracy_remote":
            if not remote_fallback:
                # Remote fallback disabled - use local Tesseract
                return self._process_with_docling_serve_tesseract(
                    file,
                    file_task,
                    force_full_page_ocr=False,
                )

            # Check if we can avoid remote OCR (embedded text exists)
            if not force_ocr:
                file_content = get_file(file.file_uuid)
                from ..services.pdf_text_probe import has_embedded_text

                has_text = has_embedded_text(
                    file_content,
                    min_chars=min_chars_pdf,
                    max_pages_to_check=8,
                )

                if has_text:
                    # Use local docling-serve without OCR
                    return self._process_with_docling_serve_no_ocr(file, file_task)

            # Use remote OCR - respect the original ocr_engine setting
            if ocr_engine == "mistral_ocr" and settings.MISTRAL_OCR_ENABLED:
                return self._process_with_mistral_ocr(file, file_task)
            elif ocr_engine == "llm_vision" and settings.VISION_OCR_ENABLED:
                return self._process_with_llm_vision_ocr(file, file_task)
            elif settings.MISTRAL_OCR_ENABLED:
                # Fallback to Mistral if no specific engine requested
                return self._process_with_mistral_ocr(file, file_task)
            elif settings.VISION_OCR_ENABLED:
                # Fallback to Vision if no specific engine requested
                return self._process_with_llm_vision_ocr(file, file_task)
            else:
                # Remote fallback requested but not configured - fail clearly
                raise ValueError(
                    "High accuracy remote OCR requested but neither Mistral OCR nor Vision LLM is enabled. "
                    "Set MISTRAL_OCR_ENABLED=true or VISION_OCR_ENABLED=true, or use a different extraction mode."
                )

        # Unknown extraction mode - fail clearly
        raise ValueError(f"Unknown extraction_mode: {extraction_mode}")

    def _process_image(
        self,
        file: models.File,
        file_task: models.FilePreprocessingTask,
        extraction_mode: str,
        force_ocr: bool,
        remote_fallback: bool,
        ocr_engine: str | None = None,
    ) -> List[models.Document]:
        """Process an image file through docling-serve with extraction mode routing.

        Images always need OCR, so the main difference is whether to use
        local Tesseract or remote Mistral/Vision.

        Args:
            file: The file model.
            file_task: The file preprocessing task.
            extraction_mode: One of "auto", "fast_local_ocr", "high_accuracy_remote", "force_ocr".
            force_ocr: If True, force full-page OCR (always True for images).
            remote_fallback: If True, use Mistral/Vision for high_accuracy_remote mode.
            ocr_engine: Original OCR engine setting (mistral_ocr, llm_vision, etc.).

        Returns:
            List of created Document objects.
        """
        # High accuracy remote mode - use remote OCR if enabled
        if extraction_mode == "high_accuracy_remote" and remote_fallback:
            # Respect the original ocr_engine setting
            if ocr_engine == "mistral_ocr" and settings.MISTRAL_OCR_ENABLED:
                return self._process_with_mistral_ocr(file, file_task)
            elif ocr_engine == "llm_vision" and settings.VISION_OCR_ENABLED:
                return self._process_with_llm_vision_ocr(file, file_task)
            elif settings.MISTRAL_OCR_ENABLED:
                # Fallback to Mistral if no specific engine requested
                return self._process_with_mistral_ocr(file, file_task)
            elif settings.VISION_OCR_ENABLED:
                # Fallback to Vision if no specific engine requested
                return self._process_with_llm_vision_ocr(file, file_task)
            else:
                # Remote fallback requested but not configured - use local
                pass

        # All other modes (auto, fast_local_ocr, force_ocr) or fallback:
        # Use docling-serve with Tesseract OCR
        return self._process_image_with_docling_serve_tesseract(file, file_task)

    def _process_image_with_docling_serve_tesseract(
        self,
        file: models.File,
        file_task: models.FilePreprocessingTask,
    ) -> List[models.Document]:
        """Process an image using docling-serve with Tesseract OCR.

        Images are always processed with force OCR since they don't have
        embedded text.

        Args:
            file: The file model.
            file_task: The file preprocessing task.

        Returns:
            List of created Document objects.

        Raises:
            ValueError: If extraction fails or produces insufficient text.
        """
        from ..services.docling_serve_client import DoclingServeError

        file_content = get_file(file.file_uuid)

        # Determine MIME type from file type
        mime_type_map = {
            models.FileType.IMAGE_PNG: "image/png",
            models.FileType.IMAGE_JPEG: "image/jpeg",
            "image/png": "image/png",
            "image/jpeg": "image/jpeg",
            "image/jpg": "image/jpeg",
        }
        mime_type = mime_type_map.get(file.file_type, "image/png")

        client = self._get_docling_serve_client()

        try:
            result = client.convert_image_tesseract(
                file_content=file_content,
                filename=file.file_name,
                mime_type=mime_type,
            )
        except DoclingServeError as e:
            raise ValueError(f"docling-serve image OCR failed: {e}")

        min_chars = settings.DOCLING_MIN_EXTRACTED_CHARS_IMAGE

        if not self._has_useful_extracted_text(result.text, min_chars=min_chars):
            raise ValueError(
                f"docling-serve Tesseract produced insufficient text for image {file.file_name} "
                f"({len(result.text)} chars)"
            )

        doc = self._build_pdf_document(
            file=file,
            file_task=file_task,
            text=result.text,
            ocr_engine="tesseract",
            extraction_method="docling_serve_tesseract_image_ocr",
            ocr_applied=True,
            extra_metadata={
                "force_ocr": True,
                "engine_used": "docling_serve",
                "file_type": file.file_type,
            },
        )

        self.db.add(doc)
        return [doc]

    def _process_with_docling_serve_tesseract(
        self,
        file: models.File,
        file_task: models.FilePreprocessingTask,
        *,
        force_full_page_ocr: bool = False,
    ) -> List[models.Document]:
        """Process a PDF using docling-serve with Tesseract OCR.

        If force_full_page_ocr is False, docling-serve may use native text where possible
        and OCR where needed.

        If force_full_page_ocr is True, docling-serve forces full-page OCR.

        Args:
            file: The file model.
            file_task: The file preprocessing task.
            force_full_page_ocr: If True, force full-page OCR.

        Returns:
            List of created Document objects.

        Raises:
            ValueError: If extraction fails or produces insufficient text.
        """
        from ..services.docling_serve_client import DoclingServeError

        file_content = get_file(file.file_uuid)
        client = self._get_docling_serve_client()

        try:
            result = client.convert_pdf_tesseract(
                file_content=file_content,
                filename=file.file_name,
                force_ocr=force_full_page_ocr,
            )
        except DoclingServeError as e:
            raise ValueError(f"docling-serve Tesseract extraction failed: {e}")

        min_chars = settings.DOCLING_MIN_EXTRACTED_CHARS_PDF

        if not self._has_useful_extracted_text(result.text, min_chars=min_chars):
            raise ValueError(
                f"docling-serve Tesseract produced insufficient text for {file.file_name} "
                f"({len(result.text)} chars)"
            )

        doc = self._build_pdf_document(
            file=file,
            file_task=file_task,
            text=result.text,
            ocr_engine="tesseract",
            extraction_method=(
                "docling_serve_tesseract_force_ocr"
                if force_full_page_ocr
                else "docling_serve_tesseract_ocr"
            ),
            ocr_applied=True,
            extra_metadata={
                "force_ocr": force_full_page_ocr,
                "engine_used": "docling_serve",
            },
        )

        self.db.add(doc)
        return [doc]

    def _process_with_docling_serve_no_ocr(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document]:
        """Process PDF using docling-serve without OCR (embedded text only).

        Args:
            file: The file model.
            file_task: The file preprocessing task.

        Returns:
            List of created Document objects.

        Raises:
            ValueError: If extraction fails or produces insufficient text.
        """
        from ..services.docling_serve_client import DoclingServeError

        file_content = get_file(file.file_uuid)
        client = self._get_docling_serve_client()

        try:
            result = client.convert_pdf_no_ocr(
                file_content=file_content,
                filename=file.file_name,
            )
        except DoclingServeError as e:
            raise ValueError(f"docling-serve extraction failed: {e}")

        min_chars = settings.DOCLING_MIN_EXTRACTED_CHARS_PDF

        if not self._has_useful_extracted_text(result.text, min_chars=min_chars):
            raise ValueError(
                f"docling-serve produced insufficient text for {file.file_name} "
                f"({len(result.text)} chars)"
            )

        doc = self._build_pdf_document(
            file=file,
            file_task=file_task,
            text=result.text,
            ocr_engine="docling_serve",
            extraction_method="docling_serve_no_ocr",
            ocr_applied=False,
            extra_metadata={
                "embedded_text_detected": True,
                "force_ocr": False,
                "engine_used": "docling_serve",
            },
        )

        self.db.add(doc)
        return [doc]

    def _build_pdf_document(
        self,
        *,
        file: models.File,
        file_task: models.FilePreprocessingTask,
        text: str,
        ocr_engine: str,
        extraction_method: str,
        ocr_applied: bool,
        extra_metadata: dict | None = None,
    ) -> models.Document:
        """Build a PDF-derived Document with consistent metadata."""
        metadata = {
            "file_type": file.file_type,
            "ocr_engine": ocr_engine,
            "extraction_method": extraction_method,
            "ocr_applied": ocr_applied,
        }

        if extra_metadata:
            metadata.update(extra_metadata)

        return models.Document(
            project_id=self.task.project_id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            text=text,
            document_name=file.file_name,
            preprocessing_config_id=self.config.id,
            meta_data=metadata,
        )

    def _process_with_mistral_ocr(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document]:
        """Process file using Mistral OCR API."""
        from ..services.mistral_ocr_service import MistralOCRService

        additional = self.config.additional_settings or {}

        # Get API key: from task metadata (user-set) or fallback to app config
        api_key = None
        if self.task.task_metadata:
            api_key = self.task.task_metadata.get("mistral_api_key")
        if not api_key:
            api_key = additional.get("mistral_api_key")
        if not api_key:
            api_key = settings.MISTRAL_API_KEY
        if not api_key:
            raise ValueError(
                "Mistral API key is not configured. "
                "Set it in Additional Settings (mistral_api_key) or in the server config (MISTRAL_API_KEY)."
            )

        model = additional.get("mistral_model", "mistral-ocr-latest")
        base_url = settings.MISTRAL_API_BASE

        service = MistralOCRService(api_key=api_key, base_url=base_url, model=model)
        file_content = get_file(file.file_uuid)
        result = service.process(file_content)

        doc = models.Document(
            project_id=self.task.project_id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            text=result.text,
            document_name=file.file_name,
            preprocessing_config_id=self.config.id,
            meta_data={
                "file_type": file.file_type,
                "ocr_engine": "mistral_ocr",
                "model": model,
            },
        )
        self.db.add(doc)
        return [doc]

    def _process_with_llm_vision_ocr(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document]:
        """Process file using a Vision LLM API."""
        from ..services.llm_vision_ocr_service import LLMVisionOCRService

        additional = self.config.additional_settings or {}

        # Get API credentials — user per-task settings take priority,
        # then fall back to server-level VISION_OCR_* config
        api_key = additional.get("vision_api_key") or settings.VISION_OCR_API_KEY or ""
        base_url = (
            additional.get("vision_base_url") or settings.VISION_OCR_API_BASE or ""
        )

        # Fallback to self.client (the pipeline-level main OpenAI client)
        if not api_key and self.client:
            api_key = self.client.api_key or ""
        if not base_url and self.client:
            base_url = str(self.client.base_url)

        if not api_key or not base_url:
            raise ValueError(
                "Vision LLM API key and base URL are required for llm_vision engine. "
                "Set them in Additional Settings (vision_api_key, vision_base_url) "
                "or configure VISION_OCR_API_KEY / VISION_OCR_API_BASE in server settings."
            )

        model = additional.get("vision_model") or settings.VISION_OCR_MODEL or "gpt-4o"
        prompt = additional.get("vision_prompt") or settings.VISION_OCR_PROMPT
        max_image_dim = additional.get("vision_max_image_dim", 2048)

        service = LLMVisionOCRService(
            api_key=api_key,
            base_url=base_url,
            model=model,
            prompt=prompt,
            max_image_dim=max_image_dim,
        )

        file_content = get_file(file.file_uuid)
        is_pdf = file.file_type == models.FileType.APPLICATION_PDF
        result = service.process(file_content, is_pdf=is_pdf)

        # Surface partial failures as warnings on the file task
        if result.failed_pages > 0:
            file_task.warnings = {
                "messages": result.errors,
                "failed_pages": result.failed_pages,
                "total_pages": result.total_pages,
            }

        doc = models.Document(
            project_id=self.task.project_id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            text=result.text,
            document_name=file.file_name,
            preprocessing_config_id=self.config.id,
            meta_data={
                "file_type": file.file_type,
                "ocr_engine": "llm_vision",
                "model": model,
            },
        )
        self.db.add(doc)
        return [doc]

    def _process_table_file(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document]:
        """Process CSV/Excel files using file metadata."""
        documents = []
        file_content = get_file(file.file_uuid)

        # Validate metadata
        self._validate_csv_metadata(file)

        # Get preprocessing strategy from file
        strategy = file.preprocessing_strategy

        # For FULL_DOCUMENT strategy
        if strategy == models.PreprocessingStrategy.FULL_DOCUMENT:
            # Read entire file as one document
            if file.file_type == models.FileType.TEXT_CSV:
                df = pd.read_csv(io.BytesIO(file_content))
            else:
                df = pd.read_excel(io.BytesIO(file_content))

            # Check row limit
            if len(df) > self.MAX_ROWS_PER_FILE:
                raise ValueError(
                    f"File {file.file_name} has {len(df)} rows, exceeding the maximum limit of {self.MAX_ROWS_PER_FILE}"
                )

            # Convert entire dataframe to text
            text = df.to_string()

            doc = models.Document(
                project_id=self.task.project_id,
                original_file_id=file.id,
                file_preprocessing_task_id=file_task.id,
                text=text,
                document_name=file.file_name,
                preprocessing_config_id=self.config.id,
                meta_data={
                    "file_type": "table",
                    "preprocessing_strategy": "full_document",
                    "total_rows": len(df),
                    "columns": list(df.columns),
                },
            )
            self.db.add(doc)
            documents.append(doc)

        elif strategy == models.PreprocessingStrategy.ROW_BY_ROW:
            # Get settings from file_metadata
            file_metadata = file.file_metadata

            # Extract settings
            delimiter = file_metadata.get("delimiter", ",")
            encoding = file_metadata.get("encoding", "utf-8")
            has_header = file_metadata.get("has_header", True)
            text_columns = file_metadata.get("text_columns", [])
            case_id_column = file_metadata.get("case_id_column")

            # Read file based on type
            try:
                if file.file_type == models.FileType.TEXT_CSV:
                    df = pd.read_csv(
                        io.BytesIO(file_content),
                        encoding=encoding,
                        delimiter=delimiter,
                        header=0 if has_header else None,
                    )
                else:
                    df = pd.read_excel(
                        io.BytesIO(file_content), header=0 if has_header else None
                    )
            except Exception as e:
                raise ValueError(f"Failed to read file {file.file_name}: {str(e)}")

            # Check row limit
            if len(df) > self.MAX_ROWS_PER_FILE:
                raise ValueError(
                    f"File {file.file_name} has {len(df)} rows, exceeding the maximum limit of {self.MAX_ROWS_PER_FILE}"
                )

            # Validate columns exist
            missing_columns = [col for col in text_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(
                    f"Text columns {missing_columns} not found in file {file.file_name}. "
                    f"Available columns: {list(df.columns)}"
                )

            # Check for duplicate case IDs
            self._check_duplicate_case_ids(file, df)

            # Process rows in batches
            batch_documents = []
            total_rows = len(df)

            for idx, row in df.iterrows():
                if self.check_cancelled():
                    break

                # Build document content from specified columns
                content_parts = []
                for col in text_columns:
                    value = row[col]
                    if pd.notna(value):  # Skip NaN values
                        content_parts.append(str(value))

                content = " ".join(content_parts)

                # Skip empty documents
                if not content.strip():
                    continue

                # Build document name using case_id_column if specified
                if case_id_column and case_id_column in row:
                    case_id = row[case_id_column]
                    doc_name = f"{case_id}"
                else:
                    doc_name = f"{file.file_name}_row_{idx}"

                # Create document
                doc = models.Document(
                    project_id=self.task.project_id,
                    original_file_id=file.id,
                    file_preprocessing_task_id=file_task.id,
                    text=content,
                    document_name=doc_name,
                    preprocessing_config_id=self.config.id,
                    meta_data={
                        "row_index": int(idx),  # Convert numpy int to Python int
                        "source_columns": text_columns,
                        "case_id": str(row[case_id_column])
                        if case_id_column and case_id_column in row
                        else None,
                        "file_type": "table",
                        "preprocessing_strategy": "row_by_row",
                        "all_row_data": row.to_dict(),  # Store full row for reference
                    },
                )

                batch_documents.append(doc)

                # Commit in batches for performance
                if len(batch_documents) >= self.BATCH_SIZE:
                    self.db.bulk_save_objects(batch_documents)
                    self.db.commit()
                    documents.extend(batch_documents)
                    batch_documents = []

                    # Update progress
                    file_task.progress = (idx + 1) / total_rows * 100
                    self.db.commit()

            # Save remaining documents
            if batch_documents:
                self.db.bulk_save_objects(batch_documents)
                self.db.commit()
                documents.extend(batch_documents)

        else:
            raise ValueError(f"Unsupported preprocessing strategy: {strategy}")

        return documents

    def _process_text_file(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document]:
        """Process plain text files."""
        file_content = get_file(file.file_uuid)

        # Decode text content
        text = file_content.decode("utf-8", errors="replace")

        # Create document
        doc = models.Document(
            project_id=self.task.project_id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            text=text,
            document_name=file.file_name,
            preprocessing_config_id=self.config.id,
            meta_data={"file_type": "text"},
        )

        self.db.add(doc)
        return [doc]


def process_files_with_config(task_id: int, db: Session):
    """Entry point for processing files with configuration."""
    pipeline = PreprocessingPipeline(db, task_id)
    pipeline.process()
