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

## Compose files

The four compose files combine via repeated `-f` flags:

| File | Purpose |
| --- | --- |
| `compose.yml` | Base stack (CPU) — **always required**. |
| `compose.dev.yml` | Local code hot-reload for development. |
| `compose.deepseek.yml` | Self-hosted Mistral-compatible OCR (DeepSeek-OCR-2 + KatDocExtract, GPU). |
| `compose.vllm.yml` | Self-hosted OpenAI-compatible endpoint (e.g. Gemma via vLLM, GPU). |

Example — base stack only:

```bash
docker compose -f compose.yml up -d
```

Example — base stack plus a self-hosted vision endpoint:

```bash
docker compose -f compose.yml -f compose.vllm.yml up -d
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
