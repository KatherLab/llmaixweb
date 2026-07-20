# Deployment Guide

Operational guide for deploying and running LLMAIx Web in production. For the
quickstart and feature overview, see [README.md](README.md); for local
development, see [DEVELOPER.md](DEVELOPER.md).

---

## Architecture at a glance

The stack is fully containerized and runs on Docker / Podman Compose:

```
┌─────────────┐    ┌──────────┐    ┌──────────────┐
│  frontend   │───▶│ backend  │───▶│  postgres    │
│ (nginx:8080)│    │ (FastAPI)│    │  (pgdata vol)│
└─────────────┘    └────┬─────┘    └──────────────┘
      /api/ proxy      │
      /ws/ proxy       ├──▶ redis (broker + result backend)
                       ├──▶ rustfs (S3-compatible file storage)
                       ├──▶ docling-serve (local OCR)
       │               │
       │  ┌────────────┴───────────┐
       └──│ worker_default         │ (Celery, 4 concurrency — general tasks)
          │ worker_preprocess      │ (Celery, 1 concurrency — heavy OCR)
          └────────────────────────┘
```

- **frontend** serves the built SPA on `:8080` and reverse-proxies `/api/` and
  `/ws/` to the backend. Only this port needs to be exposed.
- **backend** runs FastAPI (uvicorn). Celery workers run in their own
  containers (`worker_default`, `worker_preprocess`); set
  `INITIALIZE_CELERY=true` only if you want the backend process to spawn
  in-process workers instead (not recommended for the compose deployment).
- **postgres**, **redis**, **rustfs** are stateful — their data lives in named
  volumes (`pgdata`, `redis-data`, `minio-data`).
- **docling-serve** runs Docling + Tesseract for local OCR (CPU, ~8 GB RAM).

Pre-built multi-arch images (`linux/amd64`, `linux/arm64`) are published to
`ghcr.io/katherlab/llmaixweb-backend:latest` and
`ghcr.io/katherlab/llmaixweb-frontend:latest` on every GitHub release.

---

## Prerequisites

- **Docker** 24+ (or Podman + `podman-compose`)
- **An OpenAI-compatible LLM endpoint** — official OpenAI, self-hosted vLLM,
  Ollama, llama.cpp, or any compatible gateway. Required for extraction.
- **Optional:** NVIDIA GPU + Container Toolkit — only if you use the
  `compose.deepseek.yml` or `compose.vllm.yml` overlays to self-host OCR/LLM.
- **Recommended resources (CPU-only):** 4 vCPU, 8 GB RAM, 40 GB disk. OCR and
  LLM traffic drive the actual load — size for your document volume.

---

## First-time deployment

1. **Clone and configure:**
   ```bash
   git clone https://github.com/KatherLab/llmaixweb
   cd llmaixweb
   cp .env.example .env
   ```

2. **Edit `.env`** — at minimum set:
   - `SECRET_KEY` — generate with
     `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
   - `OPENAI_API_KEY`, `OPENAI_API_BASE`, `OPENAI_API_MODEL` — your LLM
     endpoint
   - `APP_URL` — the public URL users will reach (e.g.
     `https://app.example.com`). Used for invitation/reset links and SSO
     redirects.
   - `BACKEND_CORS_ORIGINS` — the same public URL (comma-separated if
     multiple).

   See [.env.example](.env.example) for the full reference (storage, OCR,
   auth/SSO, password policy, etc.).

3. **Start the stack:**
   ```bash
   docker compose up -d
   ```

4. **Wait for health checks** (first run downloads images — several minutes):
   ```bash
   docker compose ps                       # all services should be "healthy"
   docker compose logs -f backend          # "Migrations completed" → ready
   ```

5. **Create the first admin** — open `APP_URL` in a browser; the first-visit
   flow prompts you to create an admin account.

6. **Configure LLM provider** in the admin panel (Admin → Settings) if you
   didn't pin it in `.env`, then upload documents and run trials.

> **Skip the startup LLM check** (e.g. to configure the provider later via the
> admin UI) by setting `OPENAI_NO_API_CHECK=true`. Storage and `SECRET_KEY`
> checks still run.

---

## Setup options

LLMAIx Web is privacy-first: every external integration is optional and
configurable either in `.env` (build-time defaults) or at runtime in **Admin →
Settings**. The three integration areas are independent — mix and match to fit
your environment.

### LLM provider (extraction)

Extraction trials call any **OpenAI-compatible** chat/completions endpoint.
Configure the server-wide default in `.env`:

| Variable | Meaning |
|---|---|
| `OPENAI_API_BASE` | Base URL of the endpoint (e.g. `https://api.openai.com/v1`, `http://vllm:8000/v1`, `http://host:11434/v1` for Ollama) |
| `OPENAI_API_KEY` | API key (use a dummy like `sk-noop` for self-hosted endpoints that don't auth) |
| `OPENAI_API_MODEL` | Default model id |
| `OPENAI_NO_API_CHECK` | `true` skips the startup connectivity check (lets you configure later in the admin UI) |

**Common setups:**
- **Official OpenAI** — `OPENAI_API_BASE=https://api.openai.com/v1`, your real key, model e.g. `gpt-4o`.
- **Self-hosted vLLM** (GPU, via `compose.vllm.yml`) — `OPENAI_API_BASE=http://vllm:8000/v1`, `OPENAI_API_KEY=sk-noop`, model e.g. `google/gemma-4-E4B-it`.
- **Ollama / llama.cpp** — point `OPENAI_API_BASE` at the local server's OpenAI-compatible URL.
- **Custom gateway** — any OpenAI-compatible proxy works.

Users can also override the model/API key/base URL **per trial** in the trial
creation UI, so one deployment can serve multiple endpoints.

### OCR / preprocessing

Preprocessing turns uploaded files into text. Four engines, independently
enabled — at least one must be on for PDF/image handling:

| Engine | Config | Best for |
|---|---|---|
| **Docling-serve** (local) | `DOCLING_SERVE_ENABLED=true`, `DOCLING_SERVE_URL=http://docling-serve:5001` | Default; works offline, no API cost. Runs in its own container (CPU, ~8 GB RAM). |
| **Mistral OCR** (remote or self-hosted) | `MISTRAL_OCR_ENABLED=true`, `MISTRAL_API_BASE`, `MISTRAL_API_KEY` | Complex layouts, tables, forms. Official cloud, or self-hosted DeepSeek-OCR-2 via `compose.deepseek.yml`. |
| **Vision LLM OCR** (remote or self-hosted) | `VISION_OCR_ENABLED=true`, `VISION_OCR_API_BASE`, `VISION_OCR_API_KEY`, `VISION_OCR_MODEL` | Documents needing visual/layout understanding. Any OpenAI-compatible vision model, or self-hosted via `compose.vllm.yml`. |
| **Local Docling fallback** | `DOCLING_LOCAL_FALLBACK=true` (requires `docling-slim` dev dep) | Optional in-process fallback when docling-serve is unreachable. Not in the production image. |

**Behavior:** for PDFs, docling-serve is tried first for embedded text; if too
little is extracted (`DOCLING_MIN_EXTRACTED_CHARS_PDF`, default 100 chars), it
falls back to the configured OCR engine. Users can force OCR per task to skip
the embedded-text probe. Set `REMOTE_OCR_FALLBACK_ENABLED=false` (default) to
keep PHI on local engines — only enable remote OCR fallback deliberately.

**Self-hosted OCR (fully local, GPU):**
```bash
# Local Mistral-compatible OCR (DeepSeek-OCR-2 + KatDocExtract)
docker compose -f compose.yml -f compose.deepseek.yml up -d
# then: MISTRAL_API_BASE=http://ocr-api:8001, MISTRAL_API_KEY=sk-noop

# Local vision LLM via vLLM (e.g. Gemma 4)
docker compose -f compose.yml -f compose.vllm.yml up -d
# then: VISION_OCR_API_BASE=http://vllm:8000/v1, VISION_OCR_MODEL=google/gemma-4-E4B-it
```

Display names shown in the UI are customizable via `*_DISPLAY_NAME` /
`*_DISPLAY_SUBTITLE` (also editable in Admin → Settings).

### File storage

Where uploaded files and preprocessing output live. Two options:

- **RustFS / S3-compatible** (default in compose) — RustFS runs in a container
  with a `minio-data` volume. Configure via `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL`, `S3_BUCKET_NAME`. Any S3-compatible
  service (MinIO, AWS S3, Garage, etc.) works — point `S3_ENDPOINT_URL` at it.
- **Local filesystem** — set `LOCAL_DIRECTORY=/path/to/storage` and leave the
  S3 credentials empty. In compose, mount that path as a volume so files
  survive container recreation, and ensure it's writable by the backend's
  non-root user (UID 10001).

Pick one. Storage is abstracted behind `get_file()`/`save_file()`/`remove_file()`
internally, so switching is just an env change.

### Authentication & SSO (OIDC)

By default, users authenticate with email + password. Account lockout
(`LOGIN_MAX_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES`), a configurable password
policy (`PASSWORD_POLICY_*`), and rotatable refresh tokens
(`REFRESH_TOKEN_EXPIRE_DAYS`) are on by default — see `.env.example` for the
knobs.

**OpenID Connect SSO** is optional and off by default. When enabled, users can
sign in via an external identity provider (Google, Keycloak, Azure AD, etc.) in
addition to local passwords.

1. Enable globally: `SSO_ENABLED=true`.
2. In **Admin → SSO**, add each provider:
   - **Display name** (shown on the "Continue with {name}" button)
   - **Issuer URL** — e.g. `https://accounts.google.com` (discovery is fetched
     from `{issuer}/.well-known/openid-configuration`)
   - **Client ID** + **Client secret** (encrypted at rest; never returned by
     the API)
   - **Scopes** (default `openid email profile`)
3. At the IdP, register the **redirect URI**:
   ```
   {APP_URL}/api/v1/auth/sso/{provider-slug}/callback
   ```
   where `{provider-slug}` is the URL-safe slug derived from the display name
   (shown in the admin panel).

**How it flows:** the login page fetches enabled providers from `/auth/settings`
and renders a button per provider. Clicking it redirects to the IdP; on
callback, the backend exchanges the code (PKCE + signed state), fetches
userinfo, and **just-in-time provisions** the user — linking to an existing
local account by email, or creating a new one (role from
`SSO_JIT_DEFAULT_ROLE`). Tokens are delivered to the frontend via a URL
fragment (never the query string), so they don't leak into server logs or
`Referer` headers.

**Provisioning rules:**
- `SSO_BYPASS_INVITATION=true` (default) — SSO login ignores
  `REQUIRE_INVITATION`; the IdP is the trust source.
- Set `SSO_BYPASS_INVITATION=false` to keep SSO gated by a pre-existing
  invitation/local account.
- Users can link/unlink identities in **Account settings**; the last sign-in
  method can't be removed if the account has no password set (prevents
  lockout).

`SSO_CLIENT_SECRET_ENCRYPTION_KEY` is optional — leave empty to derive the
Fernet key from `SECRET_KEY`; set explicitly only to rotate independently.

### Email (optional)

SMTP is off by default. Enable it (`EMAIL_ENABLED=true` + `SMTP_*`) to send
invitation and password-reset emails. When disabled, invitations fall back to
a manual copy-link flow and password reset surfaces a "contact your admin"
message. See `.env.example` for the SMTP block.

### Site-wide banner (optional)

Show a notice bar at the very top of every page (login and landing pages
included) — e.g. a "Research Use Only!" disclaimer. It is off by default and can
be configured either in `.env` or at runtime in **Admin → Settings → General**.

| Variable | Purpose |
|----------|---------|
| `BANNER_ENABLED` | `true` to show the banner |
| `BANNER_TEXT` | Text displayed in the bar (e.g. `Research Use Only!`) |
| `BANNER_COLOR` | Color scheme: `amber` (default), `red`, `blue`, `green`, or `gray` |

The banner text is served by the unauthenticated public-settings endpoint so it
appears before login. Runtime changes take effect for a user on their next page
load.

---

## Image strategy: pre-built vs. build-from-source

The compose file references `ghcr.io/katherlab/llmaixweb-backend:latest` /
`...-frontend:latest`. By default `docker compose up -d` **pulls** these.

- **Build from source** (e.g. for a fork or unreleased changes):
  ```bash
  docker compose up -d --build
  ```
- **Pin a specific release** (recommended for reproducible prod):
  ```yaml
  # override in a compose.override.yml or edit compose.yml
  image: ghcr.io/katherlab/llmaixweb-backend:v0.4.1
  ```
  Tags follow semver: `:v0.4.1` (exact), `:0.4` (minor), `:latest` (newest
  release), plus `:sha-<commit>` per build.

> The backend Dockerfile bakes the git commit hash into the image via the
> `GIT_COMMIT_HASH` build arg so the running version is visible in the UI
> footer. Pass `-e GIT_COMMIT_HASH=$(git rev-parse HEAD)` when building
> locally for accurate version display.

---

## Compose overlays

`compose.yml` is the base (CPU-only). Layer optional overlays with `-f`:

| Overlay | When to use | GPU |
|---|---|---|
| `compose.dev.yml` | Local dev hot-reload (mounts source, uvicorn reload). **Not for production.** | No |
| `compose.deepseek.yml` | Self-hosted Mistral OCR via DeepSeek-OCR-2 + KatDocExtract | Yes (24+ GB VRAM) |
| `compose.vllm.yml` | Self-hosted OpenAI-compatible vision LLM via vLLM (e.g. Gemma 4) | Yes |

```bash
# CPU-only, remote LLM API
docker compose up -d

# Self-hosted OCR + LLM (fully local, GPU)
docker compose -f compose.yml -f compose.deepseek.yml -f compose.vllm.yml up -d
```

Without the GPU overlays, the app simply talks to whatever remote API you
configured in `.env` — no GPU needed.

---

## Reverse proxy & TLS

The frontend container listens on `:8080` (mapped to host `:5173` by default).
For production, terminate TLS in front of it (nginx, Traefik, Caddy, cloud
LB) and point it at the frontend container.

**Critical env vars when behind a proxy:**
- `APP_URL=https://app.example.com` — must match the public origin (used in
  email links and the SSO callback redirect).
- `BACKEND_CORS_ORIGINS=https://app.example.com` — the public origin.

The in-container nginx already proxies `/api/` and `/ws/` to the backend and
sets `X-Forwarded-*` headers, so the backend sees the real client IP. If your
outer proxy terminates TLS, ensure it also forwards
`X-Forwarded-Proto: https`.

**WebSocket note:** `/ws/activity` carries real-time task progress. If your
outer proxy buffers or times out long-lived connections, raise its read
timeout (the in-container nginx already sets `proxy_read_timeout 86400`).

**Port change:** to expose on a different host port, edit the `frontend`
service in `compose.yml`:
```yaml
ports: ["8443:8080"]
```

---

## Persistent storage

| Volume | Service | Holds |
|---|---|---|
| `pgdata` | postgres | All DB data — projects, users, trials, evaluations |
| `redis-data` | redis | Transient (broker + results + rate-limit counters). Loss is non-fatal. |
| `minio-data` | rustfs | Uploaded files + preprocessing output (when using S3 storage) |

**Back these up.** See [Backups](#backups) below.

**Alternative: local filesystem storage** instead of RustFS/S3 — set
`LOCAL_DIRECTORY=/path/to/storage` and leave S3 credentials empty. In
compose, mount that path as a volume so files survive container recreation.

---

## Backups

### Database (Postgres)
```bash
# Backup
docker compose exec postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup-$(date +%F).sql

# Restore
docker compose exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB" < backup-2026-06-30.sql
```
Replace `$POSTGRES_USER` / `$POSTGRES_DB` with the values from your `.env`
(defaults: `postgres` / `llmaixweb`).

### File storage (RustFS/S3)
RustFS is S3-compatible, so any S3 client works. The compose ships the
`rustfs/rc` client (MinIO-compatible `mc`-style). Example using a one-off
container:
```bash
# Sync the bucket to a local backup directory
docker compose run --rm --entrypoint sh rustfs-init -c '
  rc alias set local http://rustfs:9000 "$RUSTFS_ACCESS_KEY" "$RUSTFS_SECRET_KEY" &&
  rc mirror local/"$S3_BUCKET_NAME" /backup
'
```
Alternatively, point `aws-cli` at the endpoint:
```bash
aws --endpoint-url http://rustfs:9000 s3 sync s3://llmaixweb ./files-backup
```
For `LOCAL_DIRECTORY` storage, back up that directory directly.

### Full stack backup (stop-the-world)
```bash
docker compose stop
# back up pgdata + minio-data volumes + .env
docker compose start
```

---

## Upgrading

1. **Review the release notes** for breaking changes / migration notes.
2. **Back up the database** (see above).
3. **Pull the new images** (or rebuild):
   ```bash
   docker compose pull
   # or, building from source:
   # docker compose build
   ```
4. **Apply:** migrations run **automatically** on backend startup via
   `run_migrations.sh` (with `SKIP_RUNTIME_CHECKS=true` so no OpenAI/S3
   validation blocks the migration).
   ```bash
   docker compose up -d
   docker compose logs -f backend     # confirm "Migrations completed"
   ```
5. **Verify** in the admin panel (footer shows backend + frontend versions +
   commit hashes on hover).

> **Version pinning:** for production, pin image tags to a specific release
> (e.g. `:v0.4.1`) rather than `:latest` so upgrades are intentional. Frontend
> and backend images are independent — you can upgrade them separately, but
> keeping them in sync is recommended.

### Rolling back
If an upgrade fails, the Alembic migrations include `downgrade()` paths:
```bash
# Pin the previous image tag in compose.yml first, then:
docker compose up -d
# Run the downgrade (example: one revision back)
docker compose exec backend sh -c 'SKIP_RUNTIME_CHECKS=true uv run --no-dev alembic downgrade -1'
```
Restoring from a DB backup is the safer rollback path for major versions.

---

## Health checks & monitoring

Stateful services have healthchecks in `compose.yml`:
- **postgres** — `pg_isready`
- **redis** — `redis-cli ping`
- **rustfs** — HTTP health probe
- **docling-serve** — OpenAPI endpoint probe

The **backend** has its own HTTP healthcheck (probing `/`) and `depends_on` the
above being healthy (plus `rustfs-init` completing) before it starts — so once
the backend reports healthy, both it and its dependencies are ready. The
**frontend** waits for the backend to be healthy before starting.

```bash
docker compose ps                  # health column
docker compose logs -f backend     # app logs
docker compose logs -f worker_default worker_preprocess   # task logs
```

**Admin UI observability:**
- **Admin → Celery** — live worker stats, queue depth, active/failed tasks,
  task revocation.
- **Admin → Settings** — runtime config (OCR engines, password policy, SSO,
  etc.) with live validation; changes apply without restart via the
  `dynamic_settings` cache (broadcast to workers over Redis).
- **Navbar activity bell** — real-time preprocessing/trial progress
  (WebSocket).

---

## Security checklist (production)

- [ ] `SECRET_KEY` set to a strong random value (app refuses to start without it).
- [ ] `APP_URL` and `BACKEND_CORS_ORIGINS` set to your real public origin.
- [ ] Default `RUSTFS_ACCESS_KEY` / `RUSTFS_SECRET_KEY` / postgres password
      changed from the compose defaults.
- [ ] TLS terminated in front of the app.
- [ ] `ALLOW_FIRST_ADMIN_SETUP=false` after the first admin exists (prevents
      the bootstrap endpoint).
- [ ] `REQUIRE_INVITATION=true` if you want signup gated by invitations.
- [ ] Password policy + account lockout tuned to your org (see `.env.example`
      `PASSWORD_POLICY_*` / `LOGIN_*`).
- [ ] SSO configured in Admin → SSO only if needed (`SSO_ENABLED=true`);
      provider client secrets are encrypted at rest.
- [ ] `.env` never committed (it's gitignored) and backed up securely.
- [ ] Keep PHI on self-hosted/local providers unless you've explicitly chosen
      a remote one.
- [ ] **Encryption at rest provided by the infrastructure** — the app stores
      document text and uploaded files in plaintext; use an encrypted DB volume
      and encrypted object storage (see [docs/DATA_FLOW.md](docs/DATA_FLOW.md)).
- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES` shortened for PHI (e.g. 30–60; refresh
      rotation covers longer sessions).
- [ ] `LOG_FORMAT=json` and container stdout shipped to your SIEM/Loki; forward
      the audit log too (see [docs/AUDIT_LOGGING.md](docs/AUDIT_LOGGING.md)).
- [ ] Admins know the **Audit Log** tab (Admin → Audit Log) and the
      error-id lookup for supporting users who report an error id.
- [ ] Reviewed the clinical hardening docs: [docs/SECURITY.md](docs/SECURITY.md),
      [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md),
      [docs/RISK_REGISTER.md](docs/RISK_REGISTER.md),
      [docs/DATA_RETENTION.md](docs/DATA_RETENTION.md).

---

## Troubleshooting

See the [Troubleshooting](https://katherlab.github.io/llmaixweb/operations/troubleshooting/) guide for
common issues (port conflicts, backend startup failures, LLM connection
errors, migration errors, stuck Celery tasks).

### Reset everything (⚠️ destroys all data)
```bash
docker compose down -v        # removes pgdata + minio-data + redis-data
docker compose up -d
```

### Inspect a running backend
```bash
# Shell into the backend container
docker compose exec backend sh
# Run a one-off alembic command
docker compose exec backend sh -c 'SKIP_RUNTIME_CHECKS=true uv run --no-dev alembic current'
```

### Storage not writable
If using `LOCAL_DIRECTORY`, the path must exist and be writable by the
backend container's non-root user (UID 10001). Mount it as a volume and
`chown 10001:10001` it on the host.

---

## Further reading

- [README.md](README.md) — quickstart, feature overview, preprocessing guide
- [DEVELOPER.md](DEVELOPER.md) — local dev setup, testing, architecture notes
- [AGENTS.md](AGENTS.md) — codebase guide and conventions
- [.env.example](.env.example) — full environment variable reference
