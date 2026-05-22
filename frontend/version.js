// Frontend version - auto-synced from root package.json via update-version.js (prebuild)
// Note: Also bump version in pyproject.toml for backend, then run `uv lock`
export const frontendVersion = '0.2.3';
// Git commit hash - injected at build time via VITE_GIT_COMMIT_HASH
export const frontendGitCommit = import.meta.env.VITE_GIT_COMMIT_HASH || 'unknown';
