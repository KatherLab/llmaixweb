# backend/src/routers/v1/endpoints/admin.py
from celery.result import AsyncResult
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.src.models import PreprocessingTask

from ....celery.celery_config import celery_app
from ....core.config import SETTINGS_META, Settings
from ....core.dynamic_settings import reload_settings_cache
from ....core.security import get_admin_user
from ....dependencies import get_db
from ....models import AppSetting
from ....utils.audit import record_audit
from ....utils.crypto import encrypt
from ....utils.enums import AuditAction

router = APIRouter()

# Env-only defaults (no DB overrides), computed once. Constructed with
# SKIP_RUNTIME_CHECKS=True so it never performs OpenAI/S3 network validation
# or sys.exit() — those run once at app startup via the settings proxy. Doing
# this per-request (Settings()) previously re-ran validation on every admin
# settings read/update and could crash the worker on a transient API outage.
_ENV_DEFAULTS: dict = Settings(SKIP_RUNTIME_CHECKS=True).model_dump()


# --------------------------
# Settings endpoints
# --------------------------


@router.get("/settings")
def read_settings(current_user=Depends(get_admin_user), db: Session = Depends(get_db)):
    db_rows = db.query(AppSetting).all()
    db_overrides = {row.key: row.value for row in db_rows}
    env_defaults = _ENV_DEFAULTS
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
    db: Session = Depends(get_db),
):
    for key, value in updates.items():
        meta = SETTINGS_META.get(key)
        if not meta or meta.get("readonly", False):
            raise HTTPException(400, f"Cannot edit setting: {key}")
        if meta.get("secret", False):
            # Secret overrides are stored ENCRYPTED at rest (Fernet) and never
            # compared against the env default (we can't read the env secret
            # back here, and we must not persist it in plaintext). An empty
            # value clears the override, reverting to the env/.env value.
            secret_value = str(value)
            row = db.get(AppSetting, key)
            if not secret_value:
                if row:
                    db.delete(row)
            else:
                encrypted = encrypt(secret_value)
                if row:
                    row.value = encrypted
                else:
                    db.add(AppSetting(key=key, value=encrypted))
            continue
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
        # Only store if overridden. Canonicalize bool storage to lowercase
        # "true"/"false" so it round-trips consistently — Python's str(True) is
        # "True", which the frontend's lowercase comparison would parse as false.
        original = _ENV_DEFAULTS.get(key)
        if typ == "bool":
            stored_value = "true" if value else "false"
            original_str = "true" if original else "false"
        else:
            stored_value = str(value)
            original_str = str(original)
        if stored_value == original_str:
            row = db.get(AppSetting, key)
            if row:
                db.delete(row)
        else:
            row = db.get(AppSetting, key)
            if row:
                row.value = stored_value
            else:
                db.add(AppSetting(key=key, value=stored_value))
    db.commit()
    reload_settings_cache()
    # Audit the keys changed (never the values — some are security-relevant).
    record_audit(
        AuditAction.SETTING_CHANGE,
        actor=current_user,
        resource_type="app_setting",
        detail={"keys": list(updates.keys())},
    )
    return {"updated": True}


@router.delete("/settings/{key}")
def delete_setting(
    key: str, current_user=Depends(get_admin_user), db: Session = Depends(get_db)
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
    record_audit(
        AuditAction.SETTING_CHANGE,
        actor=current_user,
        resource_type="app_setting",
        detail={"deleted_key": key},
    )
    return {"deleted": key}


# --------------------------
# Celery endpoints
# --------------------------


@router.get("/celery/workers")
def get_celery_workers(current_user=Depends(get_admin_user)):
    """Show Celery worker stats and health."""
    assert celery_app is not None  # guarded by INITIALIZE_CELERY at startup
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
    assert celery_app is not None  # guarded by INITIALIZE_CELERY at startup
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
    task_id: str, terminate: bool = False, current_user=Depends(get_admin_user)
):
    """Revoke (cancel) a running celery task."""
    assert celery_app is not None  # guarded by INITIALIZE_CELERY at startup
    celery_app.control.revoke(task_id, terminate=terminate)
    return {"revoked": task_id, "terminate": terminate}


# (Optional) List failed tasks from your DB (example below assumes PreprocessingTask table)
@router.get("/celery/failed-tasks")
def get_failed_tasks(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    failed = (
        db.query(PreprocessingTask)
        .filter(PreprocessingTask.status == "failed")
        .order_by(PreprocessingTask.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    # Format as desired
    return [
        {
            "id": t.id,
            "message": t.message,
            "started_at": t.started_at,
            "completed_at": t.completed_at,
        }
        for t in failed
    ]
