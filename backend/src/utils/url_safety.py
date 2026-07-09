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

import ipaddress
import socket
from urllib.parse import urlparse

# Hostnames that resolve to cloud instance-metadata services. Reaching these
# from inside a container is the highest-value SSRF target and is never a
# legitimate LLM/OCR endpoint. Kept as a hostname blocklist (in addition to the
# IP-range check) so a hostname is rejected before we even resolve it.
_METADATA_HOSTS = frozenset(
    {
        "metadata.google.internal",  # GCE metadata
        "metadata",  # common short name
    }
)

# IP networks that serve cloud instance-metadata. Any resolved address falling
# in these ranges is blocked. Covers the AWS/Azure/GCE IPv4 link-local IMDS
# (169.254.169.254) and the AWS IMDSv6 endpoint.
_METADATA_NETWORKS = (
    ipaddress.ip_network("169.254.169.254/32", strict=False),  # AWS/Azure/GCE IMDS
    ipaddress.ip_network("fd00:ec2::254/128", strict=False),  # AWS IMDSv6
)

# How long to wait for a DNS resolution when checking a hostname. Short so a
# non-resolving Docker-network hostname doesn't noticeably stall validation.
_RESOLVE_TIMEOUT = 1.0


class UnsafeEndpointError(ValueError):
    """Raised when a user-supplied endpoint URL is blocked by the SSRF policy."""


def _is_metadata_ip(ip: ipaddress._BaseAddress) -> bool:
    """True if ``ip`` is a cloud instance-metadata address.

    Normalizes IPv6-mapped IPv4 (e.g. ``::ffff:169.254.169.254``) so the mapped
    v4 address is checked against the v4 metadata ranges.
    """
    if isinstance(ip, ipaddress.IPv6Address):
        mapped = ip.ipv4_mapped
        if mapped is not None:
            return any(mapped in net for net in _METADATA_NETWORKS) or any(
                ip in net for net in _METADATA_NETWORKS
            )
    return any(ip in net for net in _METADATA_NETWORKS)


def _host_resolves_to_metadata(host: str) -> bool:
    """Resolve ``host`` and return True if any A/AAAA record is a metadata IP.

    Returns False if resolution fails (e.g. a Docker-network hostname that
    doesn't resolve from the validation context) — we only block on a positive
    match, never on "couldn't tell", to preserve the self-hosted-backend
    feature. DNS rebinding where a hostname flips to a metadata IP between
    validation and the actual request is mitigated by disabled
    redirect-following at the call sites; this check catches the static case.
    """
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, socket.herror, OSError):
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _is_metadata_ip(ip):
            return True
    return False


def validate_user_endpoint(base_url: str | None) -> str | None:
    """Validate a user-supplied ``base_url`` against the SSRF policy.

    Returns the URL unchanged if it is acceptable, or ``None`` if it is
    empty/missing (callers decide how to surface "incomplete config"). Raises
    ``UnsafeEndpointError`` for blocked schemes/hosts.

    The host check handles alternate IP notations (decimal, hex, octal,
    IPv6-mapped) by parsing with :mod:`ipaddress`, and resolves hostnames so a
    name pointing at a metadata IP is also blocked.
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

    # If the host is a literal IP (incl. decimal/hex/octal/IPv6-mapped forms
    # that ipaddress understands), check it directly. Otherwise resolve the
    # hostname and check every resolved address.
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # Not a literal IP — resolve and check A/AAAA records.
        if _host_resolves_to_metadata(host):
            raise UnsafeEndpointError("Endpoint resolves to a blocked address.")
    else:
        if _is_metadata_ip(ip):
            raise UnsafeEndpointError("Endpoint resolves to a blocked address.")

    return base_url


def _parse_allowlist(allowlist: str | None) -> list[str]:
    """Parse a comma-separated host allowlist into normalized lowercase hosts."""
    if not allowlist:
        return []
    return [h.strip().lower() for h in allowlist.split(",") if h.strip()]


def enforce_endpoint_allowlist(base_url: str | None, allowlist: str | None) -> None:
    """Reject an endpoint whose host is not in a configured allowlist.

    Complements the SSRF policy: where :func:`validate_user_endpoint` blocks
    *dangerous* destinations, this optionally restricts egress to an explicit
    set of *permitted* hosts (e.g. only your on-prem LLM/OCR services), which is
    what a clinic wants so patient data can't be sent to an arbitrary endpoint.

    ``allowlist`` is a comma-separated list of hostnames. When it is empty the
    check is disabled (any host allowed, subject to the SSRF policy) so the
    default behaviour is unchanged. Matching is exact host or a ``.suffix``
    (so ``example.com`` also permits ``api.example.com``). Raises
    ``UnsafeEndpointError`` on a host that isn't permitted.
    """
    allowed = _parse_allowlist(allowlist)
    if not allowed:
        return
    if not base_url or not base_url.strip():
        return
    host = (urlparse(base_url.strip()).hostname or "").lower()
    if not host:
        raise UnsafeEndpointError("Endpoint URL is missing a host.")
    for entry in allowed:
        if host == entry or host.endswith("." + entry):
            return
    raise UnsafeEndpointError(
        "Endpoint host is not in the configured egress allowlist."
    )
