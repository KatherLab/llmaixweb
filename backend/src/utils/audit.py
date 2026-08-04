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
import threading
import time
from collections import OrderedDict
from typing import TYPE_CHECKING

from ..db.session import SessionLocal
from ..models.audit import AuditLog
from ..utils.enums import AuditAction, AuditOutcome
from ..utils.request_context import get_client_ip, get_request_id, get_request_route

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


# ───────────────────────── Denied access ─────────────────────────
#
# Denials are the one audit event an unauthenticated-ish caller can trigger at
# will: nothing rate-limits a client that hammers a 403 endpoint in a loop, and
# one INSERT per attempt would let it inflate a table that is deliberately hard
# to prune. So identical denials collapse into one row per window.
#
# The throttle is per process (a ContextVar-free module global), so with N API
# workers a persistent prober yields at most N rows per window instead of one —
# still bounded, and the burst is itself the signal you want to see.

_DENIAL_THROTTLE_SECONDS = 60.0
_DENIAL_CACHE_MAX = 2048
_recent_denials: "OrderedDict[tuple, float]" = OrderedDict()
_denial_lock = threading.Lock()


def _claim_denial_slot(key: tuple) -> bool:
    """Whether this denial should be written (False = duplicate within window).

    Entries are held newest-last, so expiry is a cheap sweep from the front.
    """
    now = time.monotonic()
    cutoff = now - _DENIAL_THROTTLE_SECONDS
    with _denial_lock:
        while _recent_denials:
            oldest_key, seen_at = next(iter(_recent_denials.items()))
            if seen_at <= cutoff:
                _recent_denials.pop(oldest_key, None)
            else:
                break
        if _recent_denials.get(key, 0.0) > cutoff:
            return False
        _recent_denials[key] = now
        _recent_denials.move_to_end(key)
        while len(_recent_denials) > _DENIAL_CACHE_MAX:
            _recent_denials.popitem(last=False)
        return True


def record_denial(
    *,
    actor: "User | None" = None,
    resource_type: str,
    resource_id: str | int | None = None,
    project_id: int | None = None,
    reason: str | None = None,
    detail: dict | None = None,
) -> None:
    """Record an authorization refusal (``ACCESS_DENIED`` / ``DENIED``).

    This is the "logged in but not allowed" trail — a user reaching for a
    project they don't own, or a non-admin hitting an admin route — which is
    what a reviewer looks at to spot a compromised account probing around.
    Failed *authentication* is recorded separately as ``LOGIN_FAILURE``.

    The attempted method + path go into ``detail`` so the row says which
    endpoint was probed, not merely which resource was refused.
    """
    route = get_request_route()
    method, path = route if route else (None, None)
    if not _claim_denial_slot(
        (
            getattr(actor, "id", None),
            resource_type,
            str(resource_id) if resource_id is not None else None,
            project_id,
            method,
            path,
        )
    ):
        return
    payload = {"method": method, "path": path}
    if reason:
        payload["reason"] = reason
    if detail:
        payload.update(detail)
    record_audit(
        AuditAction.ACCESS_DENIED,
        actor=actor,
        resource_type=resource_type,
        resource_id=resource_id,
        project_id=project_id,
        outcome=AuditOutcome.DENIED,
        detail=payload,
    )
