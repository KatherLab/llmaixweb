from functools import lru_cache
from sqlalchemy.orm import Session
from backend.src.core.config import Settings, SETTINGS_META
from backend.src.models import AppSetting
from backend.src.db.session import SessionLocal

def get_db_overrides(db: Session) -> dict:
    rows = db.query(AppSetting).all()
    # Only load overrides for non-readonly settings
    return {row.key: row.value for row in rows if not SETTINGS_META.get(row.key, {}).get("readonly", False)}

@lru_cache()
def get_settings() -> Settings:
    with SessionLocal() as db:
        overrides = get_db_overrides(db)
        return Settings(**overrides)

def reload_settings_cache():
    get_settings.cache_clear()
