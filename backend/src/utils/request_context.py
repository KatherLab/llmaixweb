# backend/src/utils/request_context.py
"""Per-request context carried via ContextVars.

A short correlation id and the client IP are stamped once per request by
``middleware.request_context.RequestContextMiddleware`` and read from anywhere
in the request's call stack — notably the audit service and structured logging
— without threading a ``Request`` argument through every function.

The correlation id doubles as the user-facing *error id*: when an unhandled
exception is caught by the global handler, the same id is returned to the
client and written to the error log, so a user can quote it to an admin.
"""

from __future__ import annotations

import secrets
import string
from contextvars import ContextVar

# base32-ish alphabet without ambiguous chars (no 0/O/1/I/l) — short, readable,
# safe to read aloud / paste into a support request.
_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_client_ip_var: ContextVar[str | None] = ContextVar("client_ip", default=None)


def new_request_id() -> str:
    """Generate a fresh 12-char correlation/error id."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(12))


def set_request_context(request_id: str, client_ip: str | None) -> None:
    _request_id_var.set(request_id)
    _client_ip_var.set(client_ip)


def get_request_id() -> str | None:
    return _request_id_var.get()


def get_client_ip() -> str | None:
    return _client_ip_var.get()


_ALLOWED = set(_ALPHABET)


def sanitize_request_id(value: str | None) -> str | None:
    """Accept an inbound X-Request-ID only if it looks like one of ours.

    Prevents log/response injection from an untrusted upstream header while
    still honouring a correlation id set by a trusted reverse proxy.
    """
    if not value:
        return None
    value = value.strip()[:64]
    if value and all(c in _ALLOWED or c in string.hexdigits + "-" for c in value):
        return value
    return None
