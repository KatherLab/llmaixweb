# Installation

LLMAIx Web ships as two Docker images (backend and frontend) orchestrated with
Docker Compose. The compose files layer together so you can add optional
self-hosted GPU services only when you need them.

## Prerequisites

- **Docker** and **Docker Compose v2**.
- An **OpenAI-compatible LLM endpoint** — either an API key for a hosted service
  (OpenAI, Mistral, …) or a self-hosted endpoint (vLLM, llama.cpp, Ollama, …).
- For self-hosted OCR / vision models: an NVIDIA **GPU** with the appropriate
  drivers.
- For local development from source: **Node.js 20+** (22+ recommended; the build image uses Node 26) and **Python 3.13**.

## Quick start

```bash
git clone https://github.com/KatherLab/llmaixweb
cd llmaixweb
cp .env.example .env
# Edit .env — at minimum SECRET_KEY (OPENAI_API_* are optional; see Configuration)

docker compose up -d
```

Then open **[http://localhost:5173](http://localhost:5173)** and create an admin
account on first visit (see [First run](#first-run)).

!!! note "First run may take a few minutes"
    Images download on first launch. Watch progress with
    `docker compose logs -f` — once the backend health check passes and
    migrations finish, the app is ready. Pre-built images are published at
    `ghcr.io/katherlab/llmaixweb-backend:latest` and `…-frontend:latest`; add
    `--build` to build from source instead.

## Compose files

The four compose files combine via repeated `-f` flags. The overlays are
**optional** — without them the app simply connects to your configured remote
API.

| File | Purpose | GPU |
| --- | --- | --- |
| `compose.yml` | Base stack (CPU) — **always required** | No |
| `compose.dev.yml` | Local code hot-reload for development | No |
| `compose.deepseek.yml` | Self-hosted Mistral-compatible OCR (DeepSeek-OCR-2 + [KatDocExtract](https://github.com/KatherLab/KatDocExtract)) | Yes (24+ GB VRAM) |
| `compose.vllm.yml` | Self-hosted OpenAI-compatible endpoint (e.g. Gemma via vLLM) | Yes (model-dependent) |

```bash
# Minimal setup (CPU, uses your configured API provider)
docker compose up -d

# Development with hot-reload
docker compose -f compose.yml -f compose.dev.yml up -d

# Self-hosted Mistral OCR (GPU)
docker compose -f compose.yml -f compose.deepseek.yml up -d

# Self-hosted vision LLM (GPU)
docker compose -f compose.yml -f compose.vllm.yml up -d

# Combine overlays: all services
docker compose -f compose.yml -f compose.deepseek.yml -f compose.vllm.yml up -d
```

Database migrations run automatically on backend container startup.

## Configuration

All settings are provided through environment variables (an `.env` file, path
controlled by `ENV_PATH`, defaults to `backend/.env`). See
[`.env.example`](https://github.com/KatherLab/llmaixweb/blob/main/.env.example)
for every available setting, and the [Configuration](../operations/configuration.md)
page for the ones that matter most in production.

## First run

On first launch there is no admin account yet. The app redirects you to the
**First admin setup** screen (`/first-admin`) to create the initial
administrator. After that, sign in and create your first
[project](concepts.md).

## Production deployment

For a hardened, production-grade deployment (reverse proxy, secrets, S3 storage,
backups, and the full go-live checklist), follow the
[Deployment](../operations/deployment.md) page.

## Development environment

To run the app from source with hot-reload, see the
[Developer guide](../development/developer-guide.md).
