# backend/src/utils/email_i18n.py
"""Message catalogs for outgoing email.

The frontend owns UI localization (``frontend/locales/*.json`` via vue-i18n), but
email is composed server-side — often in a Celery worker, long after the request
that started the job — so the backend needs its own catalogs. They live in
``backend/src/locales/emails/<locale>.json`` and are keyed by dotted paths
mirroring the frontend's convention.

Rules that keep this honest:

* ``en`` is the source of truth. A key missing from another locale falls back to
  ``en``; a key missing from ``en`` too returns the key itself, so a typo shows up
  as a visible ``job.subject.nope`` in a test rather than an empty email.
* Interpolation is ``str.format``-style (``{project}``). A missing or misspelled
  parameter degrades to the un-interpolated template instead of raising — an
  untranslated string is a cosmetic bug, a crash in a Celery finalizer is not.
* Values are inserted into HTML with Jinja autoescaping on, so catalog strings
  must not contain markup.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CATALOG_DIR = Path(__file__).resolve().parent.parent / "locales" / "emails"

# Must stay in sync with SUPPORTED_LOCALES in frontend/i18n/index.ts — the
# frontend mirrors its active locale onto User.preferred_language, and anything
# we don't have a catalog for silently becomes English.
SUPPORTED_LOCALES: tuple[str, ...] = ("en", "de", "fr", "es")
DEFAULT_LOCALE = "en"


def normalize_locale(value: str | None) -> str:
    """Map a user/browser locale onto a catalog we actually have.

    Accepts ``de``, ``de-DE``, ``DE_at`` … and falls back to English for
    anything unknown or missing.
    """
    if not value:
        return DEFAULT_LOCALE
    base = str(value).strip().replace("_", "-").split("-")[0].lower()
    return base if base in SUPPORTED_LOCALES else DEFAULT_LOCALE


@lru_cache(maxsize=len(SUPPORTED_LOCALES) + 1)
def _catalog(locale: str) -> dict[str, Any]:
    """Load and cache one locale's catalog (empty dict if unreadable)."""
    path = _CATALOG_DIR / f"{locale}.json"
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        logger.error("Email catalog missing: %s", path)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Email catalog %s could not be read: %s", path, e)
    return {}


def _lookup(catalog: dict[str, Any], key: str) -> str | None:
    node: Any = catalog
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, str) else None


def translate(locale: str | None, key: str, **params: Any) -> str:
    """Return the localized string for ``key``, interpolating ``params``.

    Falls back through: requested locale → English → the key itself.
    """
    normalized = normalize_locale(locale)
    template = _lookup(_catalog(normalized), key)
    if template is None and normalized != DEFAULT_LOCALE:
        template = _lookup(_catalog(DEFAULT_LOCALE), key)
    if template is None:
        logger.warning("Email catalog has no entry for %r (locale %s)", key, normalized)
        return key
    if not params:
        return template
    try:
        return template.format(**params)
    except (KeyError, IndexError, ValueError) as e:
        logger.warning("Could not interpolate email string %r: %s", key, e)
        return template


def translator(locale: str | None):
    """Return a ``t(key, **params)`` bound to one locale (for templates)."""
    normalized = normalize_locale(locale)

    def t(key: str, **params: Any) -> str:
        return translate(normalized, key, **params)

    return t


def format_duration(seconds: float | int | None, locale: str | None) -> str:
    """Render an elapsed time as a short localized string ("1 h 12 min").

    Returns an em dash for unknown durations so the details table never shows a
    bare "None".
    """
    if seconds is None or seconds < 0:
        return "—"
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return translate(locale, "duration.h_m", hours=hours, minutes=minutes)
    if minutes:
        return translate(locale, "duration.m_s", minutes=minutes, seconds=secs)
    return translate(locale, "duration.s", seconds=secs)


def reset_catalog_cache() -> None:
    """Drop cached catalogs (tests that write catalog files, hot reload)."""
    _catalog.cache_clear()
