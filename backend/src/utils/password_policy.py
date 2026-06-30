# backend/src/utils/password_policy.py
"""Central password policy enforcement.

Every endpoint that sets a password (registration, first-admin, change
password, admin set-password, password reset) calls :func:`validate_password`
in addition to the Pydantic ``min_length``/``max_length`` gates on the request
schemas. Keeping the rules in one place means the policy is consistent across
all flows and tunable from the admin panel without touching each endpoint.

The rules are read live from :func:`settings` (the runtime-overridable proxy),
so admin changes to ``PASSWORD_POLICY_*`` take effect immediately.
"""

from __future__ import annotations

import string

from fastapi import HTTPException, status

from ..core.config import settings


def _missing_rules(password: str) -> list[str]:
    """Return a list of human-readable policy rules the password violates."""
    settings_proxy = settings  # runtime-overridable proxy
    min_len = settings_proxy.PASSWORD_POLICY_MIN_LENGTH
    max_len = settings_proxy.PASSWORD_POLICY_MAX_LENGTH

    errors: list[str] = []

    if len(password) < min_len:
        errors.append(f"be at least {min_len} characters long")
    if len(password) > max_len:
        errors.append(f"be at most {max_len} characters long")
    if settings_proxy.PASSWORD_POLICY_REQUIRE_UPPERCASE and not any(
        c in string.ascii_uppercase for c in password
    ):
        errors.append("contain an uppercase letter")
    if settings_proxy.PASSWORD_POLICY_REQUIRE_LOWERCASE and not any(
        c in string.ascii_lowercase for c in password
    ):
        errors.append("contain a lowercase letter")
    if settings_proxy.PASSWORD_POLICY_REQUIRE_DIGIT and not any(
        c in string.digits for c in password
    ):
        errors.append("contain a digit")
    if settings_proxy.PASSWORD_POLICY_REQUIRE_SYMBOL and not any(
        c in string.punctuation for c in password
    ):
        errors.append("contain a symbol")
    return errors


def validate_password(password: str) -> None:
    """Raise ``HTTPException(400)`` if ``password`` fails the policy.

    Returns ``None`` (no return value) on success — callers just call it for
    the side effect.
    """
    errors = _missing_rules(password)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must {' and '.join(errors)}.",
        )
