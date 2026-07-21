# backend/tests/test_url_safety.py
"""Pure-unit tests for the SSRF guardrails in ``utils/url_safety.py``.

These exercise the endpoint validation / allowlist policy that protects
user-supplied custom LLM/OCR ``base_url`` values. Literal-IP paths need no
mocking (they skip DNS); only the hostname-resolution branch patches
``socket.getaddrinfo`` with crafted addrinfo tuples.

Goal: near-total branch coverage AND surfacing real SSRF gaps. Where a test
documents insecure behaviour it asserts the *secure* expectation and is marked
``xfail`` so we never lock in the weakness.
"""

import ipaddress
import socket
from unittest import mock

import pytest

from backend.src.utils import url_safety as us
from backend.src.utils.url_safety import (
    UnsafeEndpointError,
    _host_resolves_to_metadata,
    _is_metadata_ip,
    _parse_allowlist,
    enforce_endpoint_allowlist,
    validate_user_endpoint,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _addrinfo(addr: str, family: int = socket.AF_INET):
    """Build a getaddrinfo-shaped result list: (family, type, proto, canon, sockaddr)."""
    return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (addr, 0))]


# --------------------------------------------------------------------------- #
# _is_metadata_ip  (pure, no DNS)
# --------------------------------------------------------------------------- #
class TestIsMetadataIp:
    def test_ipv4_metadata(self):
        assert _is_metadata_ip(ipaddress.ip_address("169.254.169.254")) is True

    def test_ipv4_non_metadata(self):
        assert _is_metadata_ip(ipaddress.ip_address("8.8.8.8")) is False
        # link-local neighbours are NOT the IMDS host and stay allowed
        assert _is_metadata_ip(ipaddress.ip_address("169.254.169.253")) is False

    def test_ipv6_mapped_ipv4_metadata(self):
        # ::ffff:169.254.169.254 must normalize the mapped v4 and block
        assert _is_metadata_ip(ipaddress.ip_address("::ffff:169.254.169.254")) is True

    def test_ipv6_mapped_ipv4_non_metadata(self):
        # mapped-but-harmless exercises the "mapped is not None, not in net" path
        assert _is_metadata_ip(ipaddress.ip_address("::ffff:8.8.8.8")) is False

    def test_ipv6_pure_metadata(self):
        # AWS IMDSv6, no ipv4_mapped -> falls through to the plain v6 check
        assert _is_metadata_ip(ipaddress.ip_address("fd00:ec2::254")) is True

    def test_ipv6_pure_non_metadata(self):
        assert _is_metadata_ip(ipaddress.ip_address("2001:db8::1")) is False


# --------------------------------------------------------------------------- #
# _host_resolves_to_metadata  (patches socket.getaddrinfo)
# --------------------------------------------------------------------------- #
class TestHostResolvesToMetadata:
    def test_resolves_to_metadata_blocks(self):
        with mock.patch.object(
            us.socket, "getaddrinfo", return_value=_addrinfo("169.254.169.254")
        ):
            assert _host_resolves_to_metadata("evil.example") is True

    def test_resolves_to_mapped_v6_metadata_blocks(self):
        with mock.patch.object(
            us.socket,
            "getaddrinfo",
            return_value=_addrinfo("::ffff:169.254.169.254", socket.AF_INET6),
        ):
            assert _host_resolves_to_metadata("evil6.example") is True

    def test_resolves_to_safe_addr_not_blocked(self):
        with mock.patch.object(
            us.socket, "getaddrinfo", return_value=_addrinfo("10.0.0.5")
        ):
            assert _host_resolves_to_metadata("selfhosted.internal") is False

    def test_gaierror_not_blocked(self):
        # A non-resolving Docker-network hostname must NOT be blocked (feature).
        with mock.patch.object(
            us.socket, "getaddrinfo", side_effect=socket.gaierror("boom")
        ):
            assert _host_resolves_to_metadata("does-not-resolve") is False

    def test_herror_not_blocked(self):
        with mock.patch.object(
            us.socket, "getaddrinfo", side_effect=socket.herror("boom")
        ):
            assert _host_resolves_to_metadata("host.err") is False

    def test_oserror_not_blocked(self):
        with mock.patch.object(us.socket, "getaddrinfo", side_effect=OSError("boom")):
            assert _host_resolves_to_metadata("os.err") is False

    def test_unparseable_addr_is_skipped(self):
        # A scoped/garbage sockaddr triggers the ValueError->continue branch;
        # with no other records the host is treated as safe.
        with mock.patch.object(
            us.socket,
            "getaddrinfo",
            return_value=_addrinfo("fe80::1%eth0", socket.AF_INET6),
        ):
            assert _host_resolves_to_metadata("weird.host") is False

    def test_mixed_records_metadata_wins(self):
        # First a safe record, then a metadata one -> must block.
        infos = _addrinfo("10.0.0.1") + _addrinfo("169.254.169.254")
        with mock.patch.object(us.socket, "getaddrinfo", return_value=infos):
            assert _host_resolves_to_metadata("mixed.host") is True


# --------------------------------------------------------------------------- #
# validate_user_endpoint
# --------------------------------------------------------------------------- #
class TestValidateUserEndpoint:
    @pytest.mark.parametrize("value", [None, "", "   ", "\t\n"])
    def test_empty_returns_none(self, value):
        assert validate_user_endpoint(value) is None

    @pytest.mark.parametrize(
        "url",
        [
            "ftp://example.com/",
            "file:///etc/passwd",
            "gopher://example.com/",
            "ws://example.com/",
            "javascript:alert(1)",
        ],
    )
    def test_non_http_scheme_rejected(self, url):
        with pytest.raises(UnsafeEndpointError):
            validate_user_endpoint(url)

    @pytest.mark.parametrize("url", ["http:///v1", "https:///path"])
    def test_missing_host_rejected(self, url):
        with pytest.raises(UnsafeEndpointError):
            validate_user_endpoint(url)

    @pytest.mark.parametrize(
        "url",
        [
            "http://metadata/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "https://METADATA/",  # case-insensitive host match
        ],
    )
    def test_metadata_hostname_blocklist(self, url):
        with pytest.raises(UnsafeEndpointError):
            validate_user_endpoint(url)

    def test_literal_metadata_ipv4_blocked(self):
        with pytest.raises(UnsafeEndpointError):
            validate_user_endpoint("http://169.254.169.254/latest/meta-data/")

    def test_literal_metadata_ipv6_mapped_blocked(self):
        with pytest.raises(UnsafeEndpointError):
            validate_user_endpoint("http://[::ffff:169.254.169.254]/")

    def test_literal_metadata_ipv6_blocked(self):
        with pytest.raises(UnsafeEndpointError):
            validate_user_endpoint("http://[fd00:ec2::254]/")

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8000/v1",  # self-hosted localhost is allowed
            "http://10.0.0.5:11434/v1",  # private Docker-network IP allowed
            "https://api.openai.com/v1",  # public host, resolution mocked below
            "http://[2001:db8::1]/v1",  # non-metadata literal IPv6
        ],
    )
    def test_safe_literal_ips_pass_through(self, url):
        # These are literal IPs (except the public host) — no DNS for the IPs.
        # For the public host, force a benign resolution so the test is offline.
        with mock.patch.object(
            us.socket, "getaddrinfo", return_value=_addrinfo("93.184.216.34")
        ):
            assert validate_user_endpoint(url) == url

    def test_hostname_resolving_to_metadata_blocked(self):
        with mock.patch.object(
            us.socket, "getaddrinfo", return_value=_addrinfo("169.254.169.254")
        ):
            with pytest.raises(UnsafeEndpointError):
                validate_user_endpoint("http://rebind.attacker.example/v1")

    def test_hostname_not_resolving_is_allowed(self):
        # Docker-network name that doesn't resolve from the validator's context
        # must be allowed (returned unchanged), never blocked on "couldn't tell".
        with mock.patch.object(
            us.socket, "getaddrinfo", side_effect=socket.gaierror("nxdomain")
        ):
            url = "http://vllm.internal:8000/v1"
            assert validate_user_endpoint(url) == url

    def test_url_returned_unchanged_not_normalized(self):
        with mock.patch.object(
            us.socket, "getaddrinfo", return_value=_addrinfo("1.2.3.4")
        ):
            url = "https://Example.COM/v1/?x=1"
            assert validate_user_endpoint(url) == url

    # ---- SUSPECTED SSRF GAP: alternate integer/hex/octal IP notations -------
    # The docstring claims decimal/hex/octal host forms are "handled by parsing
    # with ipaddress", but ``ipaddress.ip_address`` does NOT parse those forms.
    # ``_coerce_numeric_ipv4`` now normalizes them BEFORE the metadata check, so
    # a URL like ``http://2852039166/`` (== 169.254.169.254) is rejected without
    # depending on the resolver. We simulate a strict resolver (gaierror) to
    # prove the block holds even when libc wouldn't parse the numeric form.
    @pytest.mark.parametrize(
        "url",
        [
            "http://2852039166/",  # decimal 169.254.169.254
            "http://0xA9FEA9FE/",  # hex 169.254.169.254
            "http://0251.0376.0251.0376/",  # octal 169.254.169.254
        ],
    )
    def test_alternate_notation_metadata_should_be_blocked(self, url):
        with mock.patch.object(
            us.socket, "getaddrinfo", side_effect=socket.gaierror("strict resolver")
        ):
            with pytest.raises(UnsafeEndpointError):
                validate_user_endpoint(url)


# --------------------------------------------------------------------------- #
# _parse_allowlist  (pure)
# --------------------------------------------------------------------------- #
class TestParseAllowlist:
    @pytest.mark.parametrize("value", [None, "", "   ", ",", " , , "])
    def test_empty_variants_return_empty_list(self, value):
        assert _parse_allowlist(value) == []

    def test_trims_lowercases_and_drops_blanks(self):
        assert _parse_allowlist("A.com, b.com ,, c.COM ") == [
            "a.com",
            "b.com",
            "c.com",
        ]

    def test_single_host(self):
        assert _parse_allowlist("api.internal") == ["api.internal"]


# --------------------------------------------------------------------------- #
# enforce_endpoint_allowlist
# --------------------------------------------------------------------------- #
class TestEnforceEndpointAllowlist:
    @pytest.mark.parametrize("allowlist", [None, "", "   "])
    def test_empty_allowlist_allows_anything(self, allowlist):
        # No allowlist configured -> check disabled, never raises.
        assert (
            enforce_endpoint_allowlist("http://anything.example/v1", allowlist) is None
        )

    @pytest.mark.parametrize("base_url", [None, "", "   "])
    def test_empty_base_url_is_noop(self, base_url):
        assert enforce_endpoint_allowlist(base_url, "example.com") is None

    def test_exact_host_match_allowed(self):
        assert (
            enforce_endpoint_allowlist("https://example.com/v1", "example.com") is None
        )

    def test_exact_host_match_case_insensitive(self):
        assert (
            enforce_endpoint_allowlist("https://EXAMPLE.com/v1", "example.com") is None
        )

    def test_subdomain_suffix_match_allowed(self):
        assert (
            enforce_endpoint_allowlist("https://api.example.com/v1", "example.com")
            is None
        )

    def test_deep_subdomain_suffix_match_allowed(self):
        assert (
            enforce_endpoint_allowlist("https://a.b.example.com/v1", "example.com")
            is None
        )

    def test_suffix_boundary_not_bypassed(self):
        # "notexample.com" must NOT match allowlist entry "example.com"
        with pytest.raises(UnsafeEndpointError):
            enforce_endpoint_allowlist("https://notexample.com/v1", "example.com")

    def test_non_matching_host_rejected(self):
        with pytest.raises(UnsafeEndpointError):
            enforce_endpoint_allowlist("https://evil.test/v1", "example.com,other.org")

    def test_matches_second_entry(self):
        assert (
            enforce_endpoint_allowlist("https://other.org/v1", "example.com, other.org")
            is None
        )

    def test_base_url_without_host_but_allowlist_set_rejected(self):
        # base_url is non-empty but has no host -> explicit rejection.
        with pytest.raises(UnsafeEndpointError):
            enforce_endpoint_allowlist("http://", "example.com")
