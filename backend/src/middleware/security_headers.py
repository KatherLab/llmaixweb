# backend/src/middleware/security_headers.py
"""Adds baseline HTTP security headers to every response.

Defence-in-depth for a browser-facing app handling patient data. The frontend
nginx also sets headers for the static SPA; this covers the API responses and
any direct-to-backend access. HSTS is only emitted when the request is (or was,
per ``X-Forwarded-Proto``) HTTPS, so it never breaks plain-HTTP local dev.
"""

from __future__ import annotations

from starlette.datastructures import Headers, MutableHeaders

# A deliberately strict API CSP: these responses are JSON/file payloads, never
# HTML that loads scripts, so we can lock everything down. The SPA's own CSP is
# set by nginx where the HTML is served.
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"

_STATIC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": _API_CSP,
    "Cross-Origin-Resource-Policy": "same-site",
}


class SecurityHeadersMiddleware:
    def __init__(self, app, *, hsts_max_age: int = 63072000):
        self.app = app
        self.hsts_value = f"max-age={hsts_max_age}; includeSubDomains"

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        req_headers = Headers(scope=scope)
        is_https = scope.get("scheme") == "https" or (
            req_headers.get("x-forwarded-proto", "").split(",")[0].strip() == "https"
        )

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for key, value in _STATIC_HEADERS.items():
                    headers.setdefault(key, value)
                if is_https:
                    headers.setdefault("Strict-Transport-Security", self.hsts_value)
            await send(message)

        await self.app(scope, receive, send_wrapper)
