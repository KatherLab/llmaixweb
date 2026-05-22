# utils/preprocessing.py

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
                logger.warning("All files failed to preprocess for task %s", self.task.id)
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
        """Route PDF/image file to the appropriate OCR/text extraction engine.

        For PDFs: internally tries Docling first to extract embedded text.
        If sufficient text is found and force_ocr is not set, the Docling
        result is used directly (skipping OCR). Otherwise routes to the
        user-selected OCR engine.

        For images: routes directly to the user-selected OCR engine.
        """
        additional = self.config.additional_settings or {}
        ocr_engine = additional.get("ocr_engine", "ocrmypdf")
        force_ocr = additional.get("force_ocr", False)

        # For PDFs, try Docling first for embedded text extraction
        if file.file_type == models.FileType.APPLICATION_PDF and not force_ocr:
            docling_result = self._try_docling_extraction(file, file_task)
            if docling_result is not None:
                return docling_result

        # Route to user-selected OCR engine
        if ocr_engine == "ocrmypdf":
            return self._process_with_ocrmypdf(file, file_task)
        elif ocr_engine == "mistral_ocr":
            if not settings.MISTRAL_OCR_ENABLED:
                raise ValueError(
                    "Mistral OCR is disabled by server configuration (MISTRAL_OCR_ENABLED=false)."
                )
            return self._process_with_mistral_ocr(file, file_task)
        elif ocr_engine == "llm_vision":
            if not settings.VISION_OCR_ENABLED:
                raise ValueError(
                    "Vision LLM OCR is disabled by server configuration (VISION_OCR_ENABLED=false)."
                )
            return self._process_with_llm_vision_ocr(file, file_task)
        else:
            raise ValueError(f"Unknown OCR engine: {ocr_engine}")

    def _try_docling_extraction(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document] | None:
        """Try to extract text from a PDF using Docling.

        Returns documents if sufficient text was extracted, None otherwise.
        """
        from ..services.docling_service import DoclingService

        file_content = get_file(file.file_uuid)
        service = DoclingService()
        try:
            md_text = service.process(file_content)
            # Consider text "sufficient" if it has at least 50 non-whitespace characters
            if md_text and len(md_text.strip()) > 50:
                doc = models.Document(
                    project_id=self.task.project_id,
                    original_file_id=file.id,
                    file_preprocessing_task_id=file_task.id,
                    text=md_text,
                    document_name=file.file_name,
                    preprocessing_config_id=self.config.id,
                    meta_data={
                        "file_type": file.file_type,
                        "ocr_engine": "docling",
                        "extraction_method": "embedded_text",
                    },
                )
                self.db.add(doc)
                return [doc]
        except Exception:
            logger.warning(
                "Docling extraction failed for %s, falling back to OCR",
                file.file_name,
                exc_info=True,
            )
        return None

    def _process_with_ocrmypdf(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document]:
        """Process file using ocrmypdf (Tesseract)."""
        file_content = get_file(file.file_uuid)
        additional = self.config.additional_settings or {}

        import tempfile

        import ocrmypdf

        # Write input to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_in:
            tmp_in.write(file_content)
            tmp_in_path = tmp_in.name

        tmp_out_path = tmp_in_path.replace(".pdf", "_ocr.pdf")

        try:
            # Remove alpha channel from images if present (ocrmypdf doesn't support RGBA)
            if file.file_type in (
                models.FileType.IMAGE_PNG,
                models.FileType.IMAGE_JPEG,
                "image/png",
                "image/jpeg",
            ):
                from PIL import Image

                img = Image.open(tmp_in_path)
                if img.mode == "RGBA":
                    img = img.convert("RGB")
                    img.save(tmp_in_path)

            # Run ocrmypdf
            force_ocr = additional.get("force_ocr", False)
            ocrmypdf.ocr(
                tmp_in_path,
                tmp_out_path,
                force_ocr=force_ocr,
                language="eng",
                skip_text=not force_ocr,
                deskew=True,
                clean=False,
                image_dpi=additional.get("image_dpi", 300),
            )

            # Extract text from OCR'd PDF using pypdf
            from pypdf import PdfReader

            reader = PdfReader(tmp_out_path)
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            md_text = "\n\n".join(text_parts)

            doc = models.Document(
                project_id=self.task.project_id,
                original_file_id=file.id,
                file_preprocessing_task_id=file_task.id,
                text=md_text,
                document_name=file.file_name,
                preprocessing_config_id=self.config.id,
                meta_data={
                    "file_type": file.file_type,
                    "ocr_engine": "ocrmypdf",
                    "force_ocr": additional.get("force_ocr", False),
                },
            )
            self.db.add(doc)
            return [doc]

        finally:
            # Clean up temp files
            import os

            for p in (tmp_in_path, tmp_out_path):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def _process_with_docling(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document]:
        """Process file using Docling (text extraction, no OCR)."""
        from ..services.docling_service import DoclingService

        file_content = get_file(file.file_uuid)
        service = DoclingService()
        md_text = service.process(file_content)

        doc = models.Document(
            project_id=self.task.project_id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            text=md_text,
            document_name=file.file_name,
            preprocessing_config_id=self.config.id,
            meta_data={
                "file_type": file.file_type,
                "ocr_engine": "docling",
            },
        )
        self.db.add(doc)
        return [doc]

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
