from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from backend.src.models import PreprocessingTask
from ....dependencies import get_db
from ....core.security import get_admin_user
from ....models import AppSetting
from ....celery.celery_config import celery_app
from ....core.config import Settings, SETTINGS_META
from ....core.dynamic_settings import (
    reload_settings_cache,
    get_settings,
)

from celery.result import AsyncResult

router = APIRouter()


# --------------------------
# Settings endpoints
# --------------------------

@router.get("/settings")
def read_settings(current_user=Depends(get_admin_user), db: Session = Depends(get_db)):
    db_rows = db.query(AppSetting).all()
    db_overrides = {row.key: row.value for row in db_rows}
    env_defaults = Settings().model_dump()
    result = {}

    for key, meta in SETTINGS_META.items():
        readonly = meta.get("readonly", False)
        secret = meta.get("secret", False)
        category = meta.get("category", "General")
        label = meta.get("label", key)
        typ = meta.get("type", "str")
        value = db_overrides.get(key) if key in db_overrides else env_defaults.get(key)
        show_original = None if secret else env_defaults.get(key)
        show_override = None if secret else db_overrides.get(key)
        show_effective = None if secret else value
        # for secrets, only say if set or not
        result[key] = {
            "key": key,
            "category": category,
            "label": label,
            "description": meta.get("description", ""),
            "type": typ,
            "readonly": readonly,
            "secret": secret,
            "is_set": bool(value) if secret else None,
            "original": show_original,
            "override": show_override,
            "effective": show_effective,
            "overridden": (not readonly) and (key in db_overrides),
        }
    return result

@router.put("/settings")
def update_settings(
    updates: dict = Body(...),
    current_user=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    for key, value in updates.items():
        meta = SETTINGS_META.get(key)
        if not meta or meta.get("readonly", False):
            raise HTTPException(400, f"Cannot edit setting: {key}")
        if meta.get("secret", False):
            raise HTTPException(400, f"Cannot update secret settings here.")
        # Validation
        typ = meta.get("type")
        try:
            if typ == "int":
                value = int(value)
            elif typ == "bool":
                if isinstance(value, bool):
                    pass
                elif str(value).lower() in ("true", "1", "yes"):
                    value = True
                elif str(value).lower() in ("false", "0", "no"):
                    value = False
                else:
                    raise ValueError()
            else:
                value = str(value)
        except Exception:
            raise HTTPException(422, f"Invalid value for {key}: {value}")
        # Only store if overridden
        original = getattr(Settings(), key)
        if str(value) == str(original):
            row = db.get(AppSetting, key)
            if row:
                db.delete(row)
        else:
            row = db.get(AppSetting, key)
            if row:
                row.value = str(value)
            else:
                db.add(AppSetting(key=key, value=str(value)))
    db.commit()
    reload_settings_cache()
    return {"updated": True}

@router.delete("/settings/{key}")
def delete_setting(
    key: str,
    current_user=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    meta = SETTINGS_META.get(key)
    if not meta or meta.get("readonly", False):
        raise HTTPException(400, f"Cannot delete setting: {key}")
    row = db.get(AppSetting, key)
    if not row:
        raise HTTPException(status_code=404, detail="Setting not found")
    db.delete(row)
    db.commit()
    reload_settings_cache()
    return {"deleted": key}

# --------------------------
# Celery endpoints
# --------------------------

@router.get("/celery/workers")
def get_celery_workers(current_user=Depends(get_admin_user)):
    """Show Celery worker stats and health."""
    i = celery_app.control.inspect()
    return {
        "active": i.active(),
        "registered": i.registered(),
        "stats": i.stats(),
        "ping": i.ping(),
    }

@router.get("/celery/queues")
def get_celery_queues(current_user=Depends(get_admin_user)):
    """Show queue/task status."""
    i = celery_app.control.inspect()
    return {
        "reserved": i.reserved(),
        "scheduled": i.scheduled(),
        "active": i.active(),
    }

@router.get("/celery/tasks/{task_id}")
def get_task_status(task_id: str, current_user=Depends(get_admin_user)):
    """Get task status/result."""
    result = AsyncResult(task_id, app=celery_app)
    out = {
        "id": result.id,
        "status": result.status,
        "result": str(result.result)[:500],  # Avoid huge output
        "traceback": getattr(result, "traceback", None),
    }
    return out

@router.post("/celery/revoke/{task_id}")
def revoke_task(
    task_id: str,
    terminate: bool = False,
    current_user=Depends(get_admin_user)
):
    """Revoke (cancel) a running celery task."""
    celery_app.control.revoke(task_id, terminate=terminate)
    return {"revoked": task_id, "terminate": terminate}

# (Optional) List failed tasks from your DB (example below assumes PreprocessingTask table)
@router.get("/celery/failed-tasks")
def get_failed_tasks(
    current_user=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    failed = db.query(PreprocessingTask).filter(PreprocessingTask.status == 'failed').all()
    # Format as desired
    return [{"id": t.id, "message": t.message, "started_at": t.started_at, "completed_at": t.completed_at} for t in failed]
