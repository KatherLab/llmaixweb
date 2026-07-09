# backend/src/routers/v1/endpoints/audit.py
"""Admin-only, read-only API over the audit trail and central error log.

There is deliberately no create/update/delete surface here — the audit trail is
append-only and populated exclusively by the application via
``utils.audit.record_audit`` and the global exception handler.
"""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ....core.security import get_admin_user
from ....dependencies import get_db
from ....models.audit import AuditLog, ErrorLog
from ....schemas.audit import (
    AuditLogEntry,
    ErrorLogEntry,
    PaginatedAuditLogs,
    PaginatedErrorLogs,
)
from ....utils.enums import AuditAction, AuditOutcome

router = APIRouter()


def _apply_audit_filters(
    stmt,
    *,
    action: AuditAction | None,
    outcome: AuditOutcome | None,
    actor_user_id: int | None,
    resource_type: str | None,
    project_id: int | None,
    request_id: str | None,
    start: datetime | None,
    end: datetime | None,
):
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if outcome is not None:
        stmt = stmt.where(AuditLog.outcome == outcome)
    if actor_user_id is not None:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if project_id is not None:
        stmt = stmt.where(AuditLog.project_id == project_id)
    if request_id:
        stmt = stmt.where(AuditLog.request_id == request_id)
    if start is not None:
        stmt = stmt.where(AuditLog.created_at >= start)
    if end is not None:
        stmt = stmt.where(AuditLog.created_at <= end)
    return stmt


@router.get("/audit", response_model=PaginatedAuditLogs)
def list_audit_logs(
    action: AuditAction | None = None,
    outcome: AuditOutcome | None = None,
    actor_user_id: int | None = None,
    resource_type: str | None = None,
    project_id: int | None = None,
    request_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> PaginatedAuditLogs:
    filters = dict(
        action=action,
        outcome=outcome,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        project_id=project_id,
        request_id=request_id,
        start=start,
        end=end,
    )
    count_stmt = _apply_audit_filters(
        select(func.count()).select_from(AuditLog), **filters
    )
    total = db.execute(count_stmt).scalar_one()
    rows_stmt = _apply_audit_filters(select(AuditLog), **filters)
    rows = (
        db.execute(
            rows_stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return PaginatedAuditLogs(
        total=total,
        limit=limit,
        offset=offset,
        items=[AuditLogEntry.model_validate(r) for r in rows],
    )


@router.get("/audit/export")
def export_audit_logs(
    action: AuditAction | None = None,
    outcome: AuditOutcome | None = None,
    actor_user_id: int | None = None,
    resource_type: str | None = None,
    project_id: int | None = None,
    request_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    max_rows: int = Query(50000, ge=1, le=200000),
    current_user=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Stream the (filtered) audit trail as CSV. The export itself is audited."""
    from ....utils.audit import record_audit

    filters = dict(
        action=action,
        outcome=outcome,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        project_id=project_id,
        request_id=request_id,
        start=start,
        end=end,
    )
    stmt = (
        _apply_audit_filters(select(AuditLog), **filters)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(max_rows)
    )

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "id",
                "created_at",
                "actor_user_id",
                "actor_email",
                "actor_ip",
                "action",
                "resource_type",
                "resource_id",
                "project_id",
                "outcome",
                "request_id",
                "detail",
            ]
        )
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)
        for r in db.execute(stmt).scalars().yield_per(500):
            writer.writerow(
                [
                    r.id,
                    r.created_at.isoformat() if r.created_at else "",
                    r.actor_user_id or "",
                    r.actor_email or "",
                    r.actor_ip or "",
                    r.action.value if r.action else "",
                    r.resource_type or "",
                    r.resource_id or "",
                    r.project_id or "",
                    r.outcome.value if r.outcome else "",
                    r.request_id or "",
                    r.detail if r.detail is not None else "",
                ]
            )
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    record_audit(
        AuditAction.EXPORT,
        actor=current_user,
        resource_type="audit_log",
        detail={
            "format": "csv",
            "filters": {k: str(v) for k, v in filters.items() if v is not None},
        },
    )
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit-log.csv"'},
    )


@router.get("/errors", response_model=PaginatedErrorLogs)
def list_error_logs(
    error_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> PaginatedErrorLogs:
    """List server errors, or look up a single one by the id a user reported."""
    stmt = select(ErrorLog)
    count_stmt = select(func.count()).select_from(ErrorLog)
    if error_id:
        stmt = stmt.where(ErrorLog.error_id == error_id)
        count_stmt = count_stmt.where(ErrorLog.error_id == error_id)
    total = db.execute(count_stmt).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(ErrorLog.created_at.desc(), ErrorLog.id.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return PaginatedErrorLogs(
        total=total,
        limit=limit,
        offset=offset,
        items=[ErrorLogEntry.model_validate(r) for r in rows],
    )
