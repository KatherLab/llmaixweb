# utils/preprocessing.py

import io
import tempfile
import datetime
from pathlib import Path
from typing import List

import pandas as pd
from openai import OpenAI
from sqlalchemy.orm import Session

from .. import models
from ..core.config import settings
from ..dependencies import get_file, save_file
from ..utils.enums import FileCreator


class PreprocessingPipeline:
    """Flexible preprocessing pipeline for different file types."""

    def __init__(self, db: Session, task_id: int):
        self.db = db
        self.task = db.get(models.PreprocessingTask, task_id)
        self.config = self.task.configuration
        self.cancelled = False
        self.client = None

        # Initialize OpenAI client if needed
        additional_settings = self.config.additional_settings or {}
        if additional_settings.get("api_key") and additional_settings.get("base_url"):
            self.client = OpenAI(
                api_key=additional_settings["api_key"],
                base_url=additional_settings["base_url"]
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
        self.task.status = models.PreprocessingStatus.IN_PROGRESS
        self.task.started_at = datetime.datetime.now(datetime.UTC)
        self.db.commit()

        try:
            for file_task in self.task.file_tasks:
                if self.check_cancelled():
                    break

                if file_task.status != models.PreprocessingStatus.PENDING:
                    continue

                self._process_file_task(file_task)

                # Update overall progress
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

            total = len(self.task.file_tasks)
            failed = self.task.failed_files
            completed = self.task.processed_files

            if self.cancelled:
                # Don't overwrite CANCELLED status/message
                pass
            elif completed == total:
                self.task.status = models.PreprocessingStatus.COMPLETED
                self.task.message = "Processing completed successfully"
            elif failed == total:
                self.task.status = models.PreprocessingStatus.FAILED
                self.task.message = "All files failed to preprocess"
            else:
                self.task.status = models.PreprocessingStatus.FAILED
                self.task.message = (
                    f"{completed} of {total} files processed successfully, "
                    f"{failed} failed"
                )
            self.task.completed_at = datetime.datetime.now(datetime.UTC)

        except Exception as e:
            self.task.status = models.PreprocessingStatus.FAILED
            self.task.message = f"Processing failed: {str(e)}"

        self.db.commit()

    def _process_file_task(self, file_task: models.FilePreprocessingTask):
        """Process a single file task."""
        file_task.status = models.PreprocessingStatus.IN_PROGRESS
        file_task.started_at = datetime.datetime.now(datetime.UTC)
        self.db.commit()

        try:
            file = file_task.file

            # Update config file type based on actual file
            if self.config.file_type != file.file_type:
                self.config.file_type = file.file_type

            # Route to appropriate processor
            if file.file_type in [models.FileType.TEXT_CSV, "application/vnd.ms-excel",
                                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
                documents = self._process_table_file(file, file_task)
            elif file.file_type in [models.FileType.APPLICATION_PDF]:
                documents = self._process_pdf_file(file, file_task)
            elif file.file_type in [models.FileType.IMAGE_JPEG, models.FileType.IMAGE_PNG]:
                documents = self._process_image_file(file, file_task)
            else:
                documents = self._process_text_file(file, file_task)

            file_task.document_count = len(documents)
            file_task.status = models.PreprocessingStatus.COMPLETED
            file_task.completed_at = datetime.datetime.now(datetime.UTC)
        except Exception as e:
            file_task.status = models.PreprocessingStatus.FAILED
            file_task.error_message = str(e)

        self.db.commit()

    def _process_table_file(self, file: models.File, file_task: models.FilePreprocessingTask) -> List[models.Document]:
        """Process CSV/Excel files row by row."""
        documents = []
        file_content = get_file(file.file_uuid)

        table_settings = self.config.table_settings or {}
        content_columns = table_settings.get("content_columns", [])
        name_column = table_settings.get("name_column")
        join_separator = table_settings.get("join_separator", " ")
        skip_rows = table_settings.get("skip_header_rows", 0)
        encoding = table_settings.get("encoding", "utf-8")

        # Read file based on type
        if file.file_type == models.FileType.TEXT_CSV:
            df = pd.read_csv(
                io.BytesIO(file_content),
                encoding=encoding,
                skiprows=skip_rows
            )
        else:
            df = pd.read_excel(
                io.BytesIO(file_content),
                skiprows=skip_rows
            )

        # Process each row
        for idx, row in df.iterrows():
            if self.check_cancelled():
                break

            # Build document content
            if content_columns:
                content_parts = [str(row[col]) for col in content_columns if col in row]
                content = join_separator.join(content_parts)
            else:
                # Use all columns if none specified
                content = join_separator.join(str(v) for v in row.values)

            # Build document name
            if name_column and name_column in row:
                doc_name = str(row[name_column])
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
                    "row_index": idx,
                    "source_columns": content_columns or list(df.columns),
                    "file_type": "table"
                }
            )

            self.db.add(doc)
            documents.append(doc)

            # Update progress
            file_task.progress = (idx + 1) / len(df) * 100
            self.db.commit()

        return documents

    def _process_pdf_file(self, file: models.File, file_task: models.FilePreprocessingTask) -> List[models.Document]:
        """Process PDF files with OCR support."""
        from llmaix import preprocess_file as llmaix_preprocess_file

        file_content = get_file(file.file_uuid)
        additional_settings = self.config.additional_settings or {}
        output_file = additional_settings.get("output_file", True)

        # Prepare llmaix parameters
        llmaix_params = {
            "filename": file_content,
            "pdf_backend": self.config.pdf_backend or "pymupdf4llm",
            "ocr_backend": self.config.ocr_backend or "ocrmypdf",
            "use_ocr": self.config.use_ocr,
            "force_ocr": self.config.force_ocr,
            "ocr_languages": self.config.ocr_languages,
            "ocr_model": self.config.ocr_model,
            "llm_model": self.config.llm_model,
        }

        # Add client or API credentials if available
        if self.client:
            llmaix_params["client"] = self.client
        elif additional_settings.get("api_key"):
            llmaix_params["api_key"] = additional_settings["api_key"]
            llmaix_params["base_url"] = additional_settings.get("base_url")

        preprocessed_file_id = None

        if output_file:
            # Process with output file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file_path = Path(tmp_file.name)
                try:
                    llmaix_params["output"] = tmp_file_path
                    result = llmaix_preprocess_file(**llmaix_params)

                    # Save preprocessed file
                    preprocessed_file_content = tmp_file_path.read_bytes()
                    new_file_name = f"preprocessed_{file.id}.pdf"
                    new_file_uuid = save_file(preprocessed_file_content)

                    file_obj = models.File(
                        project_id=self.task.project_id,
                        file_name=new_file_name,
                        file_type=models.FileType.APPLICATION_PDF,
                        file_storage_type=models.FileStorageType.LOCAL
                        if settings.LOCAL_DIRECTORY
                        else models.FileStorageType.S3,
                        file_uuid=new_file_uuid,
                        file_creator=FileCreator.system,
                        description=f"Preprocessed version of {file.file_name}"
                    )
                    self.db.add(file_obj)
                    self.db.commit()
                    self.db.refresh(file_obj)
                    preprocessed_file_id = file_obj.id

                finally:
                    tmp_file_path.unlink()
        else:
            # Process without output file
            result = llmaix_preprocess_file(**llmaix_params)

        # Create document
        doc = models.Document(
            project_id=self.task.project_id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            preprocessed_file_id=preprocessed_file_id,
            text=result,
            document_name=file.file_name,
            preprocessing_config_id=self.config.id,
            meta_data={
                "file_type": "pdf",
                "ocr_used": self.config.use_ocr,
                "ocr_backend": self.config.ocr_backend if self.config.use_ocr else None,
                "pdf_backend": self.config.pdf_backend
            }
        )

        self.db.add(doc)
        return [doc]

    def _process_image_file(self, file: models.File, file_task: models.FilePreprocessingTask) -> List[models.Document]:
        """Process image files with OCR."""
        from llmaix import preprocess_file as llmaix_preprocess_file

        file_content = get_file(file.file_uuid)
        additional_settings = self.config.additional_settings or {}

        # Process with llmaix
        llmaix_params = {
            "filename": file_content,
            "ocr_backend": self.config.ocr_backend or "ocrmypdf",
            "use_ocr": True,  # Always use OCR for images
            "force_ocr": True,
            "ocr_languages": self.config.ocr_languages,
            "ocr_model": self.config.ocr_model,
        }

        # Add client or API credentials if available
        if self.client:
            llmaix_params["client"] = self.client
        elif additional_settings.get("api_key"):
            llmaix_params["api_key"] = additional_settings["api_key"]
            llmaix_params["base_url"] = additional_settings.get("base_url")

        result = llmaix_preprocess_file(**llmaix_params)

        # Create document
        doc = models.Document(
            project_id=self.task.project_id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            text=result,
            document_name=file.file_name,
            preprocessing_config_id=self.config.id,
            meta_data={
                "file_type": "image",
                "ocr_backend": self.config.ocr_backend
            }
        )

        self.db.add(doc)
        return [doc]

    def _process_text_file(self, file: models.File, file_task: models.FilePreprocessingTask) -> List[models.Document]:
        """Process plain text files."""
        file_content = get_file(file.file_uuid)

        # Decode text content
        text = file_content.decode('utf-8', errors='replace')

        # Create document
        doc = models.Document(
            project_id=self.task.project_id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            text=text,
            document_name=file.file_name,
            preprocessing_config_id=self.config.id,
            meta_data={
                "file_type": "text"
            }
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


# Legacy function for backward compatibility
def preprocess_files(
        files: list[models.File],
        client: OpenAI | None = None,
        pdf_backend: str = "pymupdf4llm",
        ocr_backend: str = "ocrmypdf",
        llm_model: str | None = None,
        use_ocr: bool = True,
        force_ocr: bool = False,
        ocr_languages: list[str] | None = None,
        ocr_model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        db_session: Session | None = None,
        project_id: int | None = None,
        preprocessing_task_id: int | None = None,
        output_file: bool = True,
) -> list[str]:
    """
    Legacy preprocessing function for backward compatibility.
    Creates a configuration and task, then uses the new pipeline.
    """
    if not db_session:
        # Simple processing without database
        from llmaix import preprocess_file as llmaix_preprocess_file
        results = []
        for file in files:
            file_content = get_file(file.file_uuid)
            result = llmaix_preprocess_file(
                filename=file_content,
                client=client,
                pdf_backend=pdf_backend,
                ocr_backend=ocr_backend,
                llm_model=llm_model,
                use_ocr=use_ocr,
                force_ocr=force_ocr,
                ocr_languages=ocr_languages,
                ocr_model=ocr_model,
                base_url=base_url,
                api_key=api_key,
            )
            results.append(result)
        return results

    # Use new pipeline for database processing
    if not project_id:
        raise ValueError("project_id is required when using database session")

    # Create or get preprocessing task
    if preprocessing_task_id:
        task = db_session.get(models.PreprocessingTask, preprocessing_task_id)
        if not task:
            raise ValueError(f"PreprocessingTask {preprocessing_task_id} not found")
    else:
        # Create configuration
        config = models.PreprocessingConfiguration(
            project_id=project_id,
            name=f"Legacy config - {ocr_backend}",
            description="Created from legacy preprocess_files call",
            file_type=models.FileType.MIXED,  # Will be updated per file
            preprocessing_strategy=models.PreprocessingStrategy.FULL_DOCUMENT,
            pdf_backend=pdf_backend,
            ocr_backend=ocr_backend,
            use_ocr=use_ocr,
            force_ocr=force_ocr,
            ocr_languages=ocr_languages,
            ocr_model=ocr_model,
            llm_model=llm_model,
            additional_settings={
                "base_url": base_url,
                "api_key": api_key,
                "output_file": output_file,
            }
        )
        db_session.add(config)
        db_session.commit()

        # Create task
        task = models.PreprocessingTask(
            project_id=project_id,
            configuration_id=config.id,
            total_files=len(files)
        )
        db_session.add(task)
        db_session.commit()

        # Create file tasks
        for file in files:
            file_task = models.FilePreprocessingTask(
                preprocessing_task_id=task.id,
                file_id=file.id
            )
            db_session.add(file_task)
        db_session.commit()

    # Process using new pipeline
    pipeline = PreprocessingPipeline(db_session, task.id)
    if client:
        pipeline.client = client
    pipeline.process()

    # Return document texts for backward compatibility
    db_session.refresh(task)
    results = []
    for file_task in task.file_tasks:
        for doc in file_task.documents:
            results.append(doc.text)

    return results
