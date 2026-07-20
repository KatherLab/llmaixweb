# Contributing

Contributions are welcome. This page covers the essentials; the
[Developer guide](developer-guide.md) and [Architecture](architecture.md) pages
cover setup and code structure in depth.

## Before you start

- LLMAIx Web is licensed under **AGPL-3.0-or-later**. By contributing you agree
  that your contributions are licensed under the same terms.
- For anything non-trivial, open an issue first to discuss the approach.
- Do not include real patient data in issues, tests, or fixtures.

## Development setup

See the [Developer guide](developer-guide.md) for running the stack from source
with hot-reload.

## Quality gates

All checks must pass before a change is merged.

**Frontend:**

```bash
npm run check    # prettier --check + eslint + vue-tsc --noEmit (0 errors required)
npm run build    # must build cleanly
```

A pre-commit hook auto-runs `lint-staged` (eslint + prettier) on staged files.

**Backend:**

```bash
uv run ruff check backend/src/
uv run ruff format backend/src/
```

**Tests:**

```bash
# Backend (pytest)
ENV_PATH=backend/.env.localtest uv run pytest --verbose

# Frontend (Vitest — utils/ helpers and composables)
npm test
```

## Conventions

- **Backend** — `snake_case` for files/functions/variables, `PascalCase` for
  models and Pydantic schemas. API routes use plural nouns.
- **Frontend** — `PascalCase.vue` components, `camelCase` variables. Build
  modals on `BaseModal`, call the API through `services/*Api.ts` (never the raw
  axios instance), and reuse the shared `composables/` and `components/common/`
  primitives. See the [Architecture](architecture.md) page for the full list.
- **Types** — hand-written TypeScript domain types in `frontend/types/`
  (`@/types`) mirror the backend Pydantic schemas; keep them in sync when you
  change an API.

## Database migrations

When you change a model, generate an Alembic migration:

```bash
SKIP_RUNTIME_CHECKS=true uv run alembic revision --autogenerate -m "describe change"
```

Review the generated migration (including the `downgrade`) before committing.

## Security

Never open a public issue for a security vulnerability — follow the
[security policy](https://github.com/KatherLab/llmaixweb/security/policy)
instead.
