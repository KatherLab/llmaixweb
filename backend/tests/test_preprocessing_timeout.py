# backend/tests/test_preprocessing_timeout.py
"""`_process_with_timeout` failure/latency behavior.

Regression: a file whose processing function raises quickly (e.g. a validation
error like duplicate case IDs or missing text columns) used to surface the error
only after the full per-file timeout elapsed — because the worker thread reported
failures on a separate queue that the poller only drained at the deadline. A
fast-failing file therefore looked like it "processed" for minutes. The worker now
wakes the poller immediately, so the exception propagates at once.
"""

import time
import types


def _bare_pipeline():
    """A pipeline instance without the DB-touching __init__.

    ``_process_with_timeout`` only needs ``self._timeout_abort`` (read by the
    worker thread) plus ``file.file_name`` / ``file_task.id`` on its arguments;
    the DB-backed heartbeat is only reached while a file is genuinely still
    running, which the fast paths below never hit. Imported lazily (not at module
    top level) so config/DB env set up by conftest fixtures is in place first.
    """
    from ..src.utils.preprocessing import PreprocessingPipeline

    pipeline = PreprocessingPipeline.__new__(PreprocessingPipeline)
    pipeline._timeout_abort = False
    return pipeline


def _fake_file_and_task():
    file = types.SimpleNamespace(file_name="side_medication.xlsx")
    file_task = types.SimpleNamespace(id=123)
    return file, file_task


def test_fast_worker_exception_surfaces_immediately():
    """A quick failure must raise now, not after `timeout_seconds`."""
    pipeline = _bare_pipeline()
    file, file_task = _fake_file_and_task()

    def boom(_file, _file_task):
        raise ValueError("Duplicate case IDs found in column 'Subject ID'")

    start = time.monotonic()
    try:
        pipeline._process_with_timeout(boom, file, file_task, timeout_seconds=30)
        raise AssertionError("expected ValueError to propagate")
    except ValueError as exc:
        assert "Duplicate case IDs" in str(exc)
    elapsed = time.monotonic() - start

    # The old bug waited out the full 30s timeout; the fix surfaces it at once.
    assert elapsed < 5, f"exception took {elapsed:.1f}s to surface (should be ~instant)"


def test_successful_result_is_returned():
    pipeline = _bare_pipeline()
    file, file_task = _fake_file_and_task()
    sentinel = ["doc-1", "doc-2"]

    def ok(_file, _file_task):
        return sentinel

    assert (
        pipeline._process_with_timeout(ok, file, file_task, timeout_seconds=30)
        is sentinel
    )


def test_genuinely_slow_file_times_out():
    """A file that never finishes still raises TimeoutError at the deadline."""
    pipeline = _bare_pipeline()
    file, file_task = _fake_file_and_task()

    def slow(_file, _file_task):
        time.sleep(5)
        return []

    start = time.monotonic()
    try:
        pipeline._process_with_timeout(slow, file, file_task, timeout_seconds=1)
        raise AssertionError("expected TimeoutError")
    except TimeoutError as exc:
        assert "timeout" in str(exc).lower()
    elapsed = time.monotonic() - start
    # Times out at ~1s, well before the worker's 5s sleep completes.
    assert elapsed < 4, f"timeout took {elapsed:.1f}s (should trip at ~1s)"
