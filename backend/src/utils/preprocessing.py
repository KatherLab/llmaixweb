# backend/src/utils/preprocessing.py

import datetime
import io
import logging
import math
from typing import Any, List, cast

import httpx
import pandas as pd
from openai import OpenAI
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .. import models
from ..core.config import settings
from ..db.session import db_session
from ..dependencies import get_file
from ..middleware.error_handlers import (
    internal_error_message,
    operational_error_message,
)
from .helpers import _make_aware, detect_text_encoding
from .json_utils import case_id_str as _case_id_str
from .json_utils import strip_nul as _strip_nul
from .url_safety import enforce_endpoint_allowlist, validate_user_endpoint

logger = logging.getLogger(__name__)

# How often _process_with_timeout bumps file_task.last_heartbeat_at while
# waiting for a file to finish. Must be comfortably shorter than the sweeper's
# stale-heartbeat cutoff so an actively-processing file is never reaped.
_HEARTBEAT_INTERVAL_SECONDS = 15

# Sentinel pushed to the result queue by the worker thread when it fails, so the
# poller wakes immediately (instead of blocking a full heartbeat interval) and
# raises the real exception carried on the separate exception queue.
_WORKER_ERROR = object()


def _json_safe(value: Any) -> Any:
    """Recursively convert a value into something ``json.dumps`` can handle.

    Raw pandas cell values leak non-JSON types into JSON columns
    (``pd.Timestamp`` from date columns, numpy scalars, ``NaT``/``NaN``),
    which otherwise blow up the whole batch commit at flush time.
    """
    if isinstance(value, str):
        return _strip_nul(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if value is None or isinstance(value, (int, bool)):
        return value
    if isinstance(value, dict):
        return {_strip_nul(str(k)): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    try:
        if pd.isna(value):  # NaT, pd.NA
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if hasattr(value, "item"):  # numpy scalar
        return _json_safe(value.item())
    return _strip_nul(str(value))


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
        task = db.get(models.PreprocessingTask, task_id)
        if task is None:
            raise ValueError(f"PreprocessingTask {task_id} not found")
        self.task: models.PreprocessingTask = task
        self.config = self.task.configuration
        self.cancelled = False
        self.client = None
        self._docling_serve_client = None
        # Set when a per-file timeout leaves a zombie worker thread holding
        # `self.db`; the main loop must abort and finalize via fresh sessions.
        self._timeout_abort = False

        # Store API credentials in task metadata if custom ones provided
        if api_key and base_url:
            # Validate the user-supplied custom endpoint against the SSRF
            # policy (block cloud-metadata + non-http(s) schemes). System
            # defaults (the elif branch) are trusted and not validated here.
            validated = validate_user_endpoint(base_url)
            if validated is None:
                raise ValueError(
                    "A custom API base_url is required when api_key is set."
                )
            self.client = OpenAI(
                api_key=api_key,
                base_url=validated,
                # follow_redirects=False: a user-controlled endpoint must not
                # 3xx-bounce the request to a blocked internal address.
                http_client=httpx.Client(follow_redirects=False),
            )
            # Store in task metadata for audit
            if not self.task.task_metadata:
                self.task.task_metadata = {}
            self.task.task_metadata["custom_api_used"] = True
            self.task.task_metadata["api_base_url"] = validated
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

    def close(self) -> None:
        """Release the pipeline's HTTP clients.

        The OpenAI client (with its httpx connection pool) and the lazily-created
        DoclingServeClient are never closed otherwise; in the Celery path a new
        pipeline is constructed per file task, so leaking them accumulates open
        sockets/file descriptors across a long-running worker. Safe to call when
        the clients were never created (they stay ``None``).
        """
        client = self.client
        self.client = None
        if client is not None:
            close = getattr(client, "close", None)
            if close is not None:
                try:
                    close()
                except Exception:
                    logger.debug("Error closing pipeline OpenAI client", exc_info=True)
        dsc = self._docling_serve_client
        self._docling_serve_client = None
        if dsc is not None:
            try:
                dsc.close()
            except Exception:
                logger.debug("Error closing docling-serve client", exc_info=True)

    def _broadcast_update(self, event: str = "progress"):
        """Broadcast a preprocessing update for direct (bypass_celery) processing.

        Publishes via Redis pub/sub — the same channel the Celery worker path
        uses — so the FastAPI subscriber relays it to WebSocket clients on the
        correct event loop. This avoids the previous approach of calling
        ``manager.broadcast_to_user`` from a spawned thread/new event loop,
        which (a) sent on a foreign loop (undefined asyncio behavior) and (b)
        passed ``project_id`` as the ``user_id`` argument, so updates never
        reached real users. If Redis is unavailable this is a no-op, matching
        the Celery path's best-effort behavior.
        """
        try:
            from ..utils.redis_broadcast import publish_task_update

            message = {
                "type": "preprocessing_update",
                "task_id": self.task.id,
                "project_id": self.task.project_id,
                "status": self.task.status,
                "processed_files": self.task.processed_files,
                "total_files": self.task.total_files,
                "failed_files": self.task.failed_files,
                "cancelled_files": self.task.skipped_files,
                "configuration_name": self.task.configuration.name
                if self.task.configuration
                else None,
                "event": event,
            }
            publish_task_update(message)
        except ImportError:
            pass  # Redis broadcast not available
        except Exception as e:
            logger.error(f"Error broadcasting preprocessing update: {e}")

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

                # A per-file timeout leaves a zombie worker thread that may
                # still be using `self.db`. Abort the batch and finalize via
                # fresh sessions so the main thread never races that thread.
                if self._timeout_abort:
                    self._finalize_after_timeout(file_task.id)
                    return

                # Update overall counters in place from the just-finished file
                # task's status. Recomputing by scanning the whole file_tasks
                # collection here is O(n) per file → O(n²) for the batch and
                # triggers lazy loads; incrementing is O(1).
                if file_task.status == models.PreprocessingStatus.COMPLETED:
                    self.task.processed_files = (self.task.processed_files or 0) + 1
                elif file_task.status == models.PreprocessingStatus.FAILED:
                    self.task.failed_files = (self.task.failed_files or 0) + 1
                self.db.commit()

                # Broadcast progress update after each file
                self._broadcast_update("progress")

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
            # Count failures explicitly so CANCELLED files aren't miscounted
            # as failed (total - completed would count any non-completed
            # status, including CANCELLED).
            failed = sum(
                1
                for ft in self.task.file_tasks
                if ft.status == models.PreprocessingStatus.FAILED
            )

            # Sync the persisted counters with the final tally (the per-file
            # in-place increments don't cover the just-auto-failed unfinished
            # tasks above).
            self.task.processed_files = completed
            self.task.failed_files = failed

            # ───── final status / message ───────────────────────────────────
            if self.cancelled:
                # leave status/message set by the cancel workflow
                event = "cancelled"
            elif completed == total:
                self.task.status = models.PreprocessingStatus.COMPLETED
                self.task.message = "Processing completed successfully."
                event = "completed"
            elif failed == total:
                self.task.status = models.PreprocessingStatus.FAILED
                self.task.message = "All files failed to preprocess."
                logger.warning(
                    "All files failed to preprocess for task %s", self.task.id
                )
                event = "failed"
            else:
                self.task.status = models.PreprocessingStatus.FAILED
                self.task.message = (
                    f"{completed} of {total} files processed successfully, "
                    f"{failed} failed."
                )
                event = "failed"

            self.task.completed_at = datetime.datetime.now(datetime.UTC)

            # Broadcast final status
            self._broadcast_update(event)

        except Exception as e:
            # any unhandled exception ⇒ whole preprocessing task failed
            self.task.status = models.PreprocessingStatus.FAILED
            self.task.message = internal_error_message(e, prefix="Processing failed")
            self.task.completed_at = datetime.datetime.now(datetime.UTC)
            self.db.commit()
            # Broadcast failure
            self._broadcast_update("failed")
        finally:
            # ───── persist final state ──────────────────────────────────────
            self.db.commit()
            # Always release the pipeline's HTTP clients (OpenAI + docling-serve)
            # so per-file-task pipelines in the Celery path don't leak pools.
            self.close()

    def _fail_file_task_fresh(self, file_task_id: int, message: str) -> None:
        """Mark a single file task FAILED in a fresh session.

        Used after a per-file timeout: the timed-out worker thread may still be
        using ``self.db``, so the failure is recorded in an independent session
        to avoid concurrent (non-thread-safe) session access.
        """
        try:
            with db_session() as fresh_db:
                ft = fresh_db.get(models.FilePreprocessingTask, file_task_id)
                if ft and ft.status in (
                    models.PreprocessingStatus.PENDING,
                    models.PreprocessingStatus.IN_PROGRESS,
                ):
                    ft.status = models.PreprocessingStatus.FAILED
                    ft.error_message = message
                    ft.completed_at = datetime.datetime.now(datetime.UTC)
        except Exception:
            logger.exception(
                "Failed to mark file task %s FAILED after timeout", file_task_id
            )

    def _finalize_after_timeout(self, timed_out_file_task_id: int) -> None:
        """Abort the batch after a per-file timeout and finalize in fresh sessions.

        A timed-out worker thread keeps running and may keep using ``self.db``,
        so the whole remaining finalization (fail unfinished file tasks, mark the
        parent task FAILED, broadcast) happens through independent sessions — the
        main thread never touches ``self.db`` again.
        """
        task_id = self.task.id
        logger.warning(
            "PreprocessingTask %s: aborting batch after file task %s timed out",
            task_id,
            timed_out_file_task_id,
        )
        try:
            with db_session() as fresh_db:
                task = fresh_db.get(models.PreprocessingTask, task_id)
                if not task:
                    return

                now = datetime.datetime.now(datetime.UTC)
                for ft in task.file_tasks:
                    if ft.status in (
                        models.PreprocessingStatus.PENDING,
                        models.PreprocessingStatus.IN_PROGRESS,
                    ):
                        ft.status = models.PreprocessingStatus.FAILED
                        ft.error_message = (
                            "Skipped: a preceding file timed out and aborted the batch."
                        )
                        ft.completed_at = now

                total = len(task.file_tasks)
                completed = sum(
                    1
                    for ft in task.file_tasks
                    if ft.status == models.PreprocessingStatus.COMPLETED
                )
                # Count failures explicitly (see _finalize note re: CANCELLED).
                failed = sum(
                    1
                    for ft in task.file_tasks
                    if ft.status == models.PreprocessingStatus.FAILED
                )

                task.processed_files = completed
                task.failed_files = failed
                task.status = models.PreprocessingStatus.FAILED
                task.message = (
                    f"Processing aborted: a file exceeded its timeout and the "
                    f"batch was stopped to protect the database session. "
                    f"{completed} of {total} files processed successfully, "
                    f"{failed} failed."
                )
                task.completed_at = now

                # Capture values for broadcast before the session closes.
                broadcast_payload = {
                    "type": "preprocessing_update",
                    "task_id": task.id,
                    "project_id": task.project_id,
                    "status": task.status.value
                    if hasattr(task.status, "value")
                    else str(task.status),
                    "processed_files": task.processed_files,
                    "total_files": task.meta.get("total_files", 0)
                    if task.meta
                    else task.total_files,
                    "failed_files": task.failed_files,
                    "cancelled_files": task.skipped_files,
                    "configuration_name": task.configuration.name
                    if task.configuration
                    else None,
                    "event": "failed",
                }
        except Exception:
            logger.exception(
                "PreprocessingTask %s: failed to finalize after timeout", task_id
            )
            return

        # Publish via Redis (works from the Celery worker process); never
        # touches self.db.
        try:
            from ..utils.redis_broadcast import publish_task_update

            if not publish_task_update(broadcast_payload):
                logger.warning(
                    "PreprocessingTask %s: failed to broadcast timeout abort", task_id
                )
        except Exception:
            logger.exception(
                "PreprocessingTask %s: failed to publish timeout broadcast", task_id
            )

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
                # Default to "auto" for automatic language detection
                ocr_langs = "auto"
            # If ocr_langs is already a string (e.g., "auto") or list, use it as-is

            self._docling_serve_client = DoclingServeClient(
                base_url=base_url,
                timeout_seconds=timeout,
                max_retries=max_retries,
                default_ocr_langs=ocr_langs,
            )

        return self._docling_serve_client

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

        case_ids = df[case_id_column]

        # Empty/NaN case IDs would silently produce documents named "nan"
        # (or trip the duplicate check below with a baffling message) —
        # fail with an explicit, actionable error instead.
        empty_mask = case_ids.isna() | case_ids.astype(str).str.strip().eq("")
        if empty_mask.any():
            empty_rows = [int(i) for i in case_ids.index[empty_mask][:10]]
            raise ValueError(
                f"{int(empty_mask.sum())} row(s) in file {file.file_name} have an "
                f"empty case ID in column '{case_id_column}' (row indices: "
                f"{empty_rows}...). Fill in the missing IDs or choose a "
                "different case ID column."
            )

        # Compare the normalized strings that actually become document names
        # (so 1 vs "1" vs 1.0, or values differing only in whitespace, are
        # caught as the collisions they would cause).
        normalized = case_ids.map(_case_id_str)
        duplicates = normalized.duplicated()
        if duplicates.any():
            duplicate_values = list(normalized[duplicates].unique()[:10])
            raise ValueError(
                f"Duplicate case IDs found in column '{case_id_column}': {duplicate_values}... "
                f"File: {file.file_name}"
            )

    def _get_file_timeout(
        self, file: models.File, extraction_mode: str | None = None
    ) -> int:
        """Get timeout in seconds for a file based on its type and OCR backend.

        Args:
            file: The file model to check.
            extraction_mode: The OCR extraction mode being used (if applicable).

        Returns:
            Timeout in seconds for this file type/backend combination.
        """
        additional = self.config.additional_settings or {}
        ocr_engine = additional.get("ocr_engine", "docling_tesseract")

        # Determine which backend will be used
        is_pdf = file.file_type == models.FileType.APPLICATION_PDF

        # For table files (CSV/Excel) or plain text, use default timeout
        if file.file_type in [
            models.FileType.TEXT_CSV,
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            models.FileType.TEXT_PLAIN,
        ]:
            return settings.PREPROCESS_FILE_TIMEOUT_SECONDS

        # For PDFs with embedded text (no OCR), use docling-serve timeout
        if is_pdf and not additional.get("force_ocr", False):
            # Check if we'd use embedded text extraction
            if extraction_mode == "auto" or extraction_mode is None:
                return settings.DOCLING_SERVE_FILE_TIMEOUT_SECONDS

        # For remote OCR backends. Check the explicit engine first: with
        # extraction_mode == "high_accuracy_remote" AND ocr_engine ==
        # "llm_vision", the mode-based branch would otherwise win and apply
        # the Mistral timeout to a Vision run.
        if ocr_engine == "llm_vision":
            return settings.VISION_OCR_FILE_TIMEOUT_SECONDS
        if ocr_engine == "mistral_ocr" or extraction_mode == "high_accuracy_remote":
            return settings.MISTRAL_OCR_FILE_TIMEOUT_SECONDS

        # Default to docling-serve timeout for local OCR
        return settings.DOCLING_SERVE_FILE_TIMEOUT_SECONDS

    def _process_file_task(self, file_task: models.FilePreprocessingTask):
        """Process a single file task with timeout protection."""
        file_task_id = file_task.id  # local copy; safe to use after a timeout
        file_task.status = models.PreprocessingStatus.IN_PROGRESS
        now = datetime.datetime.now(datetime.UTC)
        file_task.started_at = now
        file_task.last_heartbeat_at = now
        # File.file_name is String(500) but this column is String(255) —
        # truncate so a long filename doesn't fail the commit (outside the
        # try below, that would abort the whole batch).
        file_task.file_name = file_task.file.file_name[:255]
        self.db.commit()

        try:
            file = file_task.file

            # Safety check: detect if another task is already processing this file
            # with the same config (race condition protection for simultaneous requests)
            # This is a final safety net - the API endpoint should have already rejected
            # such requests, but this catches any remaining race conditions
            conflicting_task = (
                self.db.query(models.FilePreprocessingTask)
                .join(models.PreprocessingTask)
                .filter(
                    models.FilePreprocessingTask.file_id == file.id,
                    models.PreprocessingTask.configuration_id == self.config.id,
                    models.FilePreprocessingTask.id != file_task.id,
                    models.FilePreprocessingTask.status.in_(
                        [
                            models.PreprocessingStatus.PENDING,
                            models.PreprocessingStatus.IN_PROGRESS,
                        ]
                    ),
                )
                .first()
            )
            if conflicting_task:
                # Another task is already processing this file with the same config
                # Cancel this task to avoid duplicate document creation
                file_task.status = models.PreprocessingStatus.CANCELLED
                file_task.error_message = (
                    f"Skipped: file is already being processed by task {conflicting_task.id} "
                    f"(same file + config combination)"
                )
                file_task.completed_at = datetime.datetime.now(datetime.UTC)
                self.db.commit()
                logger.info(
                    "Skipped file task %s for file %s: already being processed by task %s",
                    file_task.id,
                    file.file_name,
                    conflicting_task.id,
                )
                return

            # Get timeout for this file type/backend
            additional = self.config.additional_settings or {}
            extraction_mode = additional.get("extraction_mode", "auto")
            timeout_seconds = self._get_file_timeout(file, extraction_mode)
            # Capture as locals so the TimeoutError handler (which must not
            # touch self.db while a zombie thread may be using it) doesn't need
            # to read ORM attributes.
            file_name_local = file_task.file_name or file.file_name

            # Route to appropriate processor based on file type with timeout
            if file.file_type in [
                models.FileType.TEXT_CSV,
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ]:
                documents = self._process_with_timeout(
                    self._process_table_file, file, file_task, timeout_seconds
                )
            elif file.file_type in [models.FileType.TEXT_PLAIN]:
                documents = self._process_with_timeout(
                    self._process_text_file, file, file_task, timeout_seconds
                )
            else:
                # PDF/Image files — route by OCR engine with timeout
                documents = self._process_with_timeout(
                    self._route_pdf_image, file, file_task, timeout_seconds
                )

            # Flush to get document IDs before collecting them
            self.db.flush()

            file_task.document_count = len(documents)
            file_task.document_ids = [doc.id for doc in documents]
            # If the task was cancelled while this file was mid-flight (e.g. a
            # row-by-row CSV broke out of its row loop early), the file is only
            # PARTIALLY processed — mark it CANCELLED, not COMPLETED, so a partial
            # file isn't indistinguishable from a fully processed one (and is
            # rolled back with the rest when rollback_on_cancel is set).
            if self.check_cancelled():
                file_task.status = models.PreprocessingStatus.CANCELLED
            else:
                file_task.status = models.PreprocessingStatus.COMPLETED
            file_task.completed_at = datetime.datetime.now(datetime.UTC)

            # Calculate processing time
            if file_task.started_at:
                processing_time = (
                    _make_aware(datetime.datetime.now())
                    - _make_aware(file_task.started_at)
                ).total_seconds()
                file_task.processing_time = round(processing_time, 2)

        except TimeoutError as e:
            # The worker thread that timed out is still alive and may keep
            # using `self.db` (SQLAlchemy sessions are not thread-safe). Mark
            # the file task FAILED in a FRESH session and signal the batch to
            # abort, so the main thread never touches `self.db` again while
            # the zombie thread might still be using it.
            #
            # NOTE: do NOT access relationships on `file_task` here (e.g.
            # `file_task.file`) — that would lazy-load through `self.db` and
            # race the zombie thread. Use only direct columns / locals.
            self._timeout_abort = True
            file_name = (
                file_name_local if "file_name_local" in dir() else f"#{file_task_id}"
            )
            # `timeout_seconds` is computed before the timed-out call; fall back
            # gracefully if control reached here before it was set.
            secs = timeout_seconds if "timeout_seconds" in dir() else 0
            logger.error("Timeout processing file %s after %ds: %s", file_name, secs, e)
            msg = (
                f"Processing timed out after {secs} seconds. "
                "The file may be too large or the OCR service is unresponsive."
            )
            self._fail_file_task_fresh(file_task_id, msg)
            return

        except ValueError as e:
            # ValueError is this pipeline's user-facing error convention (as
            # in the API endpoints): deliberately crafted, actionable messages
            # about the user's own data/config (duplicate case IDs, missing
            # columns, unsupported variants, parse errors of the uploaded
            # file). Surface the message verbatim — hiding it behind an error
            # id would make the failure un-actionable. Sites that wrap raw
            # service/library errors route them through
            # internal_error_message() first, so no internals arrive here.
            self.db.rollback()
            file_task.status = models.PreprocessingStatus.FAILED
            logger.warning(
                "File %s failed preprocessing: %s", file_task.file.file_name, e
            )
            file_task.error_message = _strip_nul(str(e))[:4000]
            file_task.completed_at = datetime.datetime.now(datetime.UTC)

        except Exception as e:
            # A failed flush/commit leaves the session in pending-rollback
            # state; roll back before touching ORM attributes, otherwise the
            # lazy loads below raise PendingRollbackError and the file task
            # is never marked FAILED.
            self.db.rollback()
            file_task.status = models.PreprocessingStatus.FAILED
            logger.error(
                "Error processing file %s: %s",
                file_task.file.file_name,
                e,
                exc_info=True,
            )
            file_task.error_message = internal_error_message(
                e, prefix="File processing failed"
            )
            file_task.completed_at = datetime.datetime.now(datetime.UTC)

        self.db.commit()

    def _process_with_timeout(self, func, file, file_task, timeout_seconds: int):
        """Execute a processing function with timeout protection.

        Uses threading-based timeout which works in all contexts (including
        threaded Celery workers and test environments).

        While waiting, bumps ``file_task.last_heartbeat_at`` every
        ``_HEARTBEAT_INTERVAL_SECONDS`` so the orphan sweeper can distinguish a
        slow-but-alive file from a dead worker. The heartbeat uses a separate
        session and a bulk UPDATE (not ``self.db``) to avoid contending with
        the worker thread, which may be using ``self.db``.

        Args:
            func: The processing function to call.
            file: The file model to pass to func.
            file_task: The file preprocessing task model.
            timeout_seconds: Timeout in seconds.

        Returns:
            Result of func(file, file_task).

        Raises:
            TimeoutError: If processing exceeds timeout.
        """
        import queue
        import threading

        from sqlalchemy import update

        result_queue = queue.Queue()
        exception_queue = queue.Queue()

        def target():
            try:
                result = func(file, file_task)
                result_queue.put(result)
            except Exception as e:
                # If the main thread already timed out and aborted, this zombie
                # thread's result/exception is discarded anyway. Its `self.db`
                # usage may race the main session's closure (sessions aren't
                # thread-safe), surfacing as a ResourceClosed/StatementError
                # here — log it at debug rather than propagating a confusing
                # error, since the timeout path already recorded the failure in
                # a fresh session.
                if self._timeout_abort:
                    logger.debug(
                        "Zombie worker thread for file task %s ended with "
                        "%s after timeout abort (discarded): %s",
                        file_task.id,
                        type(e).__name__,
                        e,
                    )
                else:
                    # Carry the real exception on exception_queue, then wake the
                    # poller via result_queue so a fast failure surfaces at once
                    # rather than after a full heartbeat interval / the timeout.
                    exception_queue.put(e)
                    result_queue.put(_WORKER_ERROR)

        def _heartbeat():
            now = datetime.datetime.now(datetime.UTC)
            with db_session() as fresh_db:
                fresh_db.execute(
                    update(models.FilePreprocessingTask)
                    .where(models.FilePreprocessingTask.id == file_task.id)
                    .values(last_heartbeat_at=now)
                )
                fresh_db.commit()

        thread = threading.Thread(target=target, daemon=True)
        thread.start()

        deadline = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            seconds=timeout_seconds
        )
        while True:
            # Poll with a short timeout so we can heartbeat regularly without
            # delaying detection of completion/exception.
            remaining = (deadline - datetime.datetime.now(datetime.UTC)).total_seconds()
            if remaining <= 0:
                # Timed out. Surface a worker exception if one arrived; only
                # report a timeout if the worker is genuinely still running.
                try:
                    exc = exception_queue.get_nowait()
                    raise exc
                except queue.Empty:
                    raise TimeoutError(
                        f"Processing exceeded {timeout_seconds}s timeout for file {file.file_name}"
                    )
            try:
                result = result_queue.get(
                    timeout=min(_HEARTBEAT_INTERVAL_SECONDS, remaining)
                )
                # A fast worker failure would otherwise sit unread on the separate
                # exception_queue until the full per-file timeout elapsed — making a
                # file that failed in milliseconds (e.g. a validation error like
                # duplicate case IDs or missing text columns) look like it
                # "processed" for minutes. The worker pushes _WORKER_ERROR here to
                # wake us immediately; raise the real exception it carried.
                if result is _WORKER_ERROR:
                    raise exception_queue.get_nowait()
                return result
            except queue.Empty:
                # Still running — bump the heartbeat and keep waiting.
                try:
                    _heartbeat()
                except Exception as e:
                    logger.debug(
                        "Heartbeat update failed for file task %s: %s", file_task.id, e
                    )
                continue

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

    def _check_password_protected_pdf(self, file_content: bytes) -> bool:
        """Check if a PDF is password-protected using pypdf.

        Args:
            file_content: Raw PDF file bytes.

        Returns:
            True if PDF is password-protected, False otherwise.
        """
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(file_content))
            return reader.is_encrypted
        except Exception:
            # If we can't read the PDF, assume it's not password-protected
            # (it might be corrupted or invalid)
            return False

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
        file_content = get_file(file.file_uuid)

        # Check for password-protected PDF
        if self._check_password_protected_pdf(file_content):
            if settings.PDF_HANDLE_PASSWORD_PROTECTED:
                logger.warning(
                    "PDF %s is password-protected. OCR will be attempted but may fail.",
                    file.file_name,
                )
                self._add_file_task_warnings(
                    file_task,
                    [
                        "This PDF is password-protected. Text extraction may be incomplete."
                    ],
                )
            else:
                raise ValueError(
                    f"PDF {file.file_name} is password-protected. "
                    "Password-protected PDFs are not supported. "
                    "Please remove the password or use an unprotected copy."
                )

        # Check if docling-serve is disabled and no OCR engines are available
        # In this case, only PDFs with embedded text can be processed using pypdf directly
        # Exception: DOCLING_LOCAL_FALLBACK=true allows using local Docling directly
        if (
            not settings.DOCLING_SERVE_ENABLED
            and not settings.MISTRAL_OCR_ENABLED
            and not settings.VISION_OCR_ENABLED
        ):
            from ..services.pdf_text_probe import has_embedded_text

            has_text = has_embedded_text(
                file_content,
                min_chars=settings.DOCLING_MIN_EXTRACTED_CHARS_PDF,
                max_pages_to_check=settings.PDF_MAX_PAGES_FOR_TEXT_PROBE,
            )

            if has_text:
                # Extract text directly using pypdf (no docling-serve needed)
                return self._process_pdf_with_pypdf(file, file_task, file_content)
            elif settings.DOCLING_LOCAL_FALLBACK:
                # Use local Docling directly when fallback is enabled
                from ..services.docling_serve_client import (
                    DoclingServeError,
                    _convert_with_local_docling,
                )

                try:
                    result = _convert_with_local_docling(
                        file_content=file_content,
                        filename=file.file_name,
                        mime_type="application/pdf",
                        from_formats=["pdf"],
                        do_ocr=True,
                        force_ocr=True,
                        ocr_engine="tesseract",
                        ocr_langs=None,
                    )
                    doc = self._build_pdf_document(
                        file=file,
                        file_task=file_task,
                        text=result.text,
                        ocr_engine="tesseract",
                        extraction_method="local_docling_fallback",
                        ocr_applied=True,
                    )
                    return [doc]
                except DoclingServeError as e:
                    raise ValueError(
                        internal_error_message(
                            e,
                            prefix="PDF has no embedded text and local Docling fallback failed",
                        )
                    )
            else:
                # No embedded text and no OCR available - fail with clear message
                raise ValueError(
                    "PDF has no embedded text and all OCR engines are disabled. "
                    "Enable Local OCR (docling-serve), Mistral OCR, or Vision LLM in Admin Settings, "
                    "or upload a PDF with embedded text."
                )

        # Get quality thresholds from settings
        min_chars_pdf = settings.DOCLING_MIN_EXTRACTED_CHARS_PDF

        # Helper to check if docling-serve is available
        def docling_serve_available() -> bool:
            return settings.DOCLING_SERVE_ENABLED

        # Force OCR mode - always use Tesseract with force_ocr=True
        if extraction_mode == "force_ocr" or force_ocr:
            if not docling_serve_available():
                # Fall back to pypdf for embedded text, or fail
                file_content = get_file(file.file_uuid)
                from ..services.pdf_text_probe import has_embedded_text

                has_text = has_embedded_text(
                    file_content,
                    min_chars=min_chars_pdf,
                    max_pages_to_check=8,
                )
                if has_text:
                    return self._process_pdf_with_pypdf(file, file_task, file_content)
                else:
                    raise ValueError(
                        "Force OCR requested but docling-serve is disabled. "
                        "PDF has no embedded text to extract. Enable docling-serve or upload a PDF with embedded text."
                    )
            return self._process_with_docling_serve_tesseract(
                file,
                file_task,
                force_full_page_ocr=True,
            )

        # Fast local OCR - always use Tesseract
        if extraction_mode == "fast_local_ocr":
            if not docling_serve_available():
                # Fall back to pypdf for embedded text, or fail
                file_content = get_file(file.file_uuid)
                from ..services.pdf_text_probe import has_embedded_text

                has_text = has_embedded_text(
                    file_content,
                    min_chars=min_chars_pdf,
                    max_pages_to_check=8,
                )
                if has_text:
                    return self._process_pdf_with_pypdf(file, file_task, file_content)
                else:
                    raise ValueError(
                        "Fast local OCR requested but docling-serve is disabled. "
                        "PDF has no embedded text to extract. Enable docling-serve or upload a PDF with embedded text."
                    )
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
                # Use docling-serve without OCR if available, otherwise use pypdf directly
                if docling_serve_available():
                    return self._process_with_docling_serve_no_ocr(file, file_task)
                else:
                    return self._process_pdf_with_pypdf(file, file_task, file_content)
            else:
                # Need OCR - use docling-serve if available
                if docling_serve_available():
                    return self._process_with_docling_serve_tesseract(
                        file,
                        file_task,
                        force_full_page_ocr=False,
                    )
                else:
                    # No embedded text and docling-serve disabled - fail with clear message
                    raise ValueError(
                        "PDF has no embedded text and docling-serve is disabled. "
                        "Enable docling-serve in Admin Settings, or upload a PDF with embedded text."
                    )

        # High accuracy remote mode - use remote OCR only if enabled and needed
        if extraction_mode == "high_accuracy_remote":
            if not remote_fallback:
                # Remote fallback disabled - use local Tesseract (docling-serve)
                if docling_serve_available():
                    return self._process_with_docling_serve_tesseract(
                        file,
                        file_task,
                        force_full_page_ocr=False,
                    )
                else:
                    # Fall back to pypdf for embedded text, or fail
                    file_content = get_file(file.file_uuid)
                    from ..services.pdf_text_probe import has_embedded_text

                    has_text = has_embedded_text(
                        file_content,
                        min_chars=min_chars_pdf,
                        max_pages_to_check=8,
                    )
                    if has_text:
                        return self._process_pdf_with_pypdf(
                            file, file_task, file_content
                        )
                    else:
                        raise ValueError(
                            "PDF has no embedded text and docling-serve is disabled. "
                            "Enable docling-serve or use remote OCR fallback."
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
                    # Use local docling-serve without OCR if available, otherwise pypdf
                    if docling_serve_available():
                        return self._process_with_docling_serve_no_ocr(file, file_task)
                    else:
                        return self._process_pdf_with_pypdf(
                            file, file_task, file_content
                        )

            # Use remote OCR - respect the original ocr_engine setting. Check
            # actual usability (per-task credentials or global config), not just
            # the *_ENABLED flag — a run configured per-task shouldn't be blocked
            # at routing.
            mistral_usable = self._mistral_ocr_usable()
            vision_usable = self._llm_vision_ocr_usable()
            if ocr_engine == "mistral_ocr" and mistral_usable:
                return self._process_with_mistral_ocr(file, file_task)
            elif ocr_engine == "llm_vision" and vision_usable:
                return self._process_with_llm_vision_ocr(file, file_task)
            elif mistral_usable:
                # Fallback to Mistral if no specific engine requested
                return self._process_with_mistral_ocr(file, file_task)
            elif vision_usable:
                # Fallback to Vision if no specific engine requested
                return self._process_with_llm_vision_ocr(file, file_task)
            else:
                # Remote fallback requested but not configured - fail clearly.
                # Name the actually-requested engine so the message isn't
                # misleading (e.g. "docling-serve is disabled" when vision was
                # requested).
                if ocr_engine == "llm_vision":
                    raise ValueError(
                        "Vision LLM OCR was requested but is not usable: "
                        "VISION_OCR_ENABLED is false, or no api_key/base_url is "
                        "configured (set vision_api_key/vision_base_url in the "
                        "preprocessing config, or VISION_OCR_API_KEY/"
                        "VISION_OCR_API_BASE in server settings)."
                    )
                elif ocr_engine == "mistral_ocr":
                    raise ValueError(
                        "Mistral OCR was requested but is not usable: "
                        "MISTRAL_OCR_ENABLED is false, or no api_key is "
                        "configured (set mistral_api_key in the preprocessing "
                        "config, or MISTRAL_API_KEY in server settings)."
                    )
                raise ValueError(
                    "High accuracy remote OCR requested but neither Mistral OCR "
                    "nor Vision LLM is usable. Enable and configure Mistral OCR "
                    "(MISTRAL_OCR_ENABLED + MISTRAL_API_KEY) or Vision LLM "
                    "(VISION_OCR_ENABLED + VISION_OCR_API_KEY/API_BASE), or use "
                    "a different extraction mode."
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
            # Respect the original ocr_engine setting. Check actual usability
            # (per-task credentials or global config), not just the *_ENABLED
            # flag — a run configured per-task shouldn't be blocked at routing.
            mistral_usable = self._mistral_ocr_usable()
            vision_usable = self._llm_vision_ocr_usable()
            if ocr_engine == "mistral_ocr" and mistral_usable:
                return self._process_with_mistral_ocr(file, file_task)
            elif ocr_engine == "llm_vision" and vision_usable:
                return self._process_with_llm_vision_ocr(file, file_task)
            elif mistral_usable:
                # Fallback to Mistral if no specific engine requested
                return self._process_with_mistral_ocr(file, file_task)
            elif vision_usable:
                # Fallback to Vision if no specific engine requested
                return self._process_with_llm_vision_ocr(file, file_task)
            # Remote fallback requested but not usable - fall through to local
            if ocr_engine == "llm_vision":
                logger.warning(
                    "Vision LLM OCR requested for %s but it is not usable "
                    "(VISION_OCR_ENABLED=false or missing api_key/base_url); "
                    "falling back to local OCR.",
                    file.file_name,
                )
            elif ocr_engine == "mistral_ocr":
                logger.warning(
                    "Mistral OCR requested for %s but it is not usable "
                    "(MISTRAL_OCR_ENABLED=false or missing api_key); "
                    "falling back to local OCR.",
                    file.file_name,
                )

        # Check if docling-serve is available for local OCR
        if not settings.DOCLING_SERVE_ENABLED:
            # Check if local Docling fallback is available
            if settings.DOCLING_LOCAL_FALLBACK:
                # Use local Docling directly
                from ..dependencies import get_file
                from ..services.docling_serve_client import (
                    DoclingServeError,
                    _convert_with_local_docling,
                )

                file_content = get_file(file.file_uuid)
                mime_type = (
                    "image/png"
                    if file.file_type == models.FileType.IMAGE_PNG
                    else "image/jpeg"
                )

                try:
                    result = _convert_with_local_docling(
                        file_content=file_content,
                        filename=file.file_name,
                        mime_type=mime_type,
                        from_formats=["image"],
                        do_ocr=True,
                        force_ocr=True,
                        ocr_engine="tesseract",
                        ocr_langs=None,
                    )
                    doc = self._build_pdf_document(
                        file=file,
                        file_task=file_task,
                        text=result.text,
                        ocr_engine="tesseract",
                        extraction_method="local_docling_fallback",
                        ocr_applied=True,
                        extra_metadata={
                            "file_type": file.file_type,
                        },
                    )
                    return [doc]
                except DoclingServeError as e:
                    raise ValueError(
                        internal_error_message(
                            e,
                            prefix="Image processing requires OCR; docling-serve is disabled and local Docling fallback failed",
                        )
                    )
            else:
                # No local OCR and no remote OCR available - fail
                raise ValueError(
                    "Image processing requires OCR. docling-serve is disabled and no remote OCR (Mistral/Vision) is available. "
                    "Enable docling-serve in Admin Settings or configure Mistral OCR or Vision LLM."
                )

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
            raise ValueError(
                internal_error_message(e, prefix="docling-serve image OCR failed")
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
            raise ValueError(
                internal_error_message(
                    e, prefix="docling-serve Tesseract extraction failed"
                )
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
            raise ValueError(
                internal_error_message(e, prefix="docling-serve extraction failed")
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

        return [doc]

    def _process_pdf_with_pypdf(
        self,
        file: models.File,
        file_task: models.FilePreprocessingTask,
        file_content: bytes,
    ) -> List[models.Document]:
        """Process a PDF with embedded text using pypdf directly (no docling-serve).

        This is a fallback when all OCR engines are disabled but the PDF has
        embedded text that can be extracted.

        Args:
            file: The file model.
            file_task: The file preprocessing task.
            file_content: The PDF file content.

        Returns:
            List of created Document objects.
        """
        import io

        try:
            from pypdf import PdfReader

            pdf_reader = PdfReader(io.BytesIO(file_content))
            text_parts = []

            for page in pdf_reader.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)

            extracted_text = "\n\n".join(text_parts).strip()

            if not extracted_text:
                raise ValueError("pypdf extracted no text from PDF")

        except ValueError:
            # Deliberate user-facing message (e.g. "no text extracted") —
            # pass through untouched.
            raise
        except ImportError:
            raise ValueError(
                "pypdf is not installed. Install it with: pip install pypdf"
            )
        except Exception as e:
            # Raw pypdf/library errors can carry internals — error-log them
            # and surface only the category + error id.
            raise ValueError(
                internal_error_message(e, prefix="pypdf PDF extraction failed")
            )

        doc = self._build_pdf_document(
            file=file,
            file_task=file_task,
            text=extracted_text,
            ocr_engine="pypdf",
            extraction_method="pypdf_embedded_text",
            ocr_applied=False,
            extra_metadata={
                "embedded_text_detected": True,
                "force_ocr": False,
                "engine_used": "pypdf",
                "ocr_disabled_fallback": True,
            },
        )

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
        """Build a PDF-derived Document with consistent metadata and versioning.

        Implements document versioning: if a document with the same name/config
        already exists, archive it (is_latest=False) and create a new version.

        Handles re-processing safely by:
        1. Finding ALL existing documents (both latest and archived)
        2. Deleting only archived documents (is_latest=False) to free constraint slot
        3. Archiving latest documents (is_latest=True) normally
        4. Creating a new latest document

        Uses database-level locking (FOR UPDATE) to prevent race conditions
        when concurrent tasks process the same file with the same config.
        """
        # PostgreSQL rejects NUL bytes in text columns; OCR/pypdf output from
        # malformed PDFs can contain them.
        text = _strip_nul(text)

        # Use database-level locking to prevent race conditions.
        # with_for_update(nowait=True) will raise if another transaction holds the lock,
        # which we catch and retry after a brief wait.
        max_retries = 3
        retry_delay = 0.1  # seconds

        for attempt in range(max_retries):
            try:
                # Lock existing rows FOR UPDATE to prevent concurrent modifications
                all_existing_docs = (
                    self.db.query(models.Document)
                    .filter(
                        models.Document.original_file_id == file.id,
                        models.Document.preprocessing_config_id == self.config.id,
                        models.Document.document_name == file.file_name,
                    )
                    .with_for_update(nowait=True)
                    .all()
                )
                break  # Lock acquired successfully
            except OperationalError as e:
                # Lock conflict - another transaction is modifying these documents
                logger.warning(
                    "Document versioning lock conflict for file %s (attempt %d/%d): %s",
                    file.file_name,
                    attempt + 1,
                    max_retries,
                    e,
                )
                if attempt == max_retries - 1:
                    # All retries exhausted - check if documents already exist
                    # and return existing latest if found (idempotent behavior)
                    all_existing_docs = (
                        self.db.query(models.Document)
                        .filter(
                            models.Document.original_file_id == file.id,
                            models.Document.preprocessing_config_id == self.config.id,
                            models.Document.document_name == file.file_name,
                        )
                        .all()
                    )
                    latest_docs = [d for d in all_existing_docs if d.is_latest]
                    if latest_docs:
                        logger.info(
                            "Returning existing document for file %s after lock contention",
                            file.file_name,
                        )
                        return latest_docs[0]
                    # Re-raise if no existing document to return
                    raise
                import time

                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff

        # Separate latest from archived
        latest_docs = [d for d in all_existing_docs if d.is_latest]

        # Determine version_of for the new document
        version_of_root = None
        replaced_doc_id = None

        # The unique constraint on (file, config, name, is_latest) allows only ONE
        # is_latest=False document per key. So we need to:
        # 1. Delete orphaned archived docs first (free the constraint slot)
        #    Note: We cannot delete archived docs referenced by latest docs' version_of
        # 2. Then archive latest docs into the now-free slot

        # The unique constraint on (file, config, name) only applies when
        # is_latest=True, so we can have unlimited archived versions.
        # Simply archive all latest documents, then create the new version.

        # Archive latest documents
        if latest_docs:
            first_latest = latest_docs[0]
            version_of_root = first_latest.version_of or first_latest.id
            replaced_doc_id = first_latest.id

            # Archive all latest documents (usually just one)
            for doc in latest_docs:
                doc.document_sets.clear()
                doc.is_latest = False
                doc.updated_at = datetime.datetime.now(datetime.UTC)
                # Preserve version_of or point to root
                if version_of_root:
                    doc.version_of = version_of_root
            self.db.flush()

        # No need to touch archived_docs - they can coexist with unlimited versions

        metadata = {
            "file_type": file.file_type,
            "ocr_engine": ocr_engine,
            "extraction_method": extraction_method,
            "ocr_applied": ocr_applied,
        }

        if extra_metadata:
            metadata.update(extra_metadata)

        if version_of_root:
            metadata["version_of"] = version_of_root
            metadata["replaced_document_id"] = replaced_doc_id

        doc = models.Document(
            project_id=self.task.project_id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            text=text,
            document_name=file.file_name,
            preprocessing_config_id=self.config.id,
            meta_data=metadata,
            is_latest=True,
            version_of=version_of_root,
        )
        self.db.add(doc)
        return doc

    def _get_or_create_document(
        self,
        *,
        file: models.File,
        file_task: models.FilePreprocessingTask,
        text: str,
        document_name: str,
        meta_data: dict,
    ) -> models.Document:
        """Get existing document or create new one with versioning.

        Handles re-processing safely by:
        1. Finding ALL existing documents (both latest and archived)
        2. If latest exists: archive it normally
        3. If only archived exists (failed re-process): delete orphans
        4. Create a new latest document

        Uses database-level locking (FOR UPDATE) to prevent race conditions
        when concurrent tasks process the same file with the same config.
        """
        # Sanitize before anything touches the DB: PostgreSQL rejects NUL
        # bytes in text/varchar columns, and document_name is String(500) —
        # a case ID from a wrongly-selected column can be arbitrarily long
        # and would otherwise fail the whole batch commit with a DataError.
        text = _strip_nul(text)
        document_name = _strip_nul(document_name)[:500]

        # Use database-level locking to prevent race conditions
        max_retries = 3
        retry_delay = 0.1  # seconds

        for attempt in range(max_retries):
            try:
                # Lock existing rows FOR UPDATE to prevent concurrent modifications
                all_existing_docs = (
                    self.db.query(models.Document)
                    .filter(
                        models.Document.original_file_id == file.id,
                        models.Document.preprocessing_config_id == self.config.id,
                        models.Document.document_name == document_name,
                    )
                    .with_for_update(nowait=True)
                    .all()
                )
                break  # Lock acquired successfully
            except OperationalError as e:
                # Lock conflict - another transaction is modifying these documents
                logger.warning(
                    "Document versioning lock conflict for file %s (attempt %d/%d): %s",
                    file.file_name,
                    attempt + 1,
                    max_retries,
                    e,
                )
                if attempt == max_retries - 1:
                    # All retries exhausted - check if documents already exist
                    # and return existing latest if found (idempotent behavior)
                    all_existing_docs = (
                        self.db.query(models.Document)
                        .filter(
                            models.Document.original_file_id == file.id,
                            models.Document.preprocessing_config_id == self.config.id,
                            models.Document.document_name == document_name,
                        )
                        .all()
                    )
                    latest_docs = [d for d in all_existing_docs if d.is_latest]
                    if latest_docs:
                        logger.info(
                            "Returning existing document for file %s after lock contention",
                            file.file_name,
                        )
                        return latest_docs[0]
                    # Re-raise if no existing document to return
                    raise
                import time

                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff

        # Separate latest from archived
        latest_docs = [d for d in all_existing_docs if d.is_latest]

        # Determine version_of for the new document
        version_of_root = None
        replaced_doc_id = None

        # The unique constraint on (file, config, name) only applies when
        # is_latest=True, so we can have unlimited archived versions.
        # Simply archive all latest documents, then create the new version.

        # Archive latest documents
        if latest_docs:
            first_latest = latest_docs[0]
            version_of_root = first_latest.version_of or first_latest.id
            replaced_doc_id = first_latest.id

            # Archive all latest documents (usually just one)
            for doc in latest_docs:
                doc.document_sets.clear()
                doc.is_latest = False
                doc.updated_at = datetime.datetime.now(datetime.UTC)
                # Preserve version_of or point to root
                if version_of_root:
                    doc.version_of = version_of_root
            self.db.flush()

        # Create new document version
        doc_meta_data = meta_data.copy()
        if version_of_root:
            doc_meta_data["version_of"] = version_of_root
            doc_meta_data["replaced_document_id"] = replaced_doc_id

        doc = models.Document(
            project_id=self.task.project_id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            text=text,
            document_name=document_name,
            preprocessing_config_id=self.config.id,
            meta_data=doc_meta_data,
            is_latest=True,
            version_of=version_of_root,
        )
        self.db.add(doc)
        return doc

    def _mistral_ocr_usable(self) -> bool:
        """Whether Mistral OCR can actually run for this task.

        Mirrors the credential resolution in :meth:`_process_with_mistral_ocr`:
        the engine is usable when the global toggle is on *and* an API key is
        available (per-task additional_settings / task_metadata take priority,
        then the server-level ``MISTRAL_API_KEY``). This exists separately from
        the ``MISTRAL_OCR_ENABLED`` flag because a run can be fully configured
        per-task while the global toggle is off — the old gate blocked such runs
        at routing time with a misleading "disabled" error before the processing
        method (which would have found the key) was ever reached.
        """
        if not settings.MISTRAL_OCR_ENABLED:
            return False
        additional = self.config.additional_settings or {}
        api_key = None
        if self.task.task_metadata:
            api_key = self.task.task_metadata.get("mistral_api_key")
        if not api_key:
            api_key = additional.get("mistral_api_key")
        if not api_key:
            api_key = settings.MISTRAL_API_KEY
        return bool(api_key)

    def _llm_vision_ocr_usable(self) -> bool:
        """Whether the Vision LLM OCR engine can actually run for this task.

        Mirrors the credential resolution in :meth:`_process_with_llm_vision_ocr`:
        per-task ``vision_api_key`` / ``vision_base_url`` take priority, then the
        server-level ``VISION_OCR_*`` config, then the pipeline-level OpenAI
        client (``self.client``). Returns True only when both an API key and a
        base URL can be resolved — the same condition the processing method
        enforces before it will run. See :meth:`_mistral_ocr_usable` for why
        this is checked separately from ``VISION_OCR_ENABLED``.
        """
        if not settings.VISION_OCR_ENABLED:
            return False
        additional = self.config.additional_settings or {}
        api_key = additional.get("vision_api_key") or settings.VISION_OCR_API_KEY or ""
        base_url = (
            additional.get("vision_base_url") or settings.VISION_OCR_API_BASE or ""
        )
        if not api_key and self.client:
            api_key = self.client.api_key or ""
        if not base_url and self.client:
            base_url = str(self.client.base_url)
        return bool(api_key and base_url)

    def _process_with_mistral_ocr(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document]:
        """Process file using Mistral OCR API."""
        from ..services.mistral_ocr_service import MistralOCRError, MistralOCRService

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

        model = additional.get("mistral_model", settings.MISTRAL_OCR_MODEL)
        base_url = settings.MISTRAL_API_BASE

        # Pass retry settings from config
        service = MistralOCRService(
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_retries=settings.MISTRAL_OCR_MAX_RETRIES,
        )
        file_content = get_file(file.file_uuid)
        try:
            result = service.process(file_content)
        except MistralOCRError as e:
            # Raw provider errors can carry endpoint/response internals —
            # error-log them and surface only the category + error id.
            raise ValueError(internal_error_message(e, prefix="Mistral OCR failed"))

        doc = self._get_or_create_document(
            file=file,
            file_task=file_task,
            text=result.text,
            document_name=file.file_name,
            meta_data={
                "file_type": file.file_type,
                "ocr_engine": "mistral_ocr",
                "ocr_applied": True,
                "extraction_method": "mistral_ocr",
                "model": model,
                "mistral_model": model,
            },
        )
        return [doc]

    def _process_with_llm_vision_ocr(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document]:
        """Process file using a Vision LLM API."""
        from ..services.llm_vision_ocr_service import (
            LLMVisionOCRError,
            LLMVisionOCRService,
        )

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

        # Validate a user-supplied custom endpoint against the SSRF policy AND the
        # operator egress allowlist. System defaults (VISION_OCR_API_BASE) and
        # self.client.base_url (already validated in __init__) are trusted; only
        # the per-config vision_base_url from additional_settings is
        # user-controlled. The dispatch endpoint only enforces the allowlist on
        # the top-level task base_url, so without this check a user could route
        # patient page images to any non-metadata host via vision_base_url,
        # bypassing ALLOWED_OCR_ENDPOINTS. This is the actual egress point, so
        # enforcing here closes the hole regardless of how the config was created.
        if additional.get("vision_base_url"):
            base_url = validate_user_endpoint(base_url)
            enforce_endpoint_allowlist(base_url, settings.ALLOWED_OCR_ENDPOINTS)

        if not api_key or not base_url:
            raise ValueError(
                "Vision LLM API key and base URL are required for llm_vision engine. "
                "Set them in Additional Settings (vision_api_key, vision_base_url) "
                "or configure VISION_OCR_API_KEY / VISION_OCR_API_BASE in server settings."
            )

        model = additional.get("vision_model") or settings.VISION_OCR_MODEL or "gpt-4o"
        prompt = additional.get("vision_prompt") or settings.VISION_OCR_PROMPT
        max_image_dim = additional.get("vision_max_image_dim", 2048)

        # Pass retry settings and concurrency from config. Use the service as a
        # context manager so its OpenAI/httpx client is closed after use (this
        # method runs per file; leaking the client accumulates connection pools).
        file_content = get_file(file.file_uuid)
        is_pdf = file.file_type == models.FileType.APPLICATION_PDF
        try:
            with LLMVisionOCRService(
                api_key=api_key,
                base_url=base_url,
                model=model,
                prompt=prompt,
                max_image_dim=max_image_dim,
                max_retries=settings.VISION_OCR_MAX_RETRIES,
                max_concurrency=settings.VISION_OCR_MAX_CONCURRENT_FILES,
            ) as service:
                result = service.process(file_content, is_pdf=is_pdf)
        except LLMVisionOCRError as e:
            # Raw provider errors can carry endpoint/response internals —
            # error-log them and surface only the category + error id.
            raise ValueError(internal_error_message(e, prefix="Vision LLM OCR failed"))

        # Surface partial failures as warnings on the file task. The per-page
        # error strings come straight from the provider and can leak
        # endpoint/internal detail — store them in the error log and show
        # only a safe summary with the error id.
        if result.failed_pages > 0:
            safe_summary = operational_error_message(
                detail="; ".join(str(err) for err in result.errors)[:2000],
                prefix=(
                    f"{result.failed_pages} of {result.total_pages} page(s) failed OCR"
                ),
            )
            self._add_file_task_warnings(
                file_task,
                [safe_summary],
                failed_pages=result.failed_pages,
                total_pages=result.total_pages,
            )

        doc = self._get_or_create_document(
            file=file,
            file_task=file_task,
            text=result.text,
            document_name=file.file_name,
            meta_data={
                "file_type": file.file_type,
                "ocr_engine": "llm_vision",
                "ocr_applied": True,
                "extraction_method": "llm_vision_ocr",
                "model": model,
                "vision_model": model,
            },
        )
        return [doc]

    def _detect_csv_encoding(self, file_content: bytes, fallback_chain: str) -> str:
        """Detect CSV encoding using chardet or fallback chain.

        Args:
            file_content: Raw CSV file bytes.
            fallback_chain: Comma-separated list of encodings to try.

        Returns:
            Detected or first successful encoding from fallback chain.
        """
        encoding = detect_text_encoding(
            file_content,
            fallback_chain,
            use_chardet=settings.CSV_DETECT_ENCODING,
        )
        logger.info("Using encoding %s for CSV/text content", encoding)
        return encoding

    def _read_excel(
        self, file: models.File, file_content: bytes, **read_kwargs
    ) -> pd.DataFrame:
        """Read an Excel file, translating engine errors into clear messages.

        Legacy .xls files need the ``xlrd`` engine, which is not installed —
        pandas surfaces that as a bare ImportError that would reach the user
        as an opaque internal failure.
        """
        try:
            return pd.read_excel(io.BytesIO(file_content), **read_kwargs)
        except ImportError as e:
            logger.info("Excel engine unavailable for %s: %s", file.file_name, e)
            raise ValueError(
                f"Cannot read {file.file_name}: legacy Excel (.xls) files are "
                "not supported. Save the file as .xlsx and re-upload."
            )

    def _add_file_task_warnings(
        self,
        file_task: models.FilePreprocessingTask,
        messages: List[str],
        **extra: Any,
    ) -> None:
        """Merge warning messages into ``file_task.warnings``.

        Merging (rather than assigning a fresh dict) keeps earlier warnings —
        e.g. a password-protected-PDF notice — from being clobbered by later
        ones like per-page OCR failures.
        """
        warnings = dict(file_task.warnings or {})
        merged = list(warnings.get("messages", []))
        merged.extend(messages)
        warnings["messages"] = merged
        for key, value in extra.items():
            warnings[key] = value
        file_task.warnings = warnings

    def _process_table_file(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document]:
        """Process CSV/Excel files using file metadata.

        Includes encoding detection with fallback chain for CSV files.
        """
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
                # Detect encoding with fallback chain
                encoding = self._detect_csv_encoding(
                    file_content,
                    settings.CSV_ENCODING_FALLBACK_CHAIN,
                )
                try:
                    df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
                except Exception as e:
                    # Try with errors='replace' if encoding detection failed
                    logger.warning(
                        "CSV read with %s failed: %s, retrying with errors='replace'",
                        encoding,
                        e,
                    )
                    file_content_str = file_content.decode(
                        encoding, errors="replace"
                    ).encode("utf-8")
                    df = pd.read_csv(io.BytesIO(file_content_str), encoding="utf-8")
            else:
                # Honor the sheet chosen in the import config — validation and
                # preview read it, so the pipeline must too (defaulting to the
                # first sheet would silently process different data than the
                # user validated).
                sheet = (file.file_metadata or {}).get("sheet")
                df = self._read_excel(
                    file, file_content, sheet_name=sheet if sheet else 0
                )

            # Check row limit
            if len(df) > self.MAX_ROWS_PER_FILE:
                raise ValueError(
                    f"File {file.file_name} has {len(df)} rows, exceeding the maximum limit of {self.MAX_ROWS_PER_FILE}"
                )

            # An empty table would produce a junk "Empty DataFrame" document
            # that gets sent to the LLM — fail with a clear message instead.
            if df.empty:
                raise ValueError(f"File {file.file_name} contains no data rows.")

            # Convert entire dataframe to text
            text = df.to_string()

            doc = self._get_or_create_document(
                file=file,
                file_task=file_task,
                text=text,
                document_name=file.file_name,
                meta_data={
                    "file_type": "table",
                    "preprocessing_strategy": "full_document",
                    "total_rows": len(df),
                    "columns": [str(c) for c in df.columns],
                    "detected_encoding": encoding
                    if file.file_type == models.FileType.TEXT_CSV
                    else None,
                },
            )
            documents.append(doc)

        elif strategy == models.PreprocessingStrategy.ROW_BY_ROW:
            # Get settings from file_metadata
            file_metadata = file.file_metadata

            # Extract settings
            delimiter = file_metadata.get("delimiter", ",")
            user_encoding = file_metadata.get("encoding", "utf-8")
            has_header = file_metadata.get("has_header", True)
            text_columns = file_metadata.get("text_columns", [])
            case_id_column = file_metadata.get("case_id_column")

            # Read file based on type
            if file.file_type == models.FileType.TEXT_CSV:
                # Detect encoding with fallback chain, respecting user selection
                if settings.CSV_DETECT_ENCODING:
                    encoding = self._detect_csv_encoding(
                        file_content,
                        f"{user_encoding},{settings.CSV_ENCODING_FALLBACK_CHAIN}",
                    )
                else:
                    encoding = user_encoding

                try:
                    df = pd.read_csv(
                        io.BytesIO(file_content),
                        encoding=encoding,
                        delimiter=delimiter,
                        header=0 if has_header else None,
                    )
                except Exception as e:
                    # Try with errors='replace' if encoding detection failed
                    logger.warning(
                        "CSV read with %s failed: %s, retrying with errors='replace'",
                        encoding,
                        e,
                    )
                    file_content_str = file_content.decode(
                        encoding, errors="replace"
                    ).encode("utf-8")
                    df = pd.read_csv(
                        io.BytesIO(file_content_str),
                        encoding="utf-8",
                        delimiter=delimiter,
                        header=0 if has_header else None,
                    )
            else:
                # Same sheet the import config was validated/previewed against.
                sheet = file_metadata.get("sheet")
                df = self._read_excel(
                    file,
                    file_content,
                    header=0 if has_header else None,
                    sheet_name=sheet if sheet else 0,
                )

            # Check row limit
            if len(df) > self.MAX_ROWS_PER_FILE:
                raise ValueError(
                    f"File {file.file_name} has {len(df)} rows, exceeding the maximum limit of {self.MAX_ROWS_PER_FILE}"
                )

            if df.empty:
                raise ValueError(f"File {file.file_name} contains no data rows.")

            # Validate columns exist
            missing_columns = [col for col in text_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(
                    f"Text columns {missing_columns} not found in file {file.file_name}. "
                    f"Available columns: {list(df.columns)}"
                )

            # Check for duplicate case IDs
            self._check_duplicate_case_ids(file, df)

            # Create an auto-generated document set for this file's row-by-row documents
            document_set = self._create_row_by_row_document_set(
                file, df, case_id_column
            )
            documents_set_created = document_set is not None
            # Link the run's file task to its auto-generated set so the UI can
            # deep-link to the group viewer. The set was flushed on creation, so
            # its id is available here.
            if documents_set_created:
                file_task.document_set_id = document_set.id

            # Process rows in batches
            batch_documents = []
            total_rows = len(df)
            # Track documents already added to the set with an O(1) set lookup
            # instead of ``doc not in document_set.documents`` (which is O(n)
            # per row → O(n²) over a large CSV). Uses ORM identity hashing, so
            # it does not depend on the document's PK being flushed.
            added_docs: set[models.Document] = set()
            # Throttle the cancellation check: check_cancelled() does a DB
            # round-trip (db.refresh), so calling it per row caused one query
            # per row (e.g. 100k queries for a 100k-row CSV). Checking every
            # N rows keeps cancellation responsive without saturating the DB.
            cancel_check_interval = 100
            row_counter = 0
            skipped_empty_rows = 0

            for idx, row in df.iterrows():
                row_idx = int(
                    cast(Any, idx)
                )  # pandas yields a Hashable index; coerce to int
                row_counter += 1
                if row_counter % cancel_check_interval == 0 and self.check_cancelled():
                    break

                # Build document content from specified columns
                content_parts = []
                for col in text_columns:
                    value = row[col]
                    if pd.notna(value):  # Skip NaN values
                        content_parts.append(str(value))

                content = " ".join(content_parts)

                # Skip empty documents (count them so the file task can
                # surface the skipped rows as a warning instead of silently
                # dropping data)
                if not content.strip():
                    skipped_empty_rows += 1
                    continue

                # Build document name using case_id_column if specified.
                # _check_duplicate_case_ids already rejected empty/NaN IDs;
                # the pd.notna guard is belt-and-braces.
                case_id = None
                if case_id_column and case_id_column in row:
                    if pd.notna(row[case_id_column]):
                        case_id = _case_id_str(row[case_id_column])
                if case_id:
                    doc_name = case_id
                else:
                    # Bound the filename part well below document_name's 500-char
                    # limit — if truncation happened at the full name instead,
                    # every row of a long-named file would collapse to the same
                    # document name and silently version-replace each other.
                    doc_name = f"{file.file_name[:400]}_row_{idx}"

                # Create or update document (idempotent)
                doc = self._get_or_create_document(
                    file=file,
                    file_task=file_task,
                    text=content,
                    document_name=doc_name,
                    meta_data={
                        "row_index": row_idx,  # Convert numpy int to Python int
                        "source_columns": text_columns,
                        "case_id": case_id,
                        "file_type": "table",
                        "preprocessing_strategy": "row_by_row",
                        # Store full row for reference; sanitize so pandas
                        # types (Timestamp, numpy scalars, NaT) don't break
                        # the JSON serialization of meta_data at commit time.
                        "all_row_data": _json_safe(row.to_dict()),
                    },
                )

                # Add document to the auto-generated set (O(1) membership check)
                if documents_set_created and doc not in added_docs:
                    document_set.documents.append(doc)
                    added_docs.add(doc)

                batch_documents.append(doc)

                # Commit in batches for performance
                if len(batch_documents) >= self.BATCH_SIZE:
                    self.db.commit()
                    documents.extend(batch_documents)
                    batch_documents = []

                    # Update progress
                    file_task.progress = (row_idx + 1) / total_rows * 100
                    self.db.commit()

            # Save remaining documents
            if batch_documents:
                self.db.commit()
                documents.extend(batch_documents)

            if skipped_empty_rows:
                self._add_file_task_warnings(
                    file_task,
                    [
                        f"Skipped {skipped_empty_rows} row(s) with empty values "
                        "in the selected text columns."
                    ],
                    skipped_rows=skipped_empty_rows,
                )

            # All rows skipped → the file "succeeding" with zero documents
            # would look identical to a fully processed one. Fail explicitly.
            if not documents and not self.cancelled:
                raise ValueError(
                    f"No documents were created from {file.file_name}: all "
                    f"{total_rows} row(s) have empty values in the selected "
                    f"text columns {text_columns}."
                )

        else:
            raise ValueError(f"Unsupported preprocessing strategy: {strategy}")

        return documents

    def _process_text_file(
        self, file: models.File, file_task: models.FilePreprocessingTask
    ) -> List[models.Document]:
        """Process plain text files."""
        file_content = get_file(file.file_uuid)

        # Decode text content: try strict UTF-8 first, then the same
        # detection/fallback chain used for CSVs. Decoding e.g. a UTF-16 or
        # Latin-1 file blindly as UTF-8 with errors="replace" produces
        # NUL-riddled mojibake instead of the actual text.
        encoding = "utf-8"
        try:
            text = file_content.decode("utf-8")
        except UnicodeDecodeError:
            encoding = self._detect_csv_encoding(
                file_content, settings.CSV_ENCODING_FALLBACK_CHAIN
            )
            text = file_content.decode(encoding, errors="replace")
        # Strip a BOM so it doesn't leak into the document text
        text = text.lstrip("\ufeff")

        # Create or update document (idempotent)
        doc = self._get_or_create_document(
            file=file,
            file_task=file_task,
            text=text,
            document_name=file.file_name,
            meta_data={"file_type": "text", "detected_encoding": encoding},
        )

        return [doc]

    def _create_row_by_row_document_set(
        self, file: models.File, df, case_id_column: str | None
    ) -> models.DocumentSet | None:
        """Create an auto-generated DocumentSet for row-by-row documents from a single file.

        Args:
            file: The file model being processed.
            df: The pandas DataFrame with the file's data.
            case_id_column: The case ID column name (if any).

        Returns:
            The created DocumentSet, or None if creation failed.
        """
        try:
            # Build a descriptive name for the document set. DocumentSet.name
            # is String(100) — truncate (before the existence lookup, so the
            # query and the insert agree) or a long filename fails the flush
            # and poisons the session for the rest of the file.
            if case_id_column:
                set_name = f"{file.file_name} (by {case_id_column})"[:100]
            else:
                set_name = f"{file.file_name} (row-by-row)"[:100]

            # Check if an auto-generated set already exists for this file + config
            existing_set = (
                self.db.query(models.DocumentSet)
                .filter(
                    models.DocumentSet.project_id == self.task.project_id,
                    models.DocumentSet.name == set_name,
                    models.DocumentSet.is_auto_generated,
                    models.DocumentSet.preprocessing_config_id == self.config.id,
                )
                .first()
            )

            if existing_set:
                logger.info(
                    "Document set already exists for row-by-row file %s: %s",
                    file.file_name,
                    set_name,
                )
                return existing_set

            # Create new document set (description is String(500))
            description = (
                f"Auto-generated document set for row-by-row preprocessing of {file.file_name}. "
                f"Contains {len(df)} documents extracted from individual rows."
            )[:500]

            document_set = models.DocumentSet(
                project_id=self.task.project_id,
                name=set_name,
                description=description,
                is_auto_generated=True,
                preprocessing_config_id=self.config.id,
                tags=["row-by-row", "auto-generated", file.file_name],
            )

            self.db.add(document_set)
            self.db.flush()  # Get the ID before committing

            logger.info(
                "Created auto-generated document set '%s' for file %s",
                set_name,
                file.file_name,
            )

            return document_set

        except Exception as e:
            logger.warning(
                "Failed to create document set for row-by-row file %s: %s",
                file.file_name,
                e,
            )
            return None


def process_files_with_config(task_id: int, db: Session):
    """Entry point for processing files with configuration."""
    pipeline = PreprocessingPipeline(db, task_id)
    pipeline.process()
