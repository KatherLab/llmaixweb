![Tests](https://github.com/KatherLab/llmaixweb/actions/workflows/tests.yml/badge.svg?branch=main)

> [!IMPORTANT]  
> This application is an early preview. It may not run stably and extracted results can be inaccurate. Always check outputs for validity before using them in practice.

# LLMAIx (v2) Web

![cover.png](static/cover.png)

A modern web interface for the **LLMAIx** framework that turns unstructured medical documents into structured JSON with privacy‑first controls. The application includes an admin dashboard for configuring providers, prompts, schemas, and overrides, plus basic **user management** (e.g. invitations when enabled).

---

## ✨ Features

* **Upload & organize**: multi‑format file support (PDF, DOC/DOCX, PNG/JPEG images, CSV/XLSX) with column selection, grouping and previews.
* **Preprocessing & OCR**: local OCR via **OCRmyPDF** (Tesseract), text extraction via **Docling**, and API-based OCR via **Mistral OCR** or any **Vision LLM** (OpenAI-compatible). Document parsers include **PyMuPDF4LLM** and **Docling**.
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
* Optional GPU stack: NVIDIA driver + NVIDIA Container Toolkit (for LLM inference only, not needed for OCR)
* **OpenAI-compatible API** (e.g., official OpenAI, self-hosted vLLM, llama.cpp, ollama, …)
* (Optional) **RustFS** for object storage or any other S3 storage

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

| File                   | Purpose                                                                                         |
|------------------------|-------------------------------------------------------------------------------------------------|
| `compose.yml`          | **Default config** - CPU-only backend, works with Docker & Podman                               |
| `compose.gpu.yml`      | **GPU config** - GPU-enabled backend (NVIDIA driver required, for LLM inference)                |
| `compose.dev.yml`      | **Optional overlay** - Mounts local code for hot-reload (development only)                      |
| `compose.deepseek.yml` | **Optional GPU overlay** - Self-hosted Mistral OCR API via DeepSeek-OCR-2 + KatDocExtract       |
| `compose.vllm.yml`     | **Optional GPU overlay** - Bring your own vLLM OpenAI-compatible endpoint (e.g. for Vision OCR) |

**Usage pattern:**
```bash
# Default CPU setup (recommended)
docker compose up -d

# Development with code hot-reload
docker compose -f compose.dev.yml up -d

# GPU deployment (for GPU-accelerated LLM inference in the backend)
docker compose -f compose.gpu.yml up -d

# Self-hosted Mistral OCR via DeepSeek-OCR-2 (GPU required)
docker compose -f compose.yml -f compose.deepseek.yml up -d

# Self-hosted vLLM endpoint for Vision LLM OCR or as main LLM provider (GPU required)
docker compose -f compose.yml -f compose.vllm.yml up -d
```

> **Combine overlays:** Overlay files stack, e.g. `docker compose -f compose.yml -f compose.gpu.yml -f compose.deepseek.yml up -d` for GPU backend + self-hosted OCR.

### Environment Configuration

Edit the `.env` file to match your deployment. **For basic setups, only the LLM provider settings are required** - all other defaults work with docker-compose out of the box.

#### Essential Settings

| Variable           | Description                        | Default          |
|--------------------|------------------------------------|------------------|
| `OPENAI_API_KEY`   | API key for LLM provider           | (required)       |
| `OPENAI_API_BASE`  | Base URL for OpenAI-compatible API | (empty)          |
| `OPENAI_API_MODEL` | Default model to use               | (empty)          |
| `SECRET_KEY`       | Secret key for sessions            | (auto-generated) |

#### Storage

**RustFS** (can be any S3 compatible storage):

| Variable                | Default              |
|-------------------------|----------------------|
| `AWS_ACCESS_KEY_ID`     | `rustfsadmin`        |
| `AWS_SECRET_ACCESS_KEY` | `rustfsadmin`        |
| `S3_ENDPOINT_URL`       | `http://rustfs:9000` |
| `S3_BUCKET_NAME`        | `llmaixweb`          |

**Local filesystem** (alternative):

| Variable          | Description                     |
|-------------------|---------------------------------|
| `LOCAL_DIRECTORY` | Path to local storage directory |

#### Other Settings

| Variable                  | Description                           | Default                        |
|---------------------------|---------------------------------------|--------------------------------|
| `BACKEND_CORS_ORIGINS`    | Comma-separated allowed origins       | `http://localhost:5173`        |
| `VITE_API_BACKEND_URL`    | Runtime backend URL for frontend      | `http://localhost:8000/api/v1` |
| `REQUIRE_INVITATION`      | Require invitation for signup         | `false`                        |
| `ALLOW_FIRST_ADMIN_SETUP` | Allow first user to become admin      | `true`                         |
| `CELERY_PREPROCESS_POOL`  | Pool type (`auto`, `solo`, `prefork`) | `auto` (use `solo` on macOS)   |
| `MISTRAL_API_BASE`        | Mistral OCR API base URL              | `https://api.mistral.ai`       |
| `MISTRAL_API_KEY`         | Mistral OCR API key (server default)  | (empty)                        |
| `MISTRAL_OCR_ENABLED`     | Enable Mistral OCR engine             | `true`                         |
| `VISION_OCR_ENABLED`      | Enable Vision LLM OCR engine          | `true`                         |
| `VISION_OCR_API_KEY`      | Vision OCR API key (server default)   | (empty)                        |
| `VISION_OCR_API_BASE`     | Vision OCR API base URL               | (empty)                        |
| `VISION_OCR_MODEL`        | Vision OCR default model              | `gpt-4o`                       |

> **Self-hosted OCR:** Use `docker compose -f compose.yml -f compose.deepseek.yml up -d` for a local Mistral OCR-compatible API (DeepSeek-OCR-2 via KatDocExtract). Use `docker compose -f compose.yml -f compose.vllm.yml up -d` for a local vision LLM endpoint (e.g. Gemma 4). See `.env.example` for the required env var overrides.

<details>
<summary>Database & Advanced Settings (click to expand)</summary>

These defaults work with docker-compose - only change if using external services.

| Variable                      | Description                  | Default                |
|-------------------------------|------------------------------|------------------------|
| `POSTGRES_SERVER`             | Database host                | `postgres`             |
| `POSTGRES_USER`               | Database user                | `postgres`             |
| `POSTGRES_PASSWORD`           | Database password            | `postgres`             |
| `POSTGRES_DB`                 | Database name                | `llmaixweb`            |
| `CELERY_BROKER_URL`           | Redis broker URL             | `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND`       | Redis result backend         | `redis://redis:6379/0` |
| `DISABLE_CELERY`              | Disable Celery workers       | `false`                |
| `INITIALIZE_CELERY`           | Initialize Celery on startup | `false`                |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry in minutes      | `60*24*8`              |
| `RUSTFS_ACCESS_KEY`           | RustFS access key            | `rustfsadmin`          |
| `RUSTFS_SECRET_KEY`           | RustFS secret key            | `rustfsadmin`          |

</details>

#### Local Network & Reverse Proxy

> **Testing in local network?** Access from other devices requires:
> 1. Set `BACKEND_CORS_ORIGINS` to include your server IP (e.g., `http://192.168.1.100:5173`)
> 2. Set `VITE_API_BACKEND_URL` to point to your server (e.g., `http://192.168.1.100:8000/api/v1`)
> 3. Restart the stack
>
> **Using a reverse proxy (nginx, Traefik, etc.)?** Adjust:
> - `BACKEND_CORS_ORIGINS` to your public domain (e.g., `https://app.example.com`)
> - `VITE_API_BACKEND_URL` to your public API endpoint (e.g., `https://api.example.com/api/v1`)

---

## 🚀 Get started

1. **Configure**: Edit `.env` and set at minimum:
   - `OPENAI_API_KEY`, `OPENAI_API_BASE`, `OPENAI_API_MODEL` (your LLM provider)
   - `SECRET_KEY` (random string for production)

2. **Start**: `docker compose up -d`

3. **Access**: Open **[http://localhost:5173](http://localhost:5173)**

4. **Setup**: Create an admin account on first visit

5. **Configure**: In the admin panel, set up your LLM provider and extraction schemas

6. **Upload**: Add documents and run your first extraction trial

> **Troubleshooting**: Check container logs with `docker compose logs -f backend` if the app fails to start. Most issues are missing/invalid environment variables.

---

## 🔧 Development

See [DEVELOPER.md](DEVELOPER.md) for development instructions, including running tests and initializing users.

---

## 🔐 Security & Privacy

* Keep PHI strictly local unless you explicitly configure a remote provider.
* Prefer self-hosted, OpenAI-compatible endpoints for clinical data.
* Review your `.env` secrets and never commit them.

---

## 📜 License

This project is licensed under the **AGPL-3.0**. See [LICENSE](LICENSE).
