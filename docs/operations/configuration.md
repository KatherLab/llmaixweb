# Configuration

LLMAIx Web is configured through **environment variables**, read from an `.env`
file (path set by `ENV_PATH`, defaults to `backend/.env`) or the process
environment.

!!! info "Authoritative reference"
    [`.env.example`](https://github.com/KatherLab/llmaixweb/blob/main/.env.example)
    documents **every** available setting with descriptions and defaults. This
    page covers the ones that matter most; consult `.env.example` for the full,
    up-to-date list.

## Essential settings

At minimum, configure your LLM provider and a secret key.

| Variable | Description | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | API key for the LLM provider | (empty)\* |
| `OPENAI_API_BASE` | Base URL for the OpenAI-compatible API | (empty) |
| `OPENAI_API_MODEL` | Default model to use | (empty) |
| `SECRET_KEY` | Secret for sessions (`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`) | **required** |

!!! note
    \* The app **starts without an LLM key** (the shipped `.env.example` sets
    `OPENAI_NO_API_CHECK=true`). A key is only needed to run extraction trials,
    and can be provided here, in the admin panel, or per-trial. `SECRET_KEY` is
    the only truly mandatory value — the backend refuses to start without it.

## Storage

**RustFS** (S3-compatible, the docker-compose default):

| Variable | Default |
| --- | --- |
| `AWS_ACCESS_KEY_ID` | `rustfsadmin` |
| `AWS_SECRET_ACCESS_KEY` | `rustfsadmin` |
| `S3_ENDPOINT_URL` | `http://rustfs:9000` |
| `S3_BUCKET_NAME` | `llmaixweb` |

**Local filesystem** (alternative):

| Variable | Description |
| --- | --- |
| `LOCAL_DIRECTORY` | Path to the local storage directory |

## Access, auth & security

| Variable | Description | Default |
| --- | --- | --- |
| `APP_URL` | Public app URL (used for email links) | `http://localhost:5173` |
| `BACKEND_CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:5173` |
| `REQUIRE_INVITATION` | Require an invitation to sign up | `false` (compose); code default `true` |
| `ALLOW_FIRST_ADMIN_SETUP` | Let the first user become admin | `true` |
| `PASSWORD_POLICY_*` | Password complexity (length, upper/lower/digit/symbol) | min 8; upper/lower/digit |
| `LOGIN_MAX_ATTEMPTS` | Failed logins before lockout | `5` |
| `LOGIN_LOCKOUT_MINUTES` | Lockout duration | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh-token lifetime (rotatable, revocable) | `30` |
| `ADMIN_ALL_PROJECT_ACCESS` | Let admins access all projects | `false` |

## Single sign-on (OIDC)

| Variable | Description | Default |
| --- | --- | --- |
| `SSO_ENABLED` | Enable OpenID Connect single sign-on | `false` |
| `SSO_JIT_DEFAULT_ROLE` | Role for auto-provisioned SSO users | `user` |
| `SSO_BYPASS_INVITATION` | SSO login bypasses `REQUIRE_INVITATION` | `true` |

See [SSO administration](../admin/sso.md) for the provider setup.

## OCR engines

| Variable | Description | Default |
| --- | --- | --- |
| `MISTRAL_API_BASE` | Mistral OCR API base URL | `https://api.mistral.ai` |
| `MISTRAL_API_KEY` | Mistral OCR API key (server default) | (empty) |
| `MISTRAL_OCR_ENABLED` | Enable the Mistral OCR engine | `false` |
| `VISION_OCR_ENABLED` | Enable the Vision LLM OCR engine | `false` |
| `VISION_OCR_API_KEY` | Vision OCR API key (server default) | (empty) |
| `VISION_OCR_API_BASE` | Vision OCR API base URL | (empty) |
| `VISION_OCR_MODEL` | Vision OCR default model | `gpt-4o` |
| `DOCLING_LOCAL_FALLBACK` | Run Docling locally if docling-serve is down | `false` |

See [OCR engines](../user-guide/ocr-engines.md) for what each engine does.

!!! tip "Self-hosted OCR"
    Use `compose.deepseek.yml` for a local Mistral-compatible API (DeepSeek-OCR-2
    via [KatDocExtract](https://github.com/KatherLab/KatDocExtract)) or
    `compose.vllm.yml` for a local vision LLM, then point `MISTRAL_API_BASE` /
    `VISION_OCR_API_BASE` at them.

## Background processing

| Variable | Description | Default |
| --- | --- | --- |
| `CELERY_PREPROCESS_POOL` | Pool type (`auto`, `solo`, `prefork`) | `auto` (use `solo` on macOS) |
| `DISABLE_CELERY` | Disable Celery workers (run tasks synchronously) | `false` |
| `INITIALIZE_CELERY` | Spawn in-process Celery workers on startup | `false` (compose runs worker containers); code default `true` |
| `SKIP_RUNTIME_CHECKS` | Bypass OpenAI/S3 validation (used for Alembic) | `false` |

<details>
<summary>Database & advanced settings</summary>

| Variable | Description | Default |
| --- | --- | --- |
| `POSTGRES_SERVER` | Database host | `postgres` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `postgres` |
| `POSTGRES_DB` | Database name | `llmaixweb` |
| `CELERY_BROKER_URL` | Redis broker URL | `redis://redis:6379/0` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token expiry (minutes) — short-lived, paired with refresh tokens | `60` |
| `RUSTFS_ACCESS_KEY` | RustFS access key | `rustfsadmin` |
| `RUSTFS_SECRET_KEY` | RustFS secret key | `rustfsadmin` |

</details>

## Local network & reverse proxy

The frontend nginx proxies `/api/` requests to the backend, so only one URL is
needed. `APP_URL` controls invitation / password-reset link construction.

!!! note "Accessing from other devices on your network"
    1. Set `APP_URL` to your server IP (e.g. `http://192.168.1.100:5173`).
    2. Add that origin to `BACKEND_CORS_ORIGINS`.
    3. Restart the stack.

    **Behind a reverse proxy** (nginx, Traefik, …), set `APP_URL` and
    `BACKEND_CORS_ORIGINS` to your public domain (e.g. `https://app.example.com`).
    For TLS and full production setup, see [Deployment](deployment.md).

## Frontend runtime configuration

The frontend reads its API base URL from `window.__APP_CONFIG__` (injected in
Docker) with a build-time `VITE_*` fallback, so the same frontend image can point
at different backends without rebuilding.

## Runtime overrides

Some settings can also be changed at runtime from the admin
[System settings](../admin/settings.md) panel; those overrides are stored in the
database and take precedence over the environment. Settings marked read-only can
only be set via the environment.
