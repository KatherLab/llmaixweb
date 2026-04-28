![Tests](https://github.com/KatherLab/llmaixweb/actions/workflows/tests.yml/badge.svg?branch=main)

> [!IMPORTANT]  
> This application is an early preview. It may not run stably and extracted results can be inaccurate. Always check outputs for validity before using them in practice.

# LLMAIx (v2) Web

![cover.png](static/cover.png)

A modern web interface for the **LLMAIx** framework that turns unstructured medical documents into structured JSON with privacy‑first controls. The application includes an admin dashboard for configuring providers, prompts, schemas, and overrides, plus basic **user management** (e.g. invitations when enabled).

---

## ✨ Features

* **Upload & organize**: multi‑format file support (PDF, DOC/DOCX, PNG/JPEG images, CSV/XLSX) with column selection, grouping and previews.
* **Preprocessing & OCR**: pluggable methods including **Tesseract**, **Marker**, **PaddleOCR**, and vision LLMs; document parsers like **Docling**, **PyMuPDF4LLM**, and **MarkItDown**.
* **Visual schema editor**: tree‑based editor supporting nested objects/arrays, all JSON types, import/export, validation, and templates.
* **LLM trials**: run multiple extraction trials across prompts/models with temperature control, per‑trial iterations, token tracking, and OpenAI‑compatible endpoints (official OpenAI, vLLM, llama.cpp/Ollama, custom gateways).
* **Evaluation**: upload ground truth, compare field‑by‑field, compute overall/per‑field accuracy metrics.
* **Privacy‑first**: run fully locally or with self‑hosted providers; no forced external calls.
* **Admin dashboard**: provider configuration, **user management** (setup first admin, invitations/roles).

> Tech stack: **Vue 3 + Vite + TailwindCSS** (frontend), **FastAPI** (backend), **SQLAlchemy**, **Celery**, **Pydantic** for configuration.

---

## 📦 Requirements

* Node.js 18+ (for the frontend) and PNPM/NPM/Yarn
* Python 3.11+ (for the backend)
* Docker & Docker Compose (recommended for deployment)
* Optional GPU stack: NVIDIA driver + NVIDIA Container Toolkit
* **OpenAI-compatible API** (e.g., official OpenAI, self-hosted llama.cpp, vLLM, …)
* (Optional) **MinIO** for object storage or any other S3 storage

---

## 🐳 Docker Installation

### Quick Start (Development)

1. Clone the repository:

```bash
git clone https://github.com/KatherLab/llmaixweb
cd llmaixweb
```

2. Copy and edit environment files:

```bash
cp .env.example .env
# Edit .env with your settings
```

> **Note:** The `.env` file is required. The stack will fail to start without it (missing database credentials, secrets, etc.).

3. Start the stack:

```bash
# CPU only (default - works with Docker or Podman)
docker compose up -d
# or: podman compose up -d

# GPU (requires NVIDIA driver + container toolkit)
docker compose -f compose.gpu.yml up -d

# Development with hot-reload (optional overlay)
docker compose -f compose.dev.yml up -d
```

> **Tip:** Pre-built images are available at `ghcr.io/katherlab/llmaixweb-backend:cpu`, `ghcr.io/katherlab/llmaixweb-backend:gpu`, and `ghcr.io/katherlab/llmaixweb-frontend:latest`. Compose will automatically pull them if not present locally. Use `--build` to build from source instead.

4. Visit the web UI at **[http://localhost:5173](http://localhost:5173)**.

### Docker Compose Files

| File | Purpose |
|------|---------|
| `compose.yml` | **Default config** - CPU-only backend, works with Docker & Podman |
| `compose.gpu.yml` | **GPU config** - GPU-enabled backend (NVIDIA driver + container toolkit required) |
| `compose.dev.yml` | **Optional overlay** - Mounts local code for hot-reload (development only) |

**Usage pattern:**
```bash
# Default CPU setup (recommended)
docker compose up -d

# Development with code hot-reload
docker compose -f compose.dev.yml up -d

# GPU deployment
docker compose -f compose.gpu.yml up -d
```

### Environment Configuration

Edit the `.env` file to match your deployment:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key for LLM provider | (empty) |
| `OPENAI_API_BASE` | Base URL for OpenAI-compatible API | (empty) |
| `OPENAI_API_MODEL` | Default model to use | (empty) |
| `OPENAI_NO_API_CHECK` | Skip API connectivity check | `true` |
| `BACKEND_CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:5173` |
| `VITE_API_BACKEND_URL` | **Runtime** backend URL for frontend | `http://localhost:8000/api/v1` |
| `REQUIRE_INVITATION` | Require invitation for signup | `false` |
| `ALLOW_FIRST_ADMIN_SETUP` | Allow first user to become admin | `true` |

**Storage options:**
- **MinIO (local)**: Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL`, `S3_BUCKET_NAME`
- **AWS S3**: Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optionally `S3_ENDPOINT_URL`
- **Local filesystem**: Set `LOCAL_DIRECTORY=/path/to/storage`

---

## 🚀 Get started

1. Open **[http://localhost:5173](http://localhost:5173)**.
2. Create an **Admin** account.
3. Log in with your new account and configure an LLM provider under *Settings*.
4. Upload a few documents, define a schema, and run your first trial.

---

## 🔧 Development

See [DEVELOPER.md](DEVELOPER.md) for version management and release instructions.

### Initialize users

```bash
python -m backend.scripts.populate_users
```

**When using Docker**

```bash
# Running stack
docker compose -f compose.gpu.yml exec -it backend \
  python -m backend.scripts.populate_users

# Stopped stack
docker compose -f compose.gpu.yml run --rm -it backend \
  python -m backend.scripts.populate_users
```

### MinIO (optional for dev)

Start on macOS:

```bash
minio server miniodata
```

### Run backend tests

```bash
ENV_PATH=backend/.env uv run pytest --verbose --cov=backend --cov-report=html
```

---

## 🔐 Security & Privacy

* Keep PHI strictly local unless you explicitly configure a remote provider.
* Prefer self-hosted, OpenAI-compatible endpoints for clinical data.
* Review your `.env` secrets and never commit them.

---

## 📜 License

This project is licensed under the **AGPL-3.0**. See [LICENSE](LICENSE).
