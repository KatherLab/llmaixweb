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
