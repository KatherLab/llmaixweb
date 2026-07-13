// Frontend version - update this on each release
// Note: Also bump version in pyproject.toml for backend
export const frontendVersion = '0.6.4'
// Git commit hash - injected at build time via VITE_GIT_COMMIT_HASH
export const frontendGitCommit = import.meta.env.VITE_GIT_COMMIT_HASH || 'unknown'
