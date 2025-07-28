from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from backend.src.models import PreprocessingTask
from ....dependencies import get_db
from ....core.security import get_admin_user
from ....models import AppSetting
from ....celery.celery_config import celery_app

from celery.result import AsyncResult

router = APIRouter()


# --------------------------
# Settings endpoints
# --------------------------

@router.get("/settings")
def read_settings(
    current_user=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get all application settings (admin only)."""
    rows = db.query(AppSetting).all()
    return {row.key: row.value for row in rows}

@router.get("/settings/{key}")
def read_setting(
    key: str,
    current_user=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    row = db.get(AppSetting, key)
    if not row:
        raise HTTPException(status_code=404, detail="Setting not found")
    return {row.key: row.value}

@router.put("/settings")
def update_settings(
    updates: dict = Body(...),
    current_user=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    for key, value in updates.items():
        row = db.get(AppSetting, key)
        if row:
            row.value = str(value)
        else:
            row = AppSetting(key=key, value=str(value))
            db.add(row)
    db.commit()
    return {"updated": True}

@router.put("/settings/{key}")
def update_single_setting(
    key: str,
    value: str = Body(..., embed=True),
    current_user=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    row = db.get(AppSetting, key)
    if row:
        row.value = value
    else:
        row = AppSetting(key=key, value=value)
        db.add(row)
    db.commit()
    return {key: value}

@router.delete("/settings/{key}")
def delete_setting(
    key: str,
    current_user=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    row = db.get(AppSetting, key)
    if not row:
        raise HTTPException(status_code=404, detail="Setting not found")
    db.delete(row)
    db.commit()
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
