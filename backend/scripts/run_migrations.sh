#!/bin/bash
set -e

echo "Running database migrations..."

# Run Alembic migrations with SKIP_RUNTIME_CHECKS to bypass OpenAI/S3 validation
export SKIP_RUNTIME_CHECKS=true
uv run alembic upgrade head

echo "Migrations completed. Starting server..."

# Start the application
exec /app/.venv/bin/python -m uvicorn backend.src.main:app --host 0.0.0.0 --port 8000
