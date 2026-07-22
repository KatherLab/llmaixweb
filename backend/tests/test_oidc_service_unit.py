# backend/tests/test_oidc_service_unit.py
"""Unit tests for ``services/oidc_service.py`` internals.

``test_sso_flow.py`` drives the router end-to-end but mocks ``discover`` /
``exchange_code`` / ``fetch_userinfo`` wholesale, so the module's own logic —
PKCE derivation, the signed-state JWT round-trip, discovery caching + error
mapping, the id_token signature verifier, and the SSRF re-validation of
discovery-document endpoints — was never exercised. These tests hit that layer
directly with the HTTP + JWKS boundaries mocked.
"""

import base64
import datetime
import hashlib

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from backend.src.core import config
from backend.src.services import oidc_service

_ISSUER = "https://idp.example.test"
_DISCOVERY_DOC = {
    "issuer": _ISSUER,
    "authorization_endpoint": f"{_ISSUER}/authorize",
    "token_endpoint": f"{_ISSUER}/token",
    "userinfo_endpoint": f"{_ISSUER}/userinfo",
    "jwks_uri": f"{_ISSUER}/jwks",
}


@pytest.fixture(autouse=True)
def _clear_discovery_cache():
    oidc_service._DISCOVERY_CACHE.clear()
    yield
    oidc_service._DISCOVERY_CACHE.clear()


class _FakeResp:
    def __init__(self, *, status_code=200, json_data=None, text="", raise_exc=None):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc is not None:
            raise self._raise_exc

    def json(self):
        return self._json


# ─────────────────────────── _pkce_pair ───────────────────────────


def test_pkce_pair_s256_relation():
    verifier, challenge = oidc_service._pkce_pair()
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .decode("ascii")
        .rstrip("=")
    )
    assert challenge == expected
    # URL-safe, no padding.
    assert "=" not in challenge
    assert "+" not in challenge and "/" not in challenge


# ─────────────────────────── state JWT round-trip ───────────────────────────


def test_state_round_trip():
    state = oidc_service._make_state("prov", "the-verifier", "/projects", "nonce123")
    payload = oidc_service.decode_state(state)
    assert payload["provider"] == "prov"
    assert payload["verifier"] == "the-verifier"
    assert payload["redirect"] == "/projects"
    assert payload["nonce"] == "nonce123"


def test_state_empty_redirect_defaults_to_root():
    state = oidc_service._make_state("prov", "v", "", "n")
    assert oidc_service.decode_state(state)["redirect"] == "/"


def test_state_tampered_signature_rejected():
    settings = config._get_settings()
    forged = jwt.encode(
        {
            "exp": oidc_service._now() + datetime.timedelta(minutes=10),
            "iss": "llmaixweb-sso",
            "provider": "p",
            "verifier": "v",
            "redirect": "/",
            "nonce": "n",
        },
        settings.SECRET_KEY + "-wrong",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        oidc_service.decode_state(forged)
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "sso.invalid_state"


def test_state_wrong_issuer_rejected():
    settings = config._get_settings()
    tok = jwt.encode(
        {
            "exp": oidc_service._now() + datetime.timedelta(minutes=10),
            "iss": "someone-else",
            "provider": "p",
            "verifier": "v",
            "redirect": "/",
            "nonce": "n",
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException):
        oidc_service.decode_state(tok)


def test_state_expired_rejected():
    settings = config._get_settings()
    tok = jwt.encode(
        {
            "exp": oidc_service._now() - datetime.timedelta(minutes=1),
            "iss": "llmaixweb-sso",
            "provider": "p",
            "verifier": "v",
            "redirect": "/",
            "nonce": "n",
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException):
        oidc_service.decode_state(tok)


# ─────────────────────────── _validate_issuer ───────────────────────────


def test_validate_issuer_empty_required():
    with pytest.raises(HTTPException) as exc:
        oidc_service._validate_issuer("")
    assert exc.value.detail["code"] == "sso.issuer_url_required"


def test_validate_issuer_metadata_blocked():
    with pytest.raises(HTTPException) as exc:
        oidc_service._validate_issuer("http://169.254.169.254/")
    assert exc.value.detail["code"] == "sso.unsafe_issuer_url"


def test_validate_issuer_strips_trailing_slash():
    assert oidc_service._validate_issuer(f"{_ISSUER}/") == _ISSUER


# ─────────────────────────── discover ───────────────────────────


def test_discover_caches(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, timeout=None):
        calls["n"] += 1
        return _FakeResp(json_data=dict(_DISCOVERY_DOC))

    monkeypatch.setattr(oidc_service.httpx, "get", fake_get)
    first = oidc_service.discover(_ISSUER)
    second = oidc_service.discover(_ISSUER)
    assert first == second == _DISCOVERY_DOC
    assert calls["n"] == 1  # second call served from cache


def test_discover_unreachable(monkeypatch):
    def fake_get(url, timeout=None):
        return _FakeResp(raise_exc=httpx.ConnectError("refused"))

    monkeypatch.setattr(oidc_service.httpx, "get", fake_get)
    with pytest.raises(HTTPException) as exc:
        oidc_service.discover(_ISSUER)
    assert exc.value.detail["code"] == "sso.discovery_unreachable"


def test_discover_missing_endpoints(monkeypatch):
    def fake_get(url, timeout=None):
        return _FakeResp(json_data={"issuer": _ISSUER})  # no auth/token endpoints

    monkeypatch.setattr(oidc_service.httpx, "get", fake_get)
    with pytest.raises(HTTPException) as exc:
        oidc_service.discover(_ISSUER)
    assert exc.value.detail["code"] == "sso.discovery_missing_endpoints"


# ─────────────────────────── exchange_code ───────────────────────────


def _seed_discovery(monkeypatch, doc=None):
    monkeypatch.setattr(
        oidc_service, "discover", lambda issuer_url: dict(doc or _DISCOVERY_DOC)
    )


def test_exchange_code_success(monkeypatch):
    _seed_discovery(monkeypatch)
    monkeypatch.setattr(
        oidc_service.httpx,
        "post",
        lambda url, data=None, timeout=None: _FakeResp(json_data={"id_token": "x"}),
    )
    out = oidc_service.exchange_code(_ISSUER, "cid", "sec", "code", "ruri", "verifier")
    assert out == {"id_token": "x"}


def test_exchange_code_non_200(monkeypatch):
    _seed_discovery(monkeypatch)
    monkeypatch.setattr(
        oidc_service.httpx,
        "post",
        lambda url, data=None, timeout=None: _FakeResp(status_code=400, text="bad"),
    )
    with pytest.raises(HTTPException) as exc:
        oidc_service.exchange_code(_ISSUER, "cid", "sec", "code", "ruri", "v")
    assert exc.value.detail["code"] == "sso.token_exchange_failed"


def test_exchange_code_transport_error(monkeypatch):
    _seed_discovery(monkeypatch)

    def boom(url, data=None, timeout=None):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(oidc_service.httpx, "post", boom)
    with pytest.raises(HTTPException) as exc:
        oidc_service.exchange_code(_ISSUER, "cid", "sec", "code", "ruri", "v")
    assert exc.value.status_code == 502


def test_exchange_code_ssrf_blocked_token_endpoint(monkeypatch):
    """A discovery doc naming an internal token_endpoint must be refused before
    any request is made (SSRF defense-in-depth)."""
    bad_doc = dict(_DISCOVERY_DOC, token_endpoint="http://169.254.169.254/token")
    _seed_discovery(monkeypatch, bad_doc)

    def must_not_call(*a, **k):  # pragma: no cover - should never run
        raise AssertionError("request made to blocked endpoint")

    monkeypatch.setattr(oidc_service.httpx, "post", must_not_call)
    with pytest.raises(HTTPException) as exc:
        oidc_service.exchange_code(_ISSUER, "cid", "sec", "code", "ruri", "v")
    assert exc.value.detail["code"] == "sso.unsafe_discovery_endpoint"


# ─────────────────────────── fetch_userinfo ───────────────────────────


def test_fetch_userinfo_no_endpoint_returns_empty(monkeypatch):
    doc = dict(_DISCOVERY_DOC)
    doc.pop("userinfo_endpoint")
    _seed_discovery(monkeypatch, doc)
    assert oidc_service.fetch_userinfo(_ISSUER, "tok") == {}


def test_fetch_userinfo_issuer_mismatch(monkeypatch):
    _seed_discovery(monkeypatch)
    monkeypatch.setattr(
        oidc_service.httpx,
        "get",
        lambda url, headers=None, timeout=None: _FakeResp(
            json_data={"sub": "s", "iss": "https://evil.test"}
        ),
    )
    with pytest.raises(HTTPException) as exc:
        oidc_service.fetch_userinfo(_ISSUER, "tok")
    assert exc.value.detail["code"] == "sso.userinfo_issuer_mismatch"


def test_fetch_userinfo_ssrf_blocked(monkeypatch):
    bad_doc = dict(_DISCOVERY_DOC, userinfo_endpoint="http://169.254.169.254/ui")
    _seed_discovery(monkeypatch, bad_doc)

    def must_not_call(*a, **k):  # pragma: no cover
        raise AssertionError("request made to blocked endpoint")

    monkeypatch.setattr(oidc_service.httpx, "get", must_not_call)
    with pytest.raises(HTTPException) as exc:
        oidc_service.fetch_userinfo(_ISSUER, "tok")
    assert exc.value.detail["code"] == "sso.unsafe_discovery_endpoint"


# ─────────────────────────── verify_id_token ───────────────────────────


@pytest.fixture(scope="module")
def rsa_keys():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pub_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return priv_pem, pub_pem


def _sign(priv_pem, claims):
    return jwt.encode(claims, priv_pem, algorithm="RS256")


class _FakeSigningKey:
    def __init__(self, key):
        self.key = key


def _patch_jwks(monkeypatch, pub_pem):
    class _FakeJWKClient:
        def __init__(self, uri):
            self.uri = uri

        def get_signing_key_from_jwt(self, token):
            return _FakeSigningKey(pub_pem)

    monkeypatch.setattr(oidc_service.jwt, "PyJWKClient", _FakeJWKClient)


def _base_claims():
    now = oidc_service._now()
    return {
        "iss": _ISSUER,
        "aud": "client-123",
        "sub": "subject-1",
        "exp": now + datetime.timedelta(minutes=5),
        "iat": now,
        "nonce": "nonce-abc",
    }


def test_verify_id_token_valid(monkeypatch, rsa_keys):
    priv, pub = rsa_keys
    _seed_discovery(monkeypatch)
    _patch_jwks(monkeypatch, pub)
    token = _sign(priv, _base_claims())
    payload = oidc_service.verify_id_token(_ISSUER, token, "client-123", "nonce-abc")
    assert payload["sub"] == "subject-1"


def test_verify_id_token_wrong_audience(monkeypatch, rsa_keys):
    priv, pub = rsa_keys
    _seed_discovery(monkeypatch)
    _patch_jwks(monkeypatch, pub)
    token = _sign(priv, _base_claims())
    with pytest.raises(HTTPException) as exc:
        oidc_service.verify_id_token(_ISSUER, token, "other-client", "nonce-abc")
    assert exc.value.detail["code"] == "sso.id_token_verification_failed"


def test_verify_id_token_bad_signature(monkeypatch, rsa_keys):
    priv, pub = rsa_keys
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    _seed_discovery(monkeypatch)
    _patch_jwks(monkeypatch, pub)  # verify with the *original* public key
    token = _sign(other_pem, _base_claims())  # but signed by a different key
    with pytest.raises(HTTPException) as exc:
        oidc_service.verify_id_token(_ISSUER, token, "client-123", "nonce-abc")
    assert exc.value.detail["code"] == "sso.id_token_verification_failed"


def test_verify_id_token_nonce_mismatch(monkeypatch, rsa_keys):
    priv, pub = rsa_keys
    _seed_discovery(monkeypatch)
    _patch_jwks(monkeypatch, pub)
    token = _sign(priv, _base_claims())
    with pytest.raises(HTTPException) as exc:
        oidc_service.verify_id_token(_ISSUER, token, "client-123", "different-nonce")
    assert exc.value.detail["code"] == "sso.id_token_nonce_mismatch"


def test_verify_id_token_no_jwks_uri(monkeypatch, rsa_keys):
    priv, _ = rsa_keys
    doc = dict(_DISCOVERY_DOC)
    doc.pop("jwks_uri")
    _seed_discovery(monkeypatch, doc)
    token = _sign(priv, _base_claims())
    with pytest.raises(HTTPException) as exc:
        oidc_service.verify_id_token(_ISSUER, token, "client-123", "nonce-abc")
    assert exc.value.detail["code"] == "sso.no_jwks_uri"


def test_verify_id_token_ssrf_blocked_jwks(monkeypatch, rsa_keys):
    priv, _ = rsa_keys
    bad_doc = dict(_DISCOVERY_DOC, jwks_uri="http://169.254.169.254/jwks")
    _seed_discovery(monkeypatch, bad_doc)
    token = _sign(priv, _base_claims())
    with pytest.raises(HTTPException) as exc:
        oidc_service.verify_id_token(_ISSUER, token, "client-123", "nonce-abc")
    assert exc.value.detail["code"] == "sso.unsafe_discovery_endpoint"


def test_verify_id_token_hs256_rejected(monkeypatch, rsa_keys):
    """Alg-confusion guard: an HS256 token (symmetric, forgeable if the attacker
    knows the public key) must be rejected — only RS/ES are accepted."""
    _, pub = rsa_keys
    _seed_discovery(monkeypatch)
    _patch_jwks(monkeypatch, pub)
    token = jwt.encode(_base_claims(), "x" * 40, algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        oidc_service.verify_id_token(_ISSUER, token, "client-123", "nonce-abc")
    assert exc.value.detail["code"] == "sso.id_token_verification_failed"
