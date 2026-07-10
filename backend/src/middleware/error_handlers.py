# backend/src/middleware/error_handlers.py
"""Global exception handling: correlation ids + central error log.

An unhandled exception is caught here rather than leaking a bare
``Internal Server Error``. We:

1. resolve the request's correlation id (the *error id*),
2. log the full traceback server-side under that id,
3. persist a row to ``error_logs`` so an admin can look the id up, and
4. return a safe ``{error_id, message}`` body — no exception detail — telling
   the user to quote the id to their administrator.

This is the enterprise "show this id to support" pattern, and it lets us retire
the ad-hoc ``str(e)`` leaks scattered across older endpoints.
"""

from __future__ import annotations

import logging
import traceback
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from ..utils.request_context import get_request_id, new_request_id

if TYPE_CHECKING:
    from ..models.user import User

logger = logging.getLogger(__name__)


def _resolve_error_id(request: Request) -> str:
    state_id = getattr(request.state, "request_id", None)
    return state_id or get_request_id() or new_request_id()


def _write_error_log(
    *,
    error_id: str,
    exc: Exception,
    actor_id: int | None = None,
    actor_email: str | None = None,
    method: str | None = None,
    path: str | None = None,
    status_code: int = 500,
) -> None:
    """Best-effort write of one ErrorLog row (own session, never re-raises)."""
    try:
        from ..db.session import SessionLocal
        from ..models.audit import ErrorLog

        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[
            :20000
        ]
        row = ErrorLog(
            error_id=error_id,
            request_id=get_request_id(),
            actor_user_id=actor_id,
            actor_email=actor_email,
            method=method,
            path=(str(path)[:512] if path else None),
            status_code=status_code,
            exception_type=type(exc).__name__[:255],
            message=str(exc)[:2000],
            traceback=tb,
        )
        with SessionLocal() as db:
            db.add(row)
            db.commit()
    except Exception:  # pragma: no cover - logging must not mask the original error
        logger.exception("Failed to persist error log for error_id=%s", error_id)


def _persist_error_log(request: Request, error_id: str, exc: Exception) -> None:
    """Persist an uncaught-exception ErrorLog, pulling actor + route off the request."""
    user = getattr(request.state, "user", None)
    _write_error_log(
        error_id=error_id,
        exc=exc,
        actor_id=getattr(user, "id", None) if user is not None else None,
        actor_email=getattr(user, "email", None) if user is not None else None,
        method=request.method,
        path=str(request.url.path),
    )


def record_internal_error(exc: Exception, *, actor: "User | None" = None) -> str:
    """Log a *caught* exception to the error log and return its correlation id.

    Use this in the rare endpoint that must catch an exception (per-item batch
    loops, cleanup paths) yet must not leak raw exception text to the client:
    hand the returned ``error_id`` back to the caller instead of ``str(exc)``.
    The id resolves to the full traceback in ``error_logs`` for an admin, exactly
    like an uncaught 500. Best-effort — never raises.
    """
    error_id = get_request_id() or new_request_id()
    logger.error(
        "Handled internal error [error_id=%s] %s",
        error_id,
        type(exc).__name__,
        exc_info=exc,
    )
    _write_error_log(
        error_id=error_id,
        exc=exc,
        actor_id=getattr(actor, "id", None),
        actor_email=getattr(actor, "email", None),
    )
    return error_id


def internal_error_message(
    exc: Exception,
    *,
    actor: "User | None" = None,
    prefix: str = "Operation failed",
) -> str:
    """Record a caught exception and return a safe user-facing string with its id.

    For *persisted* async surfaces — ``PreprocessingTask.message``,
    ``FilePreprocessingTask.error_message``, ``Trial.meta['failures']``, per-doc
    results — that are later returned to the client. Stores the full traceback in
    the error log (admin-lookupable) and returns only ``"<prefix> (error id: X)"``
    so raw exception text (DB/storage/provider internals) never reaches the user.
    """
    error_id = record_internal_error(exc, actor=actor)
    return f"{prefix} (error id: {error_id})"


def raise_internal_error(
    exc: Exception,
    *,
    actor: "User | None" = None,
    message: str = "An unexpected error occurred.",
) -> None:
    """Record ``exc`` and raise a safe 500 that carries only the correlation id.

    Drop-in replacement for ``raise HTTPException(500, detail=str(exc))``: the
    client gets ``{error_id, message}`` (no internal detail) and the admin can
    look the id up in the error log. Matches the global handler's contract.
    """
    error_id = record_internal_error(exc, actor=actor)
    raise HTTPException(
        status_code=500,
        detail={
            "error_id": error_id,
            "message": (
                f"{message} Quote this ID to your administrator for support: {error_id}"
            ),
        },
        headers={"X-Request-ID": error_id},
    )


def register_exception_handlers(app) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        error_id = _resolve_error_id(request)
        logger.exception(
            "Unhandled exception [error_id=%s] %s %s",
            error_id,
            request.method,
            request.url.path,
        )
        _persist_error_log(request, error_id, exc)
        return JSONResponse(
            status_code=500,
            content={
                "error_id": error_id,
                "message": (
                    "An unexpected error occurred. Quote this ID to your "
                    f"administrator for support: {error_id}"
                ),
                "detail": "Internal server error.",
            },
            headers={"X-Request-ID": error_id},
        )
