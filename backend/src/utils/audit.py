# backend/src/utils/audit.py
"""Service for writing the append-only audit trail.

Design choices:

* **Independent session.** Each audit row is written in its own short-lived
  session and committed immediately, so a later rollback of the business
  transaction never discards the record, and an audit-write failure never rolls
  back the caller's work. For mutations, call :func:`record_audit` *after* the
  business commit so the trail reflects what actually persisted.
* **Never raises.** Auditing is best-effort from the caller's perspective: a
  failure to write the trail is logged but does not break the request. (In a
  hardened deployment the mirror-to-SIEM option would catch these; see the
  roadmap.)
* **PHI-free.** ``detail`` must contain only ids, counts, names, hosts — never
  document text or extracted values.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..db.session import SessionLocal
from ..models.audit import AuditLog
from ..utils.enums import AuditAction, AuditOutcome
from ..utils.request_context import get_client_ip, get_request_id

if TYPE_CHECKING:
    from ..models.user import User

logger = logging.getLogger(__name__)


def record_audit(
    action: AuditAction,
    *,
    actor: "User | None" = None,
    actor_email: str | None = None,
    resource_type: str | None = None,
    resource_id: str | int | None = None,
    project_id: int | None = None,
    outcome: AuditOutcome = AuditOutcome.SUCCESS,
    detail: dict | None = None,
) -> None:
    """Write one audit row. Best-effort; swallows and logs its own errors.

    ``actor`` (a ``User``) is snapshotted to ``actor_user_id`` + ``actor_email``.
    For unauthenticated events (e.g. a failed login) pass ``actor_email`` alone.
    The request id and client IP are pulled from the request context.
    """
    try:
        actor_id = getattr(actor, "id", None)
        email = actor_email or getattr(actor, "email", None)
        row = AuditLog(
            actor_user_id=actor_id,
            actor_email=email,
            actor_ip=get_client_ip(),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            project_id=project_id,
            outcome=outcome,
            detail=detail,
            request_id=get_request_id(),
        )
        with SessionLocal() as db:
            db.add(row)
            db.commit()
    except Exception:  # pragma: no cover - audit must never break a request
        logger.exception(
            "Failed to write audit log (action=%s, resource=%s:%s)",
            getattr(action, "value", action),
            resource_type,
            resource_id,
        )
