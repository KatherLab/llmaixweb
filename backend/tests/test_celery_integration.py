# backend/tests/test_celery_integration.py
"""Real Redis + Celery + Postgres integration test for chunked preprocessing.

Runs the actual Celery task through a REAL broker and worker (not eager mode),
so it covers what the eager test can't: broker round-trips and the chunked
self-requeue being driven by real Redis messages a real worker consumes.

Services are provided one of two ways (see integration/services.py):
  * CI: set TEST_REDIS_URL + TEST_DATABASE_URL (GitHub Actions ``services:``).
  * Local: set RUN_CELERY_INTEGRATION=1 and have podman/docker installed — the
    harness spins throwaway Redis + Postgres containers on high ports.
Otherwise the test skips (so a plain ``pytest`` never spins containers).
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from .integration.services import _container_cli, running_services

_REPO_ROOT = Path(__file__).resolve().parents[2]

_has_external = bool(
    os.environ.get("TEST_REDIS_URL") and os.environ.get("TEST_DATABASE_URL")
)
_opted_in_local = (
    os.environ.get("RUN_CELERY_INTEGRATION") == "1" and _container_cli() is not None
)

pytestmark = pytest.mark.skipif(
    not (_has_external or _opted_in_local),
    reason=(
        "Celery integration test needs real services. Set TEST_REDIS_URL + "
        "TEST_DATABASE_URL, or RUN_CELERY_INTEGRATION=1 with podman/docker."
    ),
)


def _run_migrations(env: dict) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, (
        f"alembic migration failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_chunked_preprocessing_over_real_broker():
    with running_services() as svc:
        if svc is None:
            pytest.skip("no container runtime / external services available")

        storage = tempfile.mkdtemp(prefix="itest_storage_")
        env = {
            **os.environ,
            "SKIP_RUNTIME_CHECKS": "true",
            "DISABLE_CELERY": "false",
            "OPENAI_NO_API_CHECK": "true",
            "SECRET_KEY": "integration-secret-key-1234567890",
            "CELERY_BROKER_URL": svc.redis_url,
            "SQLALCHEMY_DATABASE_URI": svc.database_url,
            "LOCAL_DIRECTORY": storage,
            "PREPROCESS_CHUNK_SIZE": "2",
            "DOCLING_SERVE_ENABLED": "false",
            "DISABLE_RATE_LIMIT": "true",
        }

        # Real schema via the actual migration chain, then drive real worker+broker.
        _run_migrations(env)
        result = subprocess.run(
            [sys.executable, "-m", "backend.tests.integration.celery_worker_runner"],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0 and "PASS ✅" in result.stdout, (
            f"integration run failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
