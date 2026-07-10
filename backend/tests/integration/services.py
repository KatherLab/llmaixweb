"""Ephemeral Redis + PostgreSQL services for Celery integration tests.

Two ways to provide the services:

1. Externally (CI): set ``TEST_REDIS_URL`` and ``TEST_DATABASE_URL`` (e.g. from
   GitHub Actions ``services:`` containers). :func:`resolve_services` returns
   them and starts/stops nothing.
2. Locally: if those env vars are unset but a container runtime (podman or
   docker) is available, :func:`resolve_services` starts throwaway Redis +
   Postgres containers on high ports (so they don't collide with a running dev
   stack) and tears them down afterwards.

If neither is available, returns ``None`` so the caller can ``pytest.skip``.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass


@dataclass
class Services:
    redis_url: str
    database_url: str


def _container_cli() -> str | None:
    for cli in ("podman", "docker"):
        if shutil.which(cli):
            return cli
    return None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_tcp(host: str, port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with contextlib.suppress(OSError):
            with socket.create_connection((host, port), timeout=1):
                return True
        time.sleep(0.3)
    return False


@contextlib.contextmanager
def running_services():
    """Yield :class:`Services`, or ``None`` if none can be provided.

    Use as a context manager so any containers we start are removed on exit.
    """
    ext_redis = os.environ.get("TEST_REDIS_URL")
    ext_db = os.environ.get("TEST_DATABASE_URL")
    if ext_redis and ext_db:
        yield Services(redis_url=ext_redis, database_url=ext_db)
        return

    cli = _container_cli()
    if not cli:
        yield None
        return

    redis_name = "llmaix-itest-redis"
    pg_name = "llmaix-itest-pg"
    redis_port = _free_port()
    pg_port = _free_port()
    started: list[str] = []

    def _rm(name: str) -> None:
        with contextlib.suppress(Exception):
            subprocess.run(
                [cli, "rm", "-f", name],
                check=False,
                capture_output=True,
                timeout=30,
            )

    try:
        _rm(redis_name)
        _rm(pg_name)

        subprocess.run(
            [
                cli,
                "run",
                "-d",
                "--rm",
                "--name",
                redis_name,
                "-p",
                f"{redis_port}:6379",
                "redis:7",
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        started.append(redis_name)
        subprocess.run(
            [
                cli,
                "run",
                "-d",
                "--rm",
                "--name",
                pg_name,
                "-e",
                "POSTGRES_USER=postgres",
                "-e",
                "POSTGRES_PASSWORD=postgres",
                "-e",
                "POSTGRES_DB=llmaix_itest",
                "-p",
                f"{pg_port}:5432",
                "postgres:16",
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        started.append(pg_name)

        if not _wait_tcp("127.0.0.1", redis_port) or not _wait_tcp(
            "127.0.0.1", pg_port
        ):
            raise RuntimeError("services did not become reachable in time")
        # Postgres accepts TCP a moment before it's ready for queries.
        _wait_pg_ready(cli, pg_name)

        yield Services(
            redis_url=f"redis://127.0.0.1:{redis_port}/0",
            database_url=(
                f"postgresql+psycopg://postgres:postgres@127.0.0.1:{pg_port}/llmaix_itest"
            ),
        )
    finally:
        for name in started:
            _rm(name)


def _wait_pg_ready(cli: str, name: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = subprocess.run(
            [cli, "exec", name, "pg_isready", "-U", "postgres"],
            capture_output=True,
            timeout=10,
        )
        if res.returncode == 0:
            return
        time.sleep(0.4)
    raise RuntimeError("postgres did not become ready")
