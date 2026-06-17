# Developer Guide

## Version Management

This project uses separate versioning for frontend and backend components.

### Version Locations

| Component | Version File                                                                                      | Exposed Via                |
|-----------|---------------------------------------------------------------------------------------------------|----------------------------|
| Frontend  | `package.json` (root) → `frontend/update-version.js` syncs to `frontend/version.js` at build time | Displayed in footer        |
| Backend   | `pyproject.toml` (llmaixweb package)                                                              | `/api/v1/version` endpoint |

### Current Versions

- **Frontend**: `package.json` → `"version": "0.3.3"` (synced to `frontend/version.js` via `prebuild` script)
- **Backend**: `pyproject.toml` → `version = "0.3.3"` (llmaixweb package version)

### Git Commit Hash

Both frontend and backend display their git commit hashes:

- **Frontend**: Injected at build time via `GIT_COMMIT_HASH` build arg
- **Backend**: Read at runtime via `git rev-parse --short HEAD`

**Hover over the version in the footer** to see the commit hash.

### Release Checklist

When making a release:

1. **Update frontend version** in `package.json` (root):
   ```json
   "version": "0.3.3"  // bump version
   ```
   The `prebuild` script (`frontend/update-version.js`) automatically syncs this to `frontend/version.js` at build time.

2. **Update backend version** in `pyproject.toml`:
   ```toml
   [project]
   version = "0.3.3"  // bump version
   ```

3. **Lock dependencies** — run `uv lock` to update `uv.lock` (it tracks the `llmaixweb` version from `pyproject.toml` and will update automatically):
   ```bash
   uv lock
   ```

4. **Build and push images** (handled by GitHub Actions on release tag)

5. **Tag the release** on GitHub:
   ```bash
   git tag v0.3.3
   git push origin v0.3.3
   ```

### Why Separate Versions?

- Frontend and backend are deployed as separate Docker images
- Each can be updated independently
- Users can see both versions in the UI footer to verify their deployment

### Version Display

The application displays both versions in the footer of every page:
```
Frontend Version: 0.3.3 | Backend Version: 0.3.3
```

Hover over each version to see the git commit hash:
```
Frontend Version: 0.3.3 (hover: Commit: abc1234) | Backend Version: 0.3.3 (hover: Commit: def5678)
```

This helps users and support quickly identify version mismatches or outdated components.

---

## Configuration Guide

### Environment Variables

The application is configured via environment variables, loaded from a `.env` file (path controlled by `ENV_PATH`, defaults to `backend/.env`).

#### Quick Start Configuration

For a basic setup, only configure these variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Session secret (min 16 chars) | `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `OPENAI_API_KEY` | API key for LLM provider | `sk-...` |
| `OPENAI_API_BASE` | Base URL for OpenAI-compatible API | `https://api.openai.com/v1` |
| `OPENAI_API_MODEL` | Default model to use | `gpt-4o` |

All other defaults work with `docker compose` out of the box.

#### Full Configuration Reference

See `.env.example` for all available options. Key categories:

| Category | Variables |
|----------|-----------|
| **LLM Provider** | `OPENAI_API_KEY`, `OPENAI_API_BASE`, `OPENAI_API_MODEL`, `OPENAI_NO_API_CHECK` |
| **Security** | `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REQUIRE_INVITATION`, `ALLOW_FIRST_ADMIN_SETUP` |
| **Storage** | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL`, `S3_BUCKET_NAME` OR `LOCAL_DIRECTORY` |
| **Database** | `POSTGRES_SERVER`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `SQLALCHEMY_DATABASE_URI` |
| **Celery** | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `DISABLE_CELERY`, `CELERY_PREPROCESS_POOL` |
| **OCR Engines** | `DOCLING_*`, `MISTRAL_*`, `VISION_OCR_*` |
| **Email/SMTP** | `EMAIL_ENABLED`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, etc. |

### Runtime Settings Override

Admin users can override certain settings at runtime via the Admin Settings UI. These are stored in the `app_settings` database table and cached via LRU cache. Settings marked as `readonly: True` in `SETTINGS_META` (`backend/src/core/config.py`) cannot be overridden.

### Skip Runtime Checks

Set `SKIP_RUNTIME_CHECKS=true` to bypass OpenAI/S3 validation (useful for Alembic migrations):
```bash
SKIP_RUNTIME_CHECKS=true uv run alembic upgrade head
```

---

## Database Migrations (Alembic)

This project uses Alembic for database schema version control and migrations.

> **PostgreSQL is required for any deployment where you plan to run Alembic migrations** (version upgrades, schema changes). Several migrations use operations like `alter_column` and `drop_column` that SQLite does not support. For active development / debugging without migration steps, SQLite can still be used.

### Configuration

- **Config file**: `alembic.ini`
- **Migration scripts**: `alembic/versions/`
- **Environment**: `alembic/env.py` (configured to load DB URL from settings)

### Running Migrations

**Docker Compose**: Migrations run automatically when the backend container starts. No manual intervention needed.

**Local Development**: All migration commands require `SKIP_RUNTIME_CHECKS=true` to bypass OpenAI/S3 validation:

```bash
# Check current database revision
SKIP_RUNTIME_CHECKS=true uv run alembic current

# Show migration history
SKIP_RUNTIME_CHECKS=true uv run alembic history

# Apply all pending migrations
SKIP_RUNTIME_CHECKS=true uv run alembic upgrade head

# Downgrade one version
SKIP_RUNTIME_CHECKS=true uv run alembic downgrade -1

# Downgrade to specific revision
SKIP_RUNTIME_CHECKS=true uv run alembic downgrade <revision_id>
```

### Creating New Migrations

After modifying models in `backend/src/models/`:

```bash
# Auto-generate migration from model changes
SKIP_RUNTIME_CHECKS=true uv run alembic revision --autogenerate --message "description"

# Create empty migration manually
SKIP_RUNTIME_CHECKS=true uv run alembic revision --empty --message "description"
```

Review and edit the generated file in `alembic/versions/` before applying.

### Initial Migration

The initial migration (`alembic/versions/2d2bfbbdcc04_initial.py`) creates all existing tables:
- users, invitations, app_settings
- projects, files, ground_truth
- preprocessing_configurations, prompts, schemas
- document_sets, field_mappings
- preprocessing_tasks, file_preprocessing_tasks
- trials, documents, evaluations, trial_results

---

## Code Style & Linting

This project uses automated formatting and linting for both frontend and backend code.

### Frontend (JavaScript / Vue)

**Prettier** handles code formatting, **ESLint** handles code quality.

| Tool       | What it does                       | Config file            |
|------------|------------------------------------|------------------------|
| Prettier   | Auto-formats JS, Vue, CSS          | `.prettierrc`          |
| ESLint     | Catches errors, enforces Vue rules | `eslint.config.js`     |

**npm scripts** (run from project root):

```bash
npm run format          # Auto-format all frontend files with Prettier
npm run format:check    # Check formatting without changing files
npm run lint            # Lint frontend with ESLint
npm run lint:fix        # Lint + auto-fix where possible
npm run check           # Full check: format:check + lint
```

**Pre-commit hook:** `simple-git-hooks` + `lint-staged` automatically runs `eslint --fix` and `prettier --write` on staged `.js`/`.vue` files before every commit.

**Preferred Prettier settings** (`.prettierrc`):
- No semicolons
- Single quotes
- 2-space indentation
- Trailing commas everywhere
- 100 character print width

### Backend (Python)

**Ruff** handles both formatting and linting for Python code.

```bash
uv run ruff check backend/src/    # Lint
uv run ruff format backend/src/   # Auto-format
```

Ruff configuration lives in `pyproject.toml` under `[tool.ruff]`:
```toml
[tool.ruff]
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Line length - too strict for strings/comments
```

### Pre-Commit Checklist (Before Pushing)

```bash
# Frontend
npm run check
npm run build

# Backend
uv run ruff check backend/src/
uv run ruff format backend/src/ --check
ENV_PATH=backend/.env.localtest uv run pytest --verbose
```

---

## Running Tests

### Backend Tests

```bash
# 1. Copy the example test environment file
cp backend/.env.localtest.example backend/.env.localtest

# 2. Edit backend/.env.localtest with your test settings (e.g., OpenAI API key for integration tests)

# 3. Run tests
ENV_PATH=backend/.env.localtest uv run pytest --verbose --cov=backend --cov-report=html
```

---

## Optional Compose Overlays

The repo ships two optional GPU-requiring compose overlays for self-hosted OCR and LLM inference:

### compose.deepseek.yml — Self-hosted Mistral OCR

Spins up **vLLM** (DeepSeek-OCR-2) + **KatDocExtract** (Mistral OCR-compatible API wrapper).

```bash
docker compose -f compose.yml -f compose.deepseek.yml up -d
```

Then in `.env`, set:
```env
MISTRAL_API_BASE=http://ocr-api:8001
MISTRAL_API_KEY=sk-noop
MISTRAL_OCR_ENABLED=true
```

Override the vLLM model or KatDocExtract port:
```env
VLLM_MODEL=deepseek-ai/DeepSeek-OCR-2
KATDOCEXTRACT_PORT=3001
```

The `ocr-api` service binds to port 3001 by default.

### compose.vllm.yml — Self-hosted vLLM endpoint

Spins up **vLLM** with a model of your choice. Default: `google/gemma-4-E4B-it`.

```bash
docker compose -f compose.yml -f compose.vllm.yml up -d
```

**Use as Vision LLM OCR provider** (in `.env`):
```env
VISION_OCR_ENABLED=true
VISION_OCR_API_BASE=http://vllm:8000/v1
VISION_OCR_API_KEY=sk-noop
VISION_OCR_MODEL=google/gemma-4-E4B-it
```

**Use as main LLM provider** (in `.env`):
```env
OPENAI_API_BASE=http://vllm:8000/v1
OPENAI_API_KEY=sk-noop
OPENAI_API_MODEL=google/gemma-4-E4B-it
OPENAI_NO_API_CHECK=true
```

Override model, tensor parallel size, or max context length:
```env
VLLM_MODEL=google/gemma-4-E4B-it
VLLM_TENSOR_PARALLEL_SIZE=1
VLLM_MAX_MODEL_LEN=32768
VLLM_GPU_MEMORY_UTILIZATION=0.90
```

### Using External APIs Instead

Both OCR paths also work with external (cloud) APIs — no compose overlay needed:

| OCR Engine       | Env Vars to Set                                                  |
|------------------|------------------------------------------------------------------|
| Mistral OCR API  | `MISTRAL_API_BASE=https://api.mistral.ai`, `MISTRAL_API_KEY=...` |
| Vision LLM OCR   | `VISION_OCR_API_BASE=<your-api>`, `VISION_OCR_MODEL=...`         |

The main LLM extraction path also accepts any OpenAI-compatible external API via `OPENAI_API_BASE`, `OPENAI_API_KEY`, and `OPENAI_API_MODEL`.

---

## Email Setup (Optional)

LLMAIx Web can send emails for user invitations and password resets via SMTP.

### Configuration

Set the following environment variables (or configure via Admin Settings UI → Email tab):

| Variable            | Description                                   |
|---------------------|-----------------------------------------------|
| `EMAIL_ENABLED`     | Set to `true` to enable email sending         |
| `SMTP_HOST`         | SMTP server hostname (e.g., `smtp.gmail.com`) |
| `SMTP_PORT`         | SMTP port (587 for STARTTLS, 465 for SSL)     |
| `SMTP_USERNAME`     | SMTP username (may be secret)                 |
| `SMTP_PASSWORD`     | SMTP password / app password (may be secret)  |
| `SMTP_FROM_ADDRESS` | Sender email address                          |
| `SMTP_FROM_NAME`    | Sender display name (default: "LLMAIx Web")   |
| `SMTP_USE_TLS`      | Use STARTTLS (default: `true`)                |

### Behavior When Email is Disabled

- **Invitations**: Created as DB records with tokens — admins copy-paste the invitation link manually (existing behavior)
- **Password Reset**: The request still succeeds (returns generic "check your email" message) but shows a warning that email delivery is not configured

### Email Templates

HTML templates live in `backend/src/templates/emails/`:
- `invitation.html` — invitation link email
- `password_reset.html` — password reset link email

Templates use Jinja2 with inline CSS. Edit them to customize branding or content.

---

## Initialize Users

```bash
python -m backend.scripts.populate_users
```

**When using Docker:**

```bash
# Running stack
docker compose exec -it backend \
  python -m backend.scripts.populate_users

# Stopped stack
docker compose run --rm -it backend \
  python -m backend.scripts.populate_users
```

---

## Local Development Setup

### Backend

```bash
# Create virtual environment with uv
uv venv
source .venv/bin/activate

# Install dependencies
uv sync

# Run backend server
cd backend/src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Requirements:**
- Python 3.13+
- PostgreSQL (or SQLite for development without migrations)
- Redis (for Celery)

### Frontend

```bash
# Install dependencies
npm install

# Run dev server
npm run dev
```

**Requirements:**
- Node.js 18+

### Hot-Reload with Docker

For development with hot-reloading of code changes:

```bash
docker compose -f compose.yml -f compose.dev.yml up -d
```

This mounts local code directories into the containers, so changes are picked up automatically.

---

## Architecture Notes

### Backend Structure

```
backend/src/
├── main.py               # FastAPI app, CORS, Celery worker spawn
├── core/
│   ├── config.py         # Pydantic Settings, lazy loading, validation
│   ├── security.py       # JWT, password hashing, OAuth2
│   └── dynamic_settings.py  # DB-backed runtime settings
├── db/
│   └── session.py        # SQLAlchemy engine, session factory
├── models/
│   └── project.py        # SQLAlchemy ORM models
├── schemas/
│   └── project.py        # Pydantic request/response schemas
├── routers/v1/endpoints/ # API route handlers
│   ├── projects.py       # Main project router with sub-routers
│   ├── files.py
│   ├── preprocessing.py
│   ├── documents.py
│   ├── schemas.py
│   ├── prompts.py
│   ├── trials.py
│   └── ...
├── services/             # External service integrations (OCR)
├── celery/
│   ├── celery_config.py  # Celery app, queues, workers
│   ├── preprocessing.py  # Celery preprocessing tasks
│   └── info_extraction.py # Celery extraction tasks
└── utils/
    ├── preprocessing.py  # PreprocessingPipeline orchestrator
    ├── info_extraction.py # LLM extraction logic
    └── evaluation.py     # Evaluation metrics
```

### Frontend Structure

```
frontend/
├── views/                # Page-level components (routed)
│   ├── Dashboard.vue
│   ├── ProjectOverview.vue
│   ├── ProjectDetail.vue
│   └── ...
├── components/           # Reusable UI components
│   ├── ProjectGrid.vue
│   ├── VisualSchemaEditor.vue
│   ├── CreateTrialModal.vue
│   └── ...
├── stores/               # Pinia state management
│   ├── auth.js
│   └── firstAdmin.js
├── services/             # API client
│   └── api.js
├── router/               # Vue Router config
│   └── index.js
└── utils/                # Helpers, formatters
```

### Key Design Patterns

1. **Lazy Settings Loading**: Settings are loaded lazily on first access to avoid requiring `.env` for operations like Alembic migrations (`core/config.py:_get_settings()`).

2. **Storage Abstraction**: `dependencies.py` provides `get_file()`/`save_file()`/`remove_file()` that work with both local and S3 storage — always use these, never access storage directly.

3. **Cancellation Pattern**: Both `PreprocessingTask` and `Trial` have `is_cancelled` + `rollback_on_cancel` flags. The Celery task checks `is_cancelled` periodically. Rollback deletes produced documents/results.

4. **Embedded Text Shortcut**: For PDFs, Docling is always tried first for embedded text. If insufficient (< 100 chars by default), falls back to configured OCR engine. Set `force_ocr=true` to skip.

5. **Dynamic Settings**: Admin panel changes are stored in `app_settings` DB table and loaded via `dynamic_settings.py` with LRU cache. Only non-readonly settings can be overridden.

---

## Debugging Tips

### Check Service Health

```bash
docker compose ps                    # All services status
docker compose logs backend          # Backend logs
docker compose logs worker_default   # Default queue worker logs
docker compose logs worker_preprocess  # Preprocessing worker logs
```

### Database Inspection

```bash
# Connect to Postgres
docker compose exec postgres psql -U postgres -d llmaixweb

# Check migration status
SKIP_RUNTIME_CHECKS=true uv run alembic current
```

### File Storage

```bash
# RustFS web console (default credentials: rustfsadmin/rustfsadmin)
open http://localhost:9001

# Local storage (if configured)
ls -la $LOCAL_DIRECTORY
```

### Celery Tasks

```bash
# Check Celery task queues (Redis)
docker compose exec redis redis-cli
> keys celery*
> llen celery  # Check default queue length
```
