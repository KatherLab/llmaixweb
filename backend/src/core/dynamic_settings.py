# backend/src/core/dynamic_settings.py
from functools import lru_cache

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# Use absolute imports for reliability across different run contexts
try:
    from .config import SETTINGS_META, Settings
except ImportError:
    from backend.src.core.config import SETTINGS_META, Settings

try:
    from .session import SessionLocal
except ImportError:
    from backend.src.db.session import SessionLocal

try:
    from ..models import AppSetting
except ImportError:
    from backend.src.models import AppSetting


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
    with SessionLocal() as db:
        overrides = get_db_overrides(db)
        return Settings(**overrides)


def reload_settings_cache():
    """Clear the dynamic settings cache and the config module's cached instance."""
    get_settings.cache_clear()

    # Also clear the cached instance in config.py
    try:
        import backend.src.core.config as config_module

        config_module._settings_instance = None
    except (ImportError, AttributeError):
        try:
            from . import config as config_module

            config_module._settings_instance = None
        except (ImportError, AttributeError):
            pass  # Ignore if we can't import (e.g., during startup)
