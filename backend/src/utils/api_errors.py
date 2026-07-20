# backend/src/utils/api_errors.py
"""Machine-readable API error codes for frontend localization (i18n Phase 3).

A migrated endpoint raises ``api_error(...)`` instead of
``HTTPException(status_code, detail="English sentence")``. The resulting
``detail`` is a dict::

    {"code": "auth.invalid_credentials", "message": "Incorrect email or password",
     "params": {...}}

The frontend renders ``t('errors.<code>', params)`` when the code is known;
the embedded English ``message`` stays as the fallback for un-migrated clients
and for codes missing from a locale catalog. This keeps the migration
incremental and non-breaking: un-migrated endpoints keep returning plain-string
``detail`` and the frontend's ``extractErrorMessage`` handles both shapes.

Codes are dotted and stable (``<domain>.<reason>``), e.g. ``auth.invalid_credentials``,
``file.too_large``. Treat them like an API contract — renaming one is a
breaking change for the frontend catalog.
"""

from typing import Any

from fastapi import HTTPException


def api_error(
    code: str,
    status_code: int,
    message: str,
    *,
    headers: dict[str, str] | None = None,
    **params: Any,
) -> HTTPException:
    """Build an ``HTTPException`` carrying a localizable error code.

    Args:
        code: Stable dotted error code (``<domain>.<reason>``). The frontend
            looks up ``errors.<code>`` in its message catalog.
        status_code: HTTP status code.
        message: English fallback sentence, embedded in the response for
            un-migrated clients and missing catalog entries.
        headers: Optional response headers (e.g. ``WWW-Authenticate``).
        **params: Interpolation values for the localized message (e.g.
            ``max_mb=25``). Only include values that appear in the catalog
            string — never PHI or secrets.
    """
    detail: dict[str, Any] = {"code": code, "message": message}
    if params:
        detail["params"] = params
    return HTTPException(status_code=status_code, detail=detail, headers=headers)
