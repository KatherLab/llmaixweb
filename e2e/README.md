# End-to-end tests (Playwright)

A single browser-driven **smoke test** of the core workflow:

```
login / first-admin → create project → upload CSV → configure row-by-row import
→ preprocess → documents → schema → prompt → trial → evaluation
```

It proves the whole stack wires together and the money path produces results —
it is intentionally shallow, not exhaustive.

## How it runs

`playwright.config.ts` boots three servers (via Playwright's `webServer`):

| Server | Port | What |
|---|---|---|
| Fake OpenAI LLM | 9099 | `e2e/support/fake-llm.mjs` — canned `/v1/models` + `/v1/chat/completions` |
| Backend (FastAPI) | 8000 | broker-free: SQLite + local storage, `DISABLE_CELERY`, LLM check skipped (`backend/.env.e2e`) |
| Frontend (Vite dev) | 3000 | the app; its dev API base URL is hardcoded to `localhost:8000` |

Deterministic and offline: no Redis, no Postgres, no OCR, no real LLM.

The UI never exposes `bypass_celery`, and the backend runs broker-free, so the
two async *executions* (preprocessing, the trial) and the ground-truth /
evaluation setup are driven through the admin API with `bypass_celery: true`
(synchronous, in-process). Everything else — login, project, upload,
import-config, schema, prompt, and all result assertions — is driven through the
browser. See `e2e/support/api.ts` for the API-side helpers.

## Running locally

```bash
npm run test:e2e        # resets backend state, then runs headless
npm run test:e2e:ui     # interactive Playwright UI mode
```

Prerequisites: `uv` (backend deps installed via `uv sync`), Node deps
(`npm ci`), and the Chromium browser (`npx playwright install chromium`).

`test:e2e` runs `e2e/support/reset.mjs` first, which deletes the ephemeral
`e2e_test.db` and `e2e_local_storage/` so every run starts from a clean
first-admin state. The backend server is never reused, so **stop any dev backend
already on port 8000** before running (the run will otherwise fail fast).

## Files

- `playwright.config.ts` — config + the three `webServer` entries (repo root)
- `backend/.env.e2e` — broker-free backend env for the run
- `e2e/support/fake-llm.mjs` — the fake OpenAI-compatible server
- `e2e/support/reset.mjs` — pre-run state reset
- `e2e/support/api.ts` — API helpers, the 8-field schema, and field mappings
- `e2e/tests/workflow.spec.ts` — the smoke test
