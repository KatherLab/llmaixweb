# backend/src/_version.py
"""Backend version information."""

import os
import re


def get_version() -> str:
    """Get the backend version from pyproject.toml.

    Reads version directly from pyproject.toml since the package
    may not be installed (uv sync only installs dependencies).
    """
    # Find pyproject.toml relative to this file
    # In Docker: /app/backend/src/_version.py -> /app/pyproject.toml
    # Locally: backend/src/_version.py -> pyproject.toml
    current_dir = os.path.dirname(os.path.realpath(__file__))
    pyproject_path = os.path.join(current_dir, "..", "..", "pyproject.toml")

    try:
        with open(pyproject_path, "r") as f:
            content = f.read()

        # Match version = "x.y.z" in [project] section
        match = re.search(
            r'^\[project\].*?^version\s*=\s*["\']([^"\']+)["\']',
            content,
            re.MULTILINE | re.DOTALL,
        )
        if match:
            return match.group(1)
    except (FileNotFoundError, IOError):
        pass

    return "unknown"


def get_git_commit() -> str:
    """Get the git commit hash from build-time environment variable or file.

    For GitHub Actions built images: returns the commit hash from GIT_COMMIT_HASH
    environment variable (set during Docker build).

    For local builds: returns "unknown" since there may be uncommitted changes.
    """
    import os

    # Try environment variable first (set during Docker build by GitHub Actions)
    commit = os.getenv("GIT_COMMIT_HASH")
    if commit:
        return commit

    # Try reading from file (written during build)
    try:
        version_file = os.path.join(os.path.dirname(__file__), "_git_commit.txt")
        with open(version_file) as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        pass

    # For local builds, return "unknown" rather than checking git
    # (local changes may exist after the commit)
    return "unknown"
