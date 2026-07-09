# backend/src/core/dynamic_settings.py
import logging
from functools import lru_cache
from typing import cast

from sqlalchemy.exc import SQLAlchemyError
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
    except SQLAlchemyError:
        # Table doesn't exist yet (e.g., during tests or first run). Postgres
        # raises ProgrammingError (not OperationalError) for a missing table,
        # so catch the broad SQLAlchemyError base class.
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
    # Always apply (even when empty) so that removing the last override resets
    # the live singleton back to its env/.env base instead of retaining stale
    # values from a previous override.
    try:
        apply_runtime_overrides(overrides)
    except Exception as e:
        # Don't let an invalid override value break settings access —
        # fall back to the existing (base) instance.
        logger.warning("Failed to apply runtime settings overrides: %s", e)
    return cast(Settings, _settings_proxy)


def reload_settings_cache(broadcast: bool = True) -> None:
    """Clear the dynamic settings cache and reapply DB overrides.

    Clears the ``lru_cache`` on :func:`get_settings` and re-runs it so that
    fresh DB overrides are applied to the shared config singleton. Because
    ``settings`` everywhere is a proxy to that singleton, the new values
    propagate to all modules (including those that bound ``settings`` at
    import time).

    When ``broadcast`` is True (default), also publishes a cache-invalidation
    message over Redis so that Celery worker processes — which run in separate
    processes with their own ``@lru_cache`` and never see the web process's
    cache clear — reload their own cached settings. Without this, admin config
    changes (e.g. disabling a remote OCR engine) wouldn't take effect in
    workers until a restart. The worker-side subscriber calls this with
    ``broadcast=False`` to avoid a re-broadcast loop.
    """
    get_settings.cache_clear()
    # Re-trigger override application to the shared singleton.
    get_settings()

    if broadcast:
        try:
            from ..utils.redis_broadcast import publish_settings_invalidate

            publish_settings_invalidate()
        except Exception as e:
            # Best-effort: if Redis is down, workers stay stale until restart.
            logger.debug("Could not broadcast settings invalidation: %s", e)
