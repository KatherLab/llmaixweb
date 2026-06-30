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
│   ├── components/           # Reusable UI components (common/, + per-domain folders)
│   ├── composables/          # Reusable composition functions (download, pagination, WS updates, theme…)
│   ├── stores/               # Pinia stores (auth, firstAdmin)
│   ├── services/             # Axios client (`api.js`) + per-resource API modules (`*Api.js`)
│   ├── router/               # Vue Router config
│   └── utils/                # Formatters, date/err/markdown/schema helpers
├── alembic/                  # Database migrations
├── pyproject.toml            # Python deps, Ruff config, project metadata
├── compose.yml               # Docker Compose (CPU)
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
1. **Docling-serve** — remote service for embedded text extraction and Tesseract OCR (default, tried first for PDFs)
2. **Local Docling fallback** — embedded Docling when docling-serve is unavailable (optional, requires `DOCLING_LOCAL_FALLBACK=true`)
3. **Mistral OCR** — API-based OCR via Mistral or self-hosted DeepSeek-OCR-2 + KatDocExtract
4. **Vision LLM OCR** — API-based OCR via any OpenAI-compatible vision model

Both Mistral OCR and Vision LLM OCR can use self-hosted backends:
- `compose.deepseek.yml` provides a local Mistral OCR API (DeepSeek-OCR-2 + KatDocExtract)
- `compose.vllm.yml` provides a local OpenAI-compatible endpoint for Vision OCR

Point `MISTRAL_API_BASE` / `VISION_OCR_API_BASE` at the respective service.

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
- `/api/v1/auth/*` — login, token refresh, logout, public settings (incl. SSO provider list)
- `/api/v1/auth/sso/*` — OIDC SSO flow (login redirect + callback with JIT provisioning)
- `/api/v1/user/*` — user CRUD, invitations, self-service linked identities (`/me/identities`)
- `/api/v1/project/*` — projects (with sub-routers for files, documents, trials, etc.)
- `/api/v1/admin/*` — admin settings, Celery monitoring
- `/api/v1/admin/sso/*` — admin CRUD for OIDC identity providers

**Projects router** (`routers/v1/endpoints/projects.py`) has nested sub-routers via `APIRouter.include_router`. Each sub-resource (files, preprocess, documents, schemas, prompts, trials, groundtruth, evaluations) is a separate module with its own prefix.

### Key Backend Files & Their Roles

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, lifespan (DB init + Celery worker spawn), CORS |
| `core/config.py` | Pydantic `Settings` class with lazy init, all env vars, runtime validation |
| `core/security.py` | JWT token create/verify, password hashing, OAuth2 scheme, admin guard, refresh-token create/verify/revoke |
| `core/dynamic_settings.py` | DB-backed runtime settings override (cached via `lru_cache`) |
| `db/session.py` | SQLAlchemy engine + session factory, `init_db()` |
| `dependencies.py` | OpenAI client, S3 client, file get/save/remove, `get_db()` |
| `celery/celery_config.py` | Celery app with 2 queues (`default`, `preprocess`) |
| `celery/preprocessing.py` | `process_files_async` Celery task |
| `celery/info_extraction.py` | `extract_info_celery` Celery task |
| `celery/task_signals.py` | Celery signal hooks + sweeper: real-time status updates, crash messages, orphaned-task cleanup, WebSocket broadcast of task updates |
| `utils/preprocessing.py` | `PreprocessingPipeline` class — main preprocessing orchestrator |
| `utils/info_extraction.py` | LLM extraction logic (called by trial executor) |
| `utils/evaluation.py` | Evaluation metrics computation |
| `utils/password_policy.py` | Shared password validator (complexity rules, config-driven) |
| `utils/crypto.py` | Fernet encrypt/decrypt for secrets at rest (e.g. SSO client secrets) |
| `services/oidc_service.py` | OIDC discovery, authorize URL (PKCE + signed state), code exchange, userinfo |
| `routers/v1/endpoints/sso.py` | OIDC SSO login/callback flow + JIT user provisioning |
| `routers/v1/endpoints/admin_sso.py` | Admin CRUD for OIDC identity providers |
| `utils/enums.py` | All shared enums (FileType, PreprocessingStrategy, etc.) |
| `utils/url_safety.py` | SSRF guardrails for user-supplied custom API endpoints (blocks cloud-metadata, restricts schemes, disables redirect-following) |

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
  / (Landing)               → Landing
  /projects                 → ProjectOverview
  /projects/:projectId      → ProjectDetail (workflow tabs: Files → Preprocessing → Documents → Schemas → Trials → Evaluation)
  /account                  → AccountSettings (profile, change password, connected SSO accounts)
  /admin                    → AdminDashboard
    /admin/settings         → AdminSettings
    /admin/sso              → AdminSSO (OIDC provider management)
    /admin/celery           → AdminCelery
  /admin/user-management    → AdminUserManagement (admin only)
/                           → AuthLayout (no navbar)
  /login                    → Login (shows SSO "Continue with…" buttons when enabled)
  /register                 → Register
  /invitation/:token        → InvitationLanding
  /auth/sso/complete        → SsoComplete (SSO callback: reads tokens from URL fragment)
  /first-admin              → FirstAdminSetup
  /forgot-password          → ForgotPassword
  /reset-password/:token    → ResetPassword
```

**Route guards:**
- `requiresAuth` → redirects to `/login` with return URL
- `adminOnly` → redirects non-admins to `/`
- First admin check runs before all routes; redirects to `/first-admin` if no admin exists
- Logged-in users are redirected away from `/login`, `/register`, `/invitation/*`, `/forgot-password`, `/reset-password/*`

### State Management
- **Pinia stores** in `stores/`:
  - `auth.js` — user session, token (localStorage), login/logout, `isAuthenticated`/`isAdmin` computed properties
  - `firstAdmin.js` — checks if any admin user exists (for first-run setup flow)

### API Client (`services/api.js`)
- Axios instance with dynamic base URL (runtime config > build-time env var > default)
- Request interceptor: adds Bearer token from localStorage
- Response interceptor: auto-logout on 401/403, toast notification

### API Service Layer (`services/*Api.js`)
Per-resource modules wrap the raw `api` instance — **components import functions from these, not the raw `api` instance**. One module per backend resource: `authApi`, `usersApi`, `ssoApi`, `projectsApi`, `llmApi`, `filesApi`, `preprocessingApi`, `documentsApi`, `documentSetsApi`, `schemasApi`, `promptsApi`, `trialsApi`, `groundtruthApi`, `evaluationsApi`, `adminApi`, `versionApi`. Each exports typed functions (e.g. `trialsApi.list(projectId, params)`, `documentsApi.delete(projectId, docId)`). The only legitimate direct `api` import outside `services/` is `stores/auth.js` (for the auth-header config).

### Shared Primitives & Composables
The frontend has a layer of reusable building blocks — prefer these over re-implementing:

- **`components/common/`** — `BaseModal` (Teleport + ref-counted scroll lock + ESC/backdrop close; the keystone most `*Modal.vue` components build on), `BaseButton`, `ConfirmationDialog`, `StatusBadge` (+ `utils/statusStyles.js`), `FilterChip`, `SearchInput`, `PaginationControls`, `JsonViewer`, `LoadingSpinner`, `EmptyState`, `ErrorBanner`, `Tooltip`, `FileIcon`, `PasswordInput` (password field w/ strength meter + show/hide, used by all auth/admin password flows), `FormField`.
- **`composables/`** — `useScrollLock` (ref-counted body scroll lock for stacked modals), `useFileDownload` (blob→objectURL→revoke), `usePagination` / `useDocumentPagination`, `useGridTheme` (shared ag-grid theme + dark-mode reactivity), `usePreprocessingUpdates` / `useTrialUpdates` (WebSocket subscribe + project-id filtering for live task progress), `useModelTesting`, `useSchemaKeyboard`.
- **`utils/`** — `formatters.js` (dates, file sizes, durations), `dateRange.js`, `errors.js` (`extractErrorMessage`), `markdown.js`, `schemaTypeIcons.js` (shared type→icon/color maps for the schema editor), `schemaTemplates.js` + `promptTemplates.js`, `ocrLabels.js`.

### Key UI Components

Large components are **orchestration shells** — they compose smaller sibling components (in the same folder) and move heavy logic into composables. When editing a feature, the shell is the entry point but the real UI/logic usually lives in its extracted children.

**Views (page-level):**
- **`Landing.vue`** — landing page; composes the 10 components in `components/landing/` (hero, pipeline visualization, interactive demo, feature grid)
- **`ProjectOverview.vue`** — project list grid
- **`ProjectDetail.vue`** — project detail with tabbed workflow interface (Files → Preprocessing → Documents → Schemas → Trials → Evaluation)
- **`AdminUserManagement.vue`** — user and invitation management (composes `InviteUserModal`/`EditUserModal` + ag-grid `UserGrid`/`InvitationGrid`)
- **`AdminSettings.vue`** — system settings configuration
- **`AdminSSO.vue`** — OIDC identity provider CRUD (admin tab under `/admin/sso`)
- **`AccountSettings.vue`** — self-service profile, change password, connected SSO accounts, sign out (`/account`)
- **`AdminCelery.vue`** — Celery task monitoring

**Components (reusable, by folder):**
- **`files/`** — `FilesAndProcessing.vue` (upload + preprocessing shell) with `FilesFilterBar`, `FileDropzone`, `UploadFilesModal`, `FilesTable`, `PreprocessingHistoryPanel`, `PreprocessingConfigPanel`, `FilePreviewModal`, `DuplicatePreviewModal`, `FileImportConfigModal`
- **`documents/`** — `DocumentsManagement.vue` (list/filter shell) with `DocumentsFilters`, `DocumentsTable`, `PaginationControls`, `BatchActionsModal` (mode-aware: `documents` or `trials`), `DocumentsGroups`, `DocumentViewer` (+ `DocumentViewerHeader`, `DocumentTextView`, `DocumentFilePreview`, `DocumentCompareView`, `VersionHistorySidebar`, `DocumentInfoSidebar`, `ExtractionMethodBadge`)
- **`schemas/`** — `SchemaManagement.vue` (lists schemas + prompts) with `SchemaListSection`/`PromptListSection`, `SchemaFormModal`/`PromptFormModal`, `SchemaViewModal`/`PromptViewModal`, `SchemaTemplatesModal`; `VisualSchemaEditor.vue` (full tree editor) + `SimpleSchemaEditor.vue` (simpler variant) with `SchemaTree`/`TreeNode`/`SchemaBlock`/`PropertyDetailsEditor` and `AddPropertyModal`/`EditPropertyModal`/`DeletePropertyModal`/`SchemaEditorToolbar`/`SchemaEditorHelpModal`
- **`trials/`** — `TrialsManagement.vue` (list/filter shell, batch select+delete) with `TrialCard`, `TrialFiltersPanel`, `CreateTrialModal` (+ `TrialMetadataCard`, `TrialSchemaSelect`/`TrialPromptSelect`/`TrialModelSelect`, `DocumentSelectionPanel` + pickers, `AdvancedSettingsPanel`, `CustomApiSettingsPanel`, `ModelTestCard`), `TrialResults` (+ `TrialResultCard`, `TrialMetaHeader`, `ResultReasoningPanel`, `ResultDocumentPreview`, `TrialDocumentErrors`), `RenameTrialModal`, `DownloadModal`, `TrialSelectorModal`, `TrialSchemaModal`, `TrialPromptModal`
- **`evaluation/`** — `EvaluationView.vue` / `EvaluationOverview.vue` (metrics + per-field accuracy), `FieldErrorAnalysis`, `DocumentAnalysis`, `EvaluationAnalysisModal`, `MetricsExportModal`
- **`groundtruth/`** — `GroundTruthManager.vue` / `GroundTruthUploadModal.vue` / `GroundTruthPreviewModal.vue`, `FieldTree`, `MappingList`, `IdFieldSelector`, `GroundTruthSample`, `ValidationBanner`
- **`admin/`** — `UserGrid` / `InvitationGrid` (ag-grid, themed via `useGridTheme`), `ActivityBell`, `InviteUserModal`, `EditUserModal`
- **`projects/`** — `ProjectGrid.vue` (ag-grid), `ProjectSettingsModal`, `CreateProjectButton`

---

## Important Development Conventions

### Naming & Imports
- Backend: `snake_case` for files, functions, variables; `PascalCase` for models and schemas
- Frontend: `PascalCase.vue` for components, `camelCase` for JS variables
- API routes use plural nouns (`/files`, `/projects`, `/trials/`)

### Frontend Patterns
- **Build modals on `BaseModal`** (Teleport + ref-counted scroll lock + ESC/backdrop). Don't hand-roll Teleport/backdrop/scroll-lock — nested modals will break.
- **Call the API through `services/*Api.js`**, not the raw `api` instance. Add a function to the relevant module if one is missing.
- **Reuse `composables/` and `components/common/`** before duplicating: downloads (`useFileDownload`), pagination (`usePagination` + `PaginationControls`), live task progress (`usePreprocessingUpdates`/`useTrialUpdates`), grid theming (`useGridTheme`), status pills (`StatusBadge`), error messages (`utils/errors.js` `extractErrorMessage`), dates/sizes (`utils/formatters.js`).
- **`defineProps` style**: use full `{ type, required, default }` validation. Object/Array defaults must be factory functions (`() => ({})` / `() => []`); use `default: undefined` for optional Object/Function props that are falsy-checked (`v-if="prop"`). Don't use `() => null` for Object/Array (triggers Vue dev-mode type warnings).
- **Dark mode**: AppLayout owns the `darkMode` toggle (writes `localStorage['darkMode']` + toggles the `dark` class on `<html>`). Tailwind is `darkMode: 'class'`. ag-grids theme via `useGridTheme`, which re-themes on the class change.
- **Verification gate**: `npm run check` (prettier + eslint, 0 errors required) and `npm run build` must pass before committing.

### Linting & Formatting

Always run these checks before committing changes:

**Frontend:**
```bash
npm run check          # prettier --check + eslint
npm run format         # prettier --write (auto-fix)
npm run lint:fix       # eslint --fix
```

Pre-commit hook auto-runs `lint-staged` (eslint + prettier on staged `.js`/`.vue` files via `simple-git-hooks`).

**Backend:**
```bash
uv run ruff check backend/src/
uv run ruff format backend/src/
```

### Build Check

Always verify the frontend builds cleanly:
```bash
npm run build
```

---

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
- Four compose files compose together via `-f` flag pattern:
  - `compose.yml` — base (CPU), always required
  - `compose.dev.yml` — local code hot-reload
  - `compose.deepseek.yml` — self-hosted Mistral OCR (vLLM + KatDocExtract, GPU)
  - `compose.vllm.yml` — self-hosted OpenAI-compatible endpoint (GPU)
- Images: `ghcr.io/katherlab/llmaixweb-backend:latest`, `ghcr.io/katherlab/llmaixweb-frontend:latest`
- Database migrations run automatically on backend container startup

### Versioning
- Separate versions for frontend (`package.json` root → auto-synced to `frontend/version.js`) and backend (`pyproject.toml` - `llmaixweb` package version)
- Both displayed in UI footer with git commit hashes on hover
- Backend commit hash read at runtime via `git rev-parse --short HEAD`; frontend commit hash injected at build time via `GIT_COMMIT_HASH` build arg

#### Release Checklist
1. **Bump frontend version** in `package.json` (root) — the `prebuild` script auto-syncs to `frontend/version.js` at build time
2. **Bump backend version** in `pyproject.toml` (e.g. `version = "0.3.3"`)
3. **Lock dependencies** — run `uv lock` if any dependencies changed; the `uv.lock` file also tracks the `llmaixweb` version and will update automatically
4. **Build and push images** — handled by GitHub Actions on release tag
5. **Tag the release:**
   ```bash
   git tag v0.3.3
   git push origin v0.3.3
   ```
- Frontend and backend are separate Docker images, so they can be updated independently

### Common Pitfalls & Patterns
- **Settings initialization** uses lazy loading to avoid requiring `.env` for Alembic — use `SKIP_RUNTIME_CHECKS=true` for migration commands
- **Storage abstraction**: `dependencies.py` provides `get_file()`/`save_file()`/`remove_file()` that work with both local and S3 storage — always use these, never access storage directly
- **Cancellation pattern**: Both `PreprocessingTask` and `Trial` have `is_cancelled` + `rollback_on_cancel` flags. The Celery task checks `is_cancelled` periodically. Rollback deletes produced documents/results.
- **DB session**: Use `get_db()` dependency injection in routes, or `db_session()` context manager for standalone operations
- **Frontend token**: Stored in `localStorage` under key `"token"`, managed by `auth.js` Pinia store
- **File UUIDs**: Storage uses UUID-based filenames, the `file_uuid` field links DB records to stored files
- **Docling-serve**: For PDFs, docling-serve is tried first for embedded text. If insufficient (< 100 chars by default), falls back to configured OCR engine. Set `force_ocr=true` to skip.

### When Adding New Features
1. **Backend model** → add to `models/project.py`, create Alembic migration
2. **Pydantic schema** → add to `schemas/project.py` or new schema file
3. **API endpoint** → add as new router file in `routers/v1/endpoints/`, register in `projects.py` sub-router or in `main.py` top-level router
4. **Frontend component** → add to `components/<domain>/` or `views/`, add route in `router/index.js`. Add API calls to the matching `services/*Api.js` module; build modals on `BaseModal` and reuse `composables/` + `components/common/` per the Frontend Patterns above.
5. **Celery task** → add to `celery/` directory, register in `celery_config.py` `include` list

### Async Task Lifecycle
1. API endpoint creates a `PreprocessingTask` or `Trial` with `PENDING` status
2. Celery task is dispatched with the DB record ID
3. Worker sets status to `IN_PROGRESS`, processes data, updates progress
4. On completion: `COMPLETED` or `FAILED` status
5. Frontend gets live updates via WebSocket (broadcast by `celery/task_signals.py`); components subscribe through the `usePreprocessingUpdates` / `useTrialUpdates` composables (which filter by project id and merge updates). Some views also poll the status endpoint as a fallback.
