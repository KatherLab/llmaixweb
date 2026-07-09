# backend/src/middleware/request_context.py
"""ASGI middleware that stamps a correlation id + client IP onto each request.

Implemented as raw ASGI (not ``BaseHTTPMiddleware``) so the ContextVars we set
propagate cleanly into the route handler and are readable by the audit service
and structured logging without a per-request context copy. The id is also
written to ``scope["state"]`` so it survives up to the global exception handler
(which runs outside this middleware for unhandled 500s) and is echoed back in
the ``X-Request-ID`` response header.
"""

from __future__ import annotations

from starlette.datastructures import Headers, MutableHeaders

from ..utils.request_context import (
    new_request_id,
    sanitize_request_id,
    set_request_context,
)


def _client_ip(scope) -> str | None:
    """Best-effort client IP.

    Honours the left-most ``X-Forwarded-For`` entry (the original client when
    the app sits behind a trusted reverse proxy, as the deployment guide
    prescribes), falling back to the direct peer address.
    """
    headers = Headers(scope=scope)
    xff = headers.get("x-forwarded-for")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first[:45]
    client = scope.get("client")
    if client:
        return str(client[0])[:45]
    return None


class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = (
            sanitize_request_id(headers.get("x-request-id")) or new_request_id()
        )
        client_ip = _client_ip(scope)

        # Expose to exception handlers (they read Request.state off scope).
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id
        scope["state"]["client_ip"] = client_ip

        set_request_context(request_id, client_ip)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append("X-Request-ID", request_id)
            await send(message)

        await self.app(scope, receive, send_wrapper)
