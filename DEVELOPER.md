# Developer Guide

## Version Management

This project uses separate versioning for frontend and backend components.

### Version Locations

| Component | Version File | Exposed Via |
|-----------|-------------|-------------|
| Frontend | `frontend/version.js` | Displayed in footer |
| Backend | `pyproject.toml` (llmaix package) | `/api/v1/version` endpoint |

### Current Versions

- **Frontend**: `frontend/version.js` → `export const frontendVersion = '0.0.2'`
- **Backend**: `pyproject.toml` → `version = "0.1.3"` (llmaix package version)

### Git Commit Hash

Both frontend and backend display their git commit hashes:

- **Frontend**: Injected at build time via `GIT_COMMIT_HASH` build arg
- **Backend**: Read at runtime via `git rev-parse --short HEAD`

**Hover over the version in the footer** to see the commit hash.

### Release Checklist

When making a release:

1. **Update frontend version** in `frontend/version.js`:
   ```javascript
   export const frontendVersion = '0.0.3';  // bump version
   ```

2. **Update backend version** in `pyproject.toml`:
   ```toml
   [project]
   version = "0.1.4"  // bump version
   ```

3. **Build and push images** (handled by GitHub Actions on release tag)

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

## 📦 RustFS Storage (Optional)

Start the RustFS server for local development:

```bash
rustfs server llmaixwebdata
```

---

## 👥 Initialize Users

```bash
python -m backend.scripts.populate_users
```

**When using Docker:**

```bash
# Running stack
docker compose -f compose.gpu.yml exec -it backend \
  python -m backend.scripts.populate_users

# Stopped stack
docker compose -f compose.gpu.yml run --rm -it backend \
  python -m backend.scripts.populate_users
```
