# backend/tests/test_chunking_integration.py
"""CI wrapper for the chunked-preprocessing validation.

The chunked self-requeue logic lives in the Celery task, which the normal test
env can't run (DISABLE_CELERY=True, and the re-enqueue needs the task defined).
`validate_chunking.py` runs it in a subprocess with Celery enabled in EAGER mode
(so the re-enqueue chain executes synchronously) against an isolated SQLite DB.
This test just drives that script and asserts it passes, giving the refactor
real end-to-end coverage in CI.
"""

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_preprocessing_chunked_self_requeue_and_cancel():
    result = subprocess.run(
        [sys.executable, "-m", "backend.tests.validate_chunking"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, (
        f"chunking validation failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "PASS ✅" in result.stdout, result.stdout
