#!/bin/bash
set -e

echo "Running database migrations..."

# Run Alembic migrations with SKIP_RUNTIME_CHECKS to bypass OpenAI/S3 validation.
# Scope the flag to this one command only — exporting it would leak into the
# uvicorn process below and disable the SECRET_KEY / storage / OpenAI startup
# guards for the whole server (config.Settings.__init__ returns early).
SKIP_RUNTIME_CHECKS=true uv run --no-dev alembic upgrade head

echo "Migrations completed. Starting server..."

# Start the application (with runtime checks ENABLED — no SKIP_RUNTIME_CHECKS in env)
# UVICORN_RELOAD=true (set by compose.dev.yml) enables hot-reload for the
# code mounted into the container.
UVICORN_ARGS=""
if [ "${UVICORN_RELOAD:-false}" = "true" ]; then
    UVICORN_ARGS="--reload"
fi
exec /app/.venv/bin/python -m uvicorn backend.src.main:app --host 0.0.0.0 --port 8000 $UVICORN_ARGS
