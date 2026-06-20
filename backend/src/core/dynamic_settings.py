# backend/src/core/dynamic_settings.py
import logging
from functools import lru_cache

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# Use absolute imports for reliability across different run contexts
try:
    from .config import SETTINGS_META, Settings

    _config_module_name = __name__.replace("dynamic_settings", "config")
except ImportError:
    from backend.src.core.config import SETTINGS_META, Settings

    _config_module_name = "backend.src.core.config"

try:
    from .session import SessionLocal
except ImportError:
    from backend.src.db.session import SessionLocal

try:
    from ..models import AppSetting
except ImportError:
    from backend.src.models import AppSetting

logger = logging.getLogger(__name__)


def get_db_overrides(db: Session) -> dict:
    try:
        rows = db.query(AppSetting).all()
        # Only load overrides for non-readonly settings
        return {
            row.key: row.value
            for row in rows
            if not SETTINGS_META.get(row.key, {}).get("readonly", False)
        }
    except OperationalError:
        # Table doesn't exist yet (e.g., during tests or first run)
        return {}


@lru_cache()
def get_settings() -> Settings:
    """Return the live settings proxy, applying DB overrides to the singleton.

    Returns the module-level proxy from ``core.config`` (not a concrete
    instance) so that ``settings = get_settings()`` bindings reflect runtime
    overrides applied here and by :func:`reload_settings_cache`, instead of
    freezing the instance at import time. Overrides are applied to the shared
    singleton (via ``config.apply_runtime_overrides``) on first load and on
    each reload; the ``lru_cache`` ensures the DB is only queried once per
    cache lifetime.
    """
    from .config import apply_runtime_overrides
    from .config import settings as _settings_proxy

    with SessionLocal() as db:
        overrides = get_db_overrides(db)
    if overrides:
        try:
            apply_runtime_overrides(overrides)
        except Exception as e:
            # Don't let an invalid override value break settings access —
            # fall back to the existing (base) instance.
            logger.warning("Failed to apply runtime settings overrides: %s", e)
    return _settings_proxy


def reload_settings_cache():
    """Clear the dynamic settings cache and reapply DB overrides.

    Clears the ``lru_cache`` on :func:`get_settings` and re-runs it so that
    fresh DB overrides are applied to the shared config singleton. Because
    ``settings`` everywhere is a proxy to that singleton, the new values
    propagate to all modules (including those that bound ``settings`` at
    import time).
    """
    get_settings.cache_clear()
    # Re-trigger override application to the shared singleton.
    get_settings()
