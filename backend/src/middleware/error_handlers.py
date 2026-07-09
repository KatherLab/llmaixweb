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

from fastapi import Request
from fastapi.responses import JSONResponse

from ..utils.request_context import get_request_id, new_request_id

logger = logging.getLogger(__name__)


def _resolve_error_id(request: Request) -> str:
    state_id = getattr(request.state, "request_id", None)
    return state_id or get_request_id() or new_request_id()


def _persist_error_log(request: Request, error_id: str, exc: Exception) -> None:
    """Best-effort write to the error log (own session, never re-raises)."""
    try:
        from ..db.session import SessionLocal
        from ..models.audit import ErrorLog

        actor_id = None
        actor_email = None
        user = getattr(request.state, "user", None)
        if user is not None:
            actor_id = getattr(user, "id", None)
            actor_email = getattr(user, "email", None)

        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[
            :20000
        ]
        row = ErrorLog(
            error_id=error_id,
            request_id=get_request_id(),
            actor_user_id=actor_id,
            actor_email=actor_email,
            method=request.method,
            path=str(request.url.path)[:512],
            status_code=500,
            exception_type=type(exc).__name__[:255],
            message=str(exc)[:2000],
            traceback=tb,
        )
        with SessionLocal() as db:
            db.add(row)
            db.commit()
    except Exception:  # pragma: no cover - logging must not mask the original error
        logger.exception("Failed to persist error log for error_id=%s", error_id)


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
