# utils/preprocessing.py

import datetime
import io
import tempfile
from pathlib import Path
from typing import List

import pandas as pd
from openai import OpenAI
from sqlalchemy.orm import Session

from .. import models
from ..core.config import settings
from ..dependencies import get_file, save_file
from ..utils.enums import FileCreator
from .helpers import _make_aware


def find_matching_configuration(
    db: Session, project_id: int, config_dict: dict, exclude_id: int | None = None
) -> models.PreprocessingConfiguration | None:
    """Find a configuration with matching settings."""
    query = db.query(models.PreprocessingConfiguration).filter(
        models.PreprocessingConfiguration.project_id == project_id
    )

    if exclude_id:
        query = query.filter(models.PreprocessingConfiguration.id != exclude_id)

    # Key fields to compare (excluding name and description)
    compare_fields = [
        "pdf_backend",
        "ocr_backend",
        "use_ocr",
        "force_ocr",
        "ocr_model",
    ]

    for field in compare_fields:
        if field in config_dict:
            query = query.filter(
                getattr(models.PreprocessingConfiguration, field) == config_dict[field]
            )

    # Handle OCR languages comparison separately (array field)
    if "ocr_languages" in config_dict:
        # Convert to sorted list for comparison
        target_langs = sorted(config_dict["ocr_languages"] or [])
        configs = query.all()

        for config in configs:
            config_langs = sorted(config.ocr_languages or [])
            if config_langs == target_langs:
                # Also check table_settings and additional_settings
                if (config.table_settings or {}) == (
                    config_dict.get("table_settings") or {}
                ):
                    if (config.additional_settings or {}) == (
                        config_dict.get("additional_settings") or {}
                    ):
                        return config
    else:
        return query.first()

    return None


class PreprocessingPipeline:
    """Flexible preprocessing pipeline for different file types."""

    MAX_ROWS_PER_FILE = 10000  # Fail-safe limit
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
                print("set to all failed")
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

    def _process_with_llmaix(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document]:
        """Process files using the new llmaix DocumentPreprocessor."""
        from llmaix import DocumentPreprocessor

        file_content = get_file(file.file_uuid)
        additional_settings = self.config.additional_settings or {}

        # Extract all settings
        mode = additional_settings.get("mode", "fast")
        ocr_engine = additional_settings.get("ocr_engine", "ocrmypdf")
        docling_ocr_engine = additional_settings.get("docling_ocr_engine", "rapidocr")
        enable_picture_description = additional_settings.get(
            "enable_picture_description", False
        )
        enable_formula = additional_settings.get("enable_formula", False)
        enable_code = additional_settings.get("enable_code", False)
        max_image_dim = additional_settings.get("max_image_dim", 800)
        use_vlm = additional_settings.get("use_vlm", False)
        use_local_vlm = additional_settings.get("use_local_vlm", False)
        local_vlm_repo_id = additional_settings.get("local_vlm_repo_id")
        vlm_model = additional_settings.get("vlm_model")
        vlm_prompt = additional_settings.get("vlm_prompt")
        vlm_base_url = additional_settings.get("vlm_base_url")

        # Build DocumentPreprocessor parameters
        preprocessor_params = {
            "mode": mode,
            "ocr_engine": ocr_engine,
            "enable_picture_description": enable_picture_description,
            "enable_formula": enable_formula,
            "enable_code": enable_code,
            "force_ocr": self.config.force_ocr,
            "languages": self.config.ocr_languages,
            "max_image_dim": max_image_dim,
        }

        # Add docling_ocr_engine when available in llmaix
        if docling_ocr_engine and mode == "advanced":
            # Map to the parameter name used in extract_docling
            preprocessor_params["ocr_engine"] = docling_ocr_engine

        # Handle VLM settings
        if use_vlm:
            if use_local_vlm and local_vlm_repo_id:
                preprocessor_params["use_local_vlm"] = True
                preprocessor_params["local_vlm_repo_id"] = local_vlm_repo_id
            else:
                # Create client for remote VLM
                api_key = None
                base_url = vlm_base_url

                # Get API key from task metadata or client
                if hasattr(self, "task") and self.task.task_metadata:
                    api_key = self.task.task_metadata.get("api_key")
                    if not base_url:
                        base_url = self.task.task_metadata.get("api_base_url")

                if not api_key and hasattr(self, "client") and self.client:
                    api_key = self.client.api_key
                    if not base_url:
                        base_url = self.client.base_url

                if api_key and base_url:

                    class VLMClient:
                        def __init__(self, base_url, api_key):
                            self.base_url = base_url
                            self.api_key = api_key

                    vlm_client = VLMClient(base_url, api_key)
                    preprocessor_params["llm_client"] = vlm_client
                    preprocessor_params["llm_model"] = (
                        vlm_model or self.config.llm_model
                    )

        if vlm_prompt:
            preprocessor_params["vlm_prompt"] = vlm_prompt

        # Create preprocessor
        preprocessor = DocumentPreprocessor(**preprocessor_params)

        # Process file
        result = preprocessor.process(file_content)

        # Create document
        doc = models.Document(
            project_id=self.task.project_id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            text=result,
            document_name=file.file_name,
            preprocessing_config_id=self.config.id,
            meta_data={
                "file_type": file.file_type,
                "preprocessing_mode": mode,
                "ocr_engine": ocr_engine if mode == "fast" else docling_ocr_engine,
                "vlm_used": use_vlm,
                "advanced_features": {
                    "picture_description": enable_picture_description,
                    "formula_extraction": enable_formula,
                    "code_extraction": enable_code,
                }
                if mode == "advanced"
                else None,
            },
        )

        self.db.add(doc)
        return [doc]

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
                # For CSV/Excel, check if it needs preprocessing
                if (
                    file.preprocessing_strategy
                    == models.PreprocessingStrategy.ROW_BY_ROW
                ):
                    documents = self._process_table_file(file, file_task)
                else:
                    # Full document CSV - use simple extraction
                    documents = self._process_table_file(file, file_task)
            elif file.file_type in [models.FileType.TEXT_PLAIN]:
                # Plain text files - no need for llmaix
                documents = self._process_text_file(file, file_task)
            else:
                # All other file types go through llmaix
                documents = self._process_with_llmaix(file, file_task)

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
            file_task.error_message = str(e)
            file_task.completed_at = datetime.datetime.now(datetime.UTC)

        self.db.commit()

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

    def _get_config_snapshot(self) -> dict:
        """Get configuration snapshot for duplicate detection."""
        return {
            "file_type": self.config.file_type,
            "preprocessing_strategy": self.config.preprocessing_strategy,
            "pdf_backend": self.config.pdf_backend,
            "ocr_backend": self.config.ocr_backend,
            "use_ocr": self.config.use_ocr,
            "force_ocr": self.config.force_ocr,
            "ocr_languages": self.config.ocr_languages,
            "ocr_model": self.config.ocr_model,
            "table_settings": self.config.table_settings,
            "llm_model": self.config.llm_model,
        }


def process_files_with_config(task_id: int, db: Session):
    """Entry point for processing files with configuration."""
    pipeline = PreprocessingPipeline(db, task_id)
    pipeline.process()
