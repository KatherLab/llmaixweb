# AGENTS.md — LLMAIx Web Codebase Guide

This file explains the structure, concepts, and conventions of the **LLMAIx Web** repository to help AI agents (and humans) work with the codebase effectively.

---

## What is LLMAIx Web?

A web application for extracting structured JSON data from unstructured medical/lab documents using LLMs. Users upload files (PDFs, images, spreadsheets), preprocess them via OCR/text extraction, define JSON schemas and prompts, run LLM-based extraction "trials", and evaluate results against ground truth data. Privacy-first: can run fully local or with self-hosted LLM providers.

**Tech stack:** Vue 3 + Vite + TailwindCSS (frontend), FastAPI (backend), SQLAlchemy (ORM), Celery (async tasks), PostgreSQL (primary DB, SQLite for dev), Pydantic (config).

---

## Top-Level Directory Layout

```
llmaixweb/
├── backend/src/              # FastAPI Python backend
│   ├── main.py               # App entry point, CORS, Celery worker spawn
│   ├── core/                 # Config, security, dynamic settings
│   ├── db/                   # SQLAlchemy engine, session, base
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic request/response schemas
│   ├── routers/v1/endpoints/ # FastAPI route handlers
│   ├── services/             # External service integrations (OCR)
│   ├── celery/               # Celery app config + tasks
│   └── utils/                # Enums, helpers, evaluation logic
├── frontend/                 # Vue 3 frontend
│   ├── views/                # Page-level components (routed)
│   ├── components/           # Reusable UI components
│   ├── stores/               # Pinia stores (auth, firstAdmin)
│   ├── services/             # Axios API client
│   ├── router/               # Vue Router config
│   └── utils/                # Formatters, file type helpers
├── alembic/                  # Database migrations
├── pyproject.toml            # Python deps, Ruff config, project metadata
├── compose.yml               # Docker Compose (CPU)
├── compose.gpu.yml           # Docker Compose (GPU)
├── compose.dev.yml           # Docker Compose (dev hot-reload)
├── compose.deepseek.yml      # Optional: self-hosted Mistral OCR (DeepSeek-OCR-2 + KatDocExtract, GPU)
└── compose.vllm.yml          # Optional: self-hosted vLLM endpoint (e.g. Gemma 4 for Vision OCR, GPU)
```

---

## Core Concepts & Data Flow

### The Project Workflow (Step-by-Step)

A **Project** is the top-level container. Within a project, users follow this sequence:

```
Files → Preprocessing → Documents → Schemas + Prompts → Trials → Evaluation
```

### 1. Files
Users upload files to a project. Supported types: PDF, DOC/DOCX, PNG/JPEG, CSV/XLSX, TXT. Files are stored either in **local storage** (`LOCAL_DIRECTORY`) or **S3-compatible storage** (via `boto3`). Each file gets a UUID-based filename for storage. Duplicate detection uses SHA-256 hashes.

**Key model:** `File` (`models/project.py:119`)
- Links to project via `project_id`
- Has a `preprocessing_strategy` (for CSV/XLSX: `full_document` or `row_by_row`)
- Has `file_metadata` JSON for CSV import config (text columns, delimiters, etc.)
- `file_creator` distinguishes user-uploaded vs system-generated files

### 2. Preprocessing
Files are processed asynchronously via **Celery** to extract text content. The `PreprocessingPipeline` class (`utils/preprocessing.py`) handles this.

**Key models:**
- `PreprocessingTask` — overall task for a batch of files (tracks progress, cancellation)
- `FilePreprocessingTask` — per-file subtask (status, errors, warnings)
- `PreprocessingConfiguration` — reusable settings presets (which OCR engine, parameters)

**OCR engines (for PDFs/images):**
1. **Docling** — embedded text extraction (tried first for PDFs, no OCR, falls back if insufficient text)
2. **ocrmypdf (Tesseract)** — local OCR using Tesseract
3. **Mistral OCR** — API-based OCR via Mistral
4. **Vision LLM OCR** — API-based OCR via any OpenAI-compatible vision model

Both Mistral OCR and Vision LLM OCR can use self-hosted backends:
`compose.deepseek.yml` provides a local Mistral OCR API; `compose.vllm.yml` provides a local OpenAI-compatible endpoint for Vision OCR. Point `MISTRAL_API_BASE` / `VISION_OCR_API_BASE` at the respective service.

**For CSV/XLSX files:**
- `full_document` strategy: entire table converted to text
- `row_by_row` strategy: each row becomes a separate document (with configurable text columns and optional case ID column)

**FilePreprocessingTask.warnings** stores processing warnings (e.g., skipped rows).

### 3. Documents
The output of preprocessing — each `Document` has extracted `text` content ready for LLM extraction. Documents link back to their original file and preprocessing config. They can be organized into **DocumentSets** (groups of documents for trial execution).

**Key model:** `Document` (`models/project.py:188`)
- `text` — the extracted text content (what gets sent to the LLM)
- `document_name` — human-readable name
- `meta_data` — tracks extraction method, OCR engine used, row index, etc.
- Has a uniqueness constraint on `(original_file_id, preprocessing_config_id, document_name)`

**DocumentSet** allows grouping documents. Trials are run against all documents in a set.

### 4. Schemas & Prompts
Before running LLM extraction, users define:
- **Schema** — a JSON schema defining the structured output format (nested objects, arrays, all JSON types). Has a visual tree editor in the frontend.
- **Prompt** — system prompt and user prompt templates. The user prompt typically receives the document text as input; the system prompt instructs the LLM on extraction rules using the schema.

**Key models:**
- `Schema` (`models/project.py:467`) — `schema_name` + `schema_definition` (JSON)
- `Prompt` (`models/project.py:448`) — `system_prompt` + `user_prompt`

### 5. Trials
A **Trial** runs LLM-based extraction against a set of documents using a specific schema + prompt + LLM model combination. Results are stored as `TrialResult` objects (one per document).

**Key model:** `Trial` (`models/project.py:492`)
- References `schema_id`, `prompt_id`, `document_set_id`
- `llm_model`, `api_key`, `base_url` — the LLM endpoint configuration (OpenAI-compatible)
- `bypass_celery` — if True, runs synchronously (for small trials)
- `advanced_options` — JSON for temperature, max_tokens, etc.
- `document_ids` — explicit list of document IDs to process
- Supports cancellation with optional rollback

**TrialResult** — one per document per trial, stores the `result` JSON and `additional_content`.

**Important:** The system uses **any OpenAI-compatible API**. This includes official OpenAI, self-hosted vLLM, llama.cpp, Ollama, or custom gateways.

### 6. Evaluation
Users can upload **GroundTruth** files (CSV/XLSX with correct extraction values) and compare trial results against them via **Evaluations**.

**Key models:**
- `GroundTruth` — uploaded file with cached data, links to a project
- `FieldMapping` — maps ground truth columns to schema fields, with `comparison_method` (exact, fuzzy, numeric, etc.)
- `Evaluation` — stores overall metrics, per-field metrics, per-document metrics, confusion matrices
- `EvaluationMetric` — individual field-level correctness for each document

**Creating an evaluation** requires: a trial, a ground truth file, field mappings associating ground truth columns with schema fields. The system then computes accuracy metrics.

---

## Backend Architecture

### API Structure
All endpoints are under `/api/v1/`. The main router (`main.py:78-83`) includes:
- `/api/v1/auth/*` — login, token refresh
- `/api/v1/user/*` — user CRUD, invitations
- `/api/v1/project/*` — projects (with sub-routers for files, documents, trials, etc.)
- `/api/v1/admin/*` — admin settings, Celery monitoring

**Projects router** (`routers/v1/endpoints/projects.py`) has nested sub-routers via `APIRouter.include_router`. Each sub-resource (files, preprocess, documents, schemas, prompts, trials, groundtruth, evaluations) is a separate module with its own prefix.

### Key Backend Files & Their Roles

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, lifespan (DB init + Celery worker spawn), CORS |
| `core/config.py` | Pydantic `Settings` class with lazy init, all env vars, runtime validation |
| `core/security.py` | JWT token create/verify, password hashing, OAuth2 scheme, admin guard |
| `core/dynamic_settings.py` | DB-backed runtime settings override (cached via `lru_cache`) |
| `db/session.py` | SQLAlchemy engine + session factory, `init_db()` |
| `dependencies.py` | OpenAI client, S3 client, file get/save/remove, `get_db()` |
| `celery/celery_config.py` | Celery app with 2 queues (`default`, `preprocess`) |
| `celery/preprocessing.py` | `process_files_async` Celery task |
| `celery/info_extraction.py` | `extract_info_celery` Celery task |
| `utils/preprocessing.py` | `PreprocessingPipeline` class — main preprocessing orchestrator |
| `utils/info_extraction.py` | LLM extraction logic (called by trial executor) |
| `utils/evaluation.py` | Evaluation metrics computation |
| `utils/enums.py` | All shared enums (FileType, PreprocessingStrategy, etc.) |

### Configuration System
- **`Settings` class** (`core/config.py`): Uses Pydantic `BaseSettings`. Reads from `.env` file (path in `ENV_PATH` env var, defaults to `backend/.env`) or environment variables. Validates OpenAI API connection and storage on init.
- **Runtime overrides**: Admin panel changes are stored in `app_settings` DB table and loaded via `dynamic_settings.py` with LRU cache. Only non-readonly settings can be overridden.
- **Skip runtime checks**: Set `SKIP_RUNTIME_CHECKS=true` for Alembic migrations (bypasses OpenAI/S3 validation).

### Database
- Uses SQLAlchemy ORM with `declarative_base`
- `init_db()` creates all tables via `Base.metadata.create_all()`
- Alembic for migrations (auto-generated from model changes)
- Migration command prefix: `SKIP_RUNTIME_CHECKS=true uv run alembic ...`

### Celery
- Two task queues: `default` (general tasks, 4 workers) and `preprocess` (heavy OCR, 1 worker)
- Workers are spawned as `multiprocessing.Process` objects in the FastAPI lifespan
- Pool type configurable via `CELERY_DEV_POOL` (default: `threads`) and `CELERY_PREPROCESS_POOL`
- Task safety: `task_acks_late=True`, `task_reject_on_worker_lost=True`, `worker_prefetch_multiplier=1`

---

## Frontend Architecture

### Routing Structure (`router/index.js`)
```
/                           → AppLayout (navbar)
  / (Landing)               → Dashboard
  /projects                 → Project list
  /projects/:projectId      → Project detail (workflow tabs)
  /admin/user-management    → User management (admin only)
  /admin/settings           → Settings (admin only)
  /admin/celery             → Celery monitoring (admin only)
/                           → AuthLayout (no navbar)
  /login                    → Login
  /register                 → Register
  /invitation/:token        → Invitation registration
  /first-admin              → First admin setup
```

**Route guards:**
- `requiresAuth` → redirects to `/login` with return URL
- `adminOnly` → redirects non-admins to `/`
- First admin check runs before all routes; redirects to `/first-admin` if no admin exists
- Logged-in users are redirected away from `/login`, `/register`, `/invitation/*`

### State Management
- **Pinia stores** in `stores/`:
  - `auth.js` — user session, token (localStorage), login/logout, `isAuthenticated`/`isAdmin` computed properties
  - `firstAdmin.js` — checks if any admin user exists (for first-run setup flow)

### API Client (`services/api.js`)
- Axios instance with dynamic base URL (runtime config > build-time env var > default)
- Request interceptor: adds Bearer token from localStorage
- Response interceptor: auto-logout on 401/403, toast notification

### Key UI Components
- **`ProjectWorkflow.vue`** — step-based tabs showing the full pipeline (Files → Preprocessing → Documents → Schemas → Trials → Evaluation)
- **`VisualSchemaEditor.vue`** / **`SchemaTree.vue`** — tree-based JSON schema editor
- **`CreateTrialModal.vue`** — trial creation dialog with schema/prompt/model selection
- **`EvaluationView.vue`** — metrics display with per-field accuracy
- **Various admin views** — settings management, Celery monitoring, user/invitation management

---

## Important Development Conventions

### Naming & Imports
- Backend: `snake_case` for files, functions, variables; `PascalCase` for models and schemas
- Frontend: `PascalCase.vue` for components, `camelCase` for JS variables
- API routes use plural nouns (`/files`, `/projects`, `/trials/`)

### Environment Variables
- `.env.example` documents all available settings
- `ENV_PATH` env var controls `.env` file location (defaults to `backend/.env`)
- Frontend runtime config via `window.__APP_CONFIG__` (injected in Docker)
- Frontend build-time vars via `VITE_*` prefix

### Running Tests

Backend:
```bash
ENV_PATH=backend/.env.localtest uv run pytest --verbose --cov=backend --cov-report=html
```

Frontend tests are currently not set up.

### Docker
- Five compose files compose together via `-f` flag pattern:
  - `compose.yml` — base (CPU), always required
  - `compose.gpu.yml` — GPU-enabled backend
  - `compose.dev.yml` — local code hot-reload
  - `compose.deepseek.yml` — self-hosted Mistral OCR (vLLM + KatDocExtract, GPU)
  - `compose.vllm.yml` — self-hosted OpenAI-compatible endpoint (GPU)
- Images: `ghcr.io/katherlab/llmaixweb-backend:cpu|gpu`, `ghcr.io/katherlab/llmaixweb-frontend:latest`
- Database migrations run automatically on backend container startup

### Versioning
- Separate versions for frontend (`package.json` root → auto-synced to `frontend/version.js`) and backend (`pyproject.toml` - `llmaixweb` package version)
- Both displayed in UI footer with git commit hashes on hover
- Backend commit hash read at runtime via `git rev-parse --short HEAD`; frontend commit hash injected at build time via `GIT_COMMIT_HASH` build arg

#### Release Checklist
1. **Bump frontend version** in `package.json` (root) — the `prebuild` script auto-syncs to `frontend/version.js` at build time
2. **Bump backend version** in `pyproject.toml` (e.g. `version = "0.1.4"`)
3. **Lock dependencies** — run `uv lock` if any dependencies changed; the `uv.lock` file also tracks the `llmaixweb` version and will update automatically
4. **Build and push images** — handled by GitHub Actions on release tag
5. **Tag the release:**
   ```bash
   git tag v0.0.3
   git push origin v0.0.3
   ```
- Frontend and backend are separate Docker images, so they can be updated independently

### Common Pitfalls & Patterns
- **Settings initialization** uses lazy loading to avoid requiring `.env` for Alembic — use `SKIP_RUNTIME_CHECKS=true` for migration commands
- **Storage abstraction**: `dependencies.py` provides `get_file()`/`save_file()`/`remove_file()` that work with both local and S3 storage — always use these, never access storage directly
- **Cancellation pattern**: Both `PreprocessingTask` and `Trial` have `is_cancelled` + `rollback_on_cancel` flags. The Celery task checks `is_cancelled` periodically. Rollback deletes produced documents/results.
- **DB session**: Use `get_db()` dependency injection in routes, or `db_session()` context manager for standalone operations
- **Frontend token**: Stored in `localStorage` under key `"token"`, managed by `auth.js` Pinia store
- **File UUIDs**: Storage uses UUID-based filenames, the `file_uuid` field links DB records to stored files
- **Docling fallback**: For PDFs, Docling is always tried first for embedded text. If insufficient (< 50 chars), falls back to configured OCR engine. Set `force_ocr=true` to skip Docling.

### When Adding New Features
1. **Backend model** → add to `models/project.py`, create Alembic migration
2. **Pydantic schema** → add to `schemas/project.py` or new schema file
3. **API endpoint** → add as new router file in `routers/v1/endpoints/`, register in `projects.py` sub-router or in `main.py` top-level router
4. **Frontend component** → add to `components/` or `views/`, add route in `router/index.js`
5. **Celery task** → add to `celery/` directory, register in `celery_config.py` `include` list

### Async Task Lifecycle
1. API endpoint creates a `PreprocessingTask` or `Trial` with `PENDING` status
2. Celery task is dispatched with the DB record ID
3. Worker sets status to `IN_PROGRESS`, processes data, updates progress
4. On completion: `COMPLETED` or `FAILED` status
5. Frontend polls status endpoint periodically for progress updates
