# Configuration

LLMAIx Web is configured entirely through **environment variables**, read from
an `.env` file (path set by `ENV_PATH`, defaults to `backend/.env`) or the
process environment.

!!! info "Authoritative reference"
    [`.env.example`](https://github.com/KatherLab/llmaixweb/blob/main/.env.example)
    documents **every** available setting with descriptions and defaults. This
    page groups the most important ones; consult `.env.example` for the full,
    up-to-date list.

## Settings that can also be changed at runtime

Some settings can be overridden at runtime from the admin **[System settings](../admin/settings.md)**
panel; those overrides are stored in the database and take precedence over the
environment. Settings marked read-only can only be set via the environment.

## Categories

- **Core / security** — application secret key, token lifetimes, password
  policy, account lockout. In production the app refuses to start with an
  insecure secret key.
- **Storage** — local directory vs. S3-compatible object storage (endpoint,
  bucket, credentials). Always accessed through the storage abstraction, so the
  same app works with either backend.
- **Database & broker** — PostgreSQL connection and the Redis broker used by
  Celery.
- **LLM & OCR endpoints** — base URLs and API keys for the default extraction
  model, Mistral OCR (`MISTRAL_API_BASE`), and vision-LLM OCR
  (`VISION_OCR_API_BASE`); plus Docling settings including
  `DOCLING_LOCAL_FALLBACK`.
- **Background processing** — Celery pool types (`CELERY_DEV_POOL`,
  `CELERY_PREPROCESS_POOL`) and `DISABLE_CELERY` to run tasks synchronously.
- **Access control** — `ADMIN_ALL_PROJECT_ACCESS` to let admins see all
  projects.
- **Runtime checks** — `SKIP_RUNTIME_CHECKS=true` bypasses OpenAI/S3 validation
  (used for Alembic migrations).

## Frontend runtime configuration

The frontend reads its API base URL from `window.__APP_CONFIG__` (injected in
Docker) with a build-time `VITE_*` fallback, so the same frontend image can
point at different backends without rebuilding.
