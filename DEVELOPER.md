# Developer Guide

## Version Management

This project uses separate versioning for frontend and backend components.

### Version Locations

| Component | Version File                                                                                      | Exposed Via                |
|-----------|---------------------------------------------------------------------------------------------------|----------------------------|
| Frontend  | `package.json` (root) → `frontend/update-version.js` syncs to `frontend/version.js` at build time | Displayed in footer        |
| Backend   | `pyproject.toml` (llmaixweb package)                                                              | `/api/v1/version` endpoint |

### Current Versions

- **Frontend**: `package.json` → `"version": "0.2.4"` (synced to `frontend/version.js` via `prebuild` script)
- **Backend**: `pyproject.toml` → `version = "0.2.4"` (llmaixweb package version)

### Git Commit Hash

Both frontend and backend display their git commit hashes:

- **Frontend**: Injected at build time via `GIT_COMMIT_HASH` build arg
- **Backend**: Read at runtime via `git rev-parse --short HEAD`

**Hover over the version in the footer** to see the commit hash.

### Release Checklist

When making a release:

1. **Update frontend version** in `package.json` (root):
   ```json
   "version": "0.2.4"  // bump version
   ```
   The `prebuild` script (`frontend/update-version.js`) automatically syncs this to `frontend/version.js` at build time.

2. **Update backend version** in `pyproject.toml`:
   ```toml
   [project]
   version = "0.1.5"  // bump version
   ```

3. **Lock dependencies** — run `uv lock` to update `uv.lock` (it tracks the `llmaixweb` version from `pyproject.toml` and will update automatically):
   ```bash
   uv lock
   ```

4. **Build and push images** (handled by GitHub Actions on release tag)

4. **Tag the release** on GitHub:
   ```bash
   git tag v0.0.3
   git push origin v0.0.3
   ```

### Why Separate Versions?

- Frontend and backend are deployed as separate Docker images
- Each can be updated independently
- Users can see both versions in the UI footer to verify their deployment

### Version Display

The application displays both versions in the footer of every page:
```
Frontend Version: 0.0.2 | Backend Version: 0.1.3
```

Hover over each version to see the git commit hash:
```
Frontend Version: 0.0.2 (hover: Commit: abc1234) | Backend Version: 0.1.3 (hover: Commit: def5678)
```

This helps users and support quickly identify version mismatches or outdated components.

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

## 🧪 Running Tests

### Backend Tests

```bash
# 1. Copy the example test environment file
cp backend/.env.localtest.example backend/.env.localtest

# 2. Edit backend/.env.localtest with your test settings (e.g., OpenAI API key for integration tests)

# 3. Run tests
ENV_PATH=backend/.env.localtest uv run pytest --verbose --cov=backend --cov-report=html
```

---

## 🐳 Optional Compose Overlays

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

## 📦 RustFS Storage (Optional)

Start the RustFS server for local development:

```bash
rustfs server llmaixwebdata
```

---

---

## ✉️ Email Setup (Optional)

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

## 👥 Initialize Users

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
