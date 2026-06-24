# backend/src/utils/url_safety.py
"""SSRF guardrails for user-supplied custom API endpoints.

Users may configure their own LLM and preprocessing/OCR backends (custom
``base_url``). That is a feature, so we don't blanket-block private/loopback
addresses — self-hosted backends (vLLM, docling, Mistral) legitimately run on
the Docker network or localhost. Instead we close the high-value, low-cost
SSRF vectors:

  * block the cloud metadata endpoints (never a legitimate LLM endpoint),
  * restrict schemes to http/https (no ``file://``, ``gopher://``, …),
  * disable HTTP redirect-following on outbound clients (no "bounce" to
    metadata via a 3xx),

and separately sanitize what comes back from the upstream so a response body or
error string can't be used as an exfiltration channel (handled at the call
sites in ``utils/info_extraction.py`` / ``utils/helpers.py``).
"""

from __future__ import annotations

from urllib.parse import urlparse

# Hostnames / IPs that resolve to cloud instance-metadata services. Reaching
# these from inside a container is the highest-value SSRF target and is never
# a legitimate LLM/OCR endpoint.
_METADATA_HOSTS = frozenset(
    {
        "169.254.169.254",  # AWS / Azure / GCE IMDS (IPv4 link-local)
        "fd00:ec2::254",  # AWS IMDSv6
        "metadata.google.internal",  # GCE metadata
        "metadata",  # common short name
    }
)


class UnsafeEndpointError(ValueError):
    """Raised when a user-supplied endpoint URL is blocked by the SSRF policy."""


def validate_user_endpoint(base_url: str | None) -> str | None:
    """Validate a user-supplied ``base_url`` against the SSRF policy.

    Returns the URL unchanged if it is acceptable, or ``None`` if it is
    empty/missing (callers decide how to surface "incomplete config"). Raises
    ``UnsafeEndpointError`` for blocked schemes/hosts.
    """
    if not base_url or not base_url.strip():
        return None

    parsed = urlparse(base_url.strip())
    scheme = (parsed.scheme or "").lower()

    if scheme not in ("http", "https"):
        raise UnsafeEndpointError("Only http and https endpoints are allowed.")

    host = (parsed.hostname or "").lower()
    if not host:
        raise UnsafeEndpointError("Endpoint URL is missing a host.")

    if host in _METADATA_HOSTS:
        raise UnsafeEndpointError("Endpoint resolves to a blocked address.")

    return base_url
