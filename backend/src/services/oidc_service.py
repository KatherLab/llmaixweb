# backend/src/services/oidc_service.py
"""OpenID Connect helpers: discovery, authorization URL (with PKCE + signed
state), code exchange, and userinfo retrieval.

State is carried as a short-lived signed JWT (HS256, using the app secret)
rather than server-side session storage — it embeds the provider slug, the
PKCE code_verifier, a nonce, and the post-login redirect path. This keeps the
SSO flow stateless and worker-safe.
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import secrets

import httpx
import jwt
from fastapi import status

from ..core.config import settings
from ..utils.api_errors import api_error
from ..utils.url_safety import UnsafeEndpointError, validate_user_endpoint

logger = logging.getLogger(__name__)

# Per-process discovery cache: issuer -> discovery document. OIDC discovery
# documents are effectively static; a process restart picks up changes.
_DISCOVERY_CACHE: dict[str, dict] = {}

_DISCOVERY_TIMEOUT = 10.0
_TOKEN_TIMEOUT = 15.0
_USERINFO_TIMEOUT = 15.0


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _validate_issuer(issuer_url: str) -> str:
    """SSRF-check the issuer URL. Empty/blocked → 400."""
    try:
        validated = validate_user_endpoint(issuer_url)
    except UnsafeEndpointError as e:
        raise api_error(
            "sso.unsafe_issuer_url",
            status.HTTP_400_BAD_REQUEST,
            f"Unsafe OIDC issuer URL: {e}",
            error=str(e),
        )
    if not validated:
        raise api_error(
            "sso.issuer_url_required",
            status.HTTP_400_BAD_REQUEST,
            "OIDC issuer URL is required.",
        )
    return validated.rstrip("/")


def discover(issuer_url: str) -> dict:
    """Fetch + cache the OIDC discovery document for ``issuer_url``."""
    issuer = _validate_issuer(issuer_url)
    if issuer in _DISCOVERY_CACHE:
        return _DISCOVERY_CACHE[issuer]

    discovery_url = f"{issuer}/.well-known/openid-configuration"
    try:
        resp = httpx.get(discovery_url, timeout=_DISCOVERY_TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        # Don't echo the raw httpx error: it can embed the internal host/port a
        # misconfigured issuer resolved to. Log it, tell the client generically.
        logger.warning("OIDC discovery failed for %s: %s", issuer, e)
        raise api_error(
            "sso.discovery_unreachable",
            status.HTTP_400_BAD_REQUEST,
            "Failed to reach the OIDC discovery endpoint. Check the issuer URL.",
        )
    doc = resp.json()
    # Minimal sanity check — these are the endpoints we actually use.
    if not all(doc.get(k) for k in ("authorization_endpoint", "token_endpoint")):
        raise api_error(
            "sso.discovery_missing_endpoints",
            status.HTTP_400_BAD_REQUEST,
            "OIDC discovery document is missing required endpoints.",
        )
    _DISCOVERY_CACHE[issuer] = doc
    return doc


def _pkce_pair() -> tuple[str, str]:
    """Return ``(code_verifier, code_challenge)`` with S256 challenge."""
    verifier = secrets.token_urlsafe(64)
    challenge = hashlib.sha256(verifier.encode("ascii")).digest()
    import base64

    challenge_b64 = base64.urlsafe_b64encode(challenge).decode("ascii").rstrip("=")
    return verifier, challenge_b64


def _make_state(
    provider_slug: str, code_verifier: str, redirect: str, nonce: str
) -> str:
    payload = {
        "exp": _now() + datetime.timedelta(minutes=10),
        "iss": "llmaixweb-sso",
        "provider": provider_slug,
        "verifier": code_verifier,
        "redirect": redirect or "/",
        # Bound to the OIDC `nonce` sent in the authorize request; verified
        # against the id_token on callback to defend against replay.
        "nonce": nonce,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def _verify_state(state: str) -> dict:
    try:
        payload = jwt.decode(
            state, settings.SECRET_KEY, algorithms=["HS256"], issuer="llmaixweb-sso"
        )
    except jwt.PyJWTError as e:
        logger.info("SSO state rejected: %s", e)
        raise api_error(
            "sso.invalid_state",
            status.HTTP_400_BAD_REQUEST,
            "Invalid or expired SSO state. Please restart the sign-in.",
        )
    return payload


def build_authorization_url(
    issuer_url: str,
    client_id: str,
    redirect_uri: str,
    provider_slug: str,
    scopes: str = "openid email profile",
    post_login_redirect: str = "/",
) -> tuple[str, str]:
    """Return ``(authorize_url, state_jwt)``. The state JWT is set as a cookie
    by the caller and verified on callback."""
    doc = discover(issuer_url)
    verifier, challenge = _pkce_pair()
    nonce = secrets.token_urlsafe(16)
    state = _make_state(provider_slug, verifier, post_login_redirect, nonce)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes or "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    req = httpx.Request("GET", doc["authorization_endpoint"], params=params)
    return str(req.url), state


def exchange_code(
    issuer_url: str,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict:
    """Exchange an authorization code for a token response (id_token + access_token)."""
    doc = discover(issuer_url)
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
        "code_verifier": code_verifier,
    }
    try:
        resp = httpx.post(doc["token_endpoint"], data=data, timeout=_TOKEN_TIMEOUT)
    except httpx.HTTPError as e:
        logger.warning("OIDC token endpoint unreachable (%s): %s", issuer_url, e)
        raise api_error(
            "sso.token_endpoint_unreachable",
            status.HTTP_502_BAD_GATEWAY,
            "Failed to contact the OIDC token endpoint.",
        )
    if resp.status_code != 200:
        # The IdP's response body can contain sensitive details — log it, don't
        # echo it back to the browser.
        logger.warning(
            "OIDC token exchange failed (%s): %s %s",
            issuer_url,
            resp.status_code,
            resp.text[:300],
        )
        raise api_error(
            "sso.token_exchange_failed",
            status.HTTP_400_BAD_REQUEST,
            "OIDC token exchange failed.",
        )
    return resp.json()


def fetch_userinfo(issuer_url: str, access_token: str) -> dict:
    """Fetch userinfo from the IdP. Validates the returned ``iss`` matches the issuer."""
    doc = discover(issuer_url)
    userinfo_endpoint = doc.get("userinfo_endpoint")
    if not userinfo_endpoint:
        # No userinfo endpoint — caller must decode the id_token instead.
        return {}

    try:
        resp = httpx.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=_USERINFO_TIMEOUT,
        )
    except httpx.HTTPError as e:
        logger.warning("OIDC userinfo endpoint unreachable (%s): %s", issuer_url, e)
        raise api_error(
            "sso.userinfo_endpoint_unreachable",
            status.HTTP_502_BAD_GATEWAY,
            "Failed to contact the OIDC userinfo endpoint.",
        )
    if resp.status_code != 200:
        logger.warning(
            "OIDC userinfo request failed (%s): %s %s",
            issuer_url,
            resp.status_code,
            resp.text[:300],
        )
        raise api_error(
            "sso.userinfo_request_failed",
            status.HTTP_400_BAD_REQUEST,
            "OIDC userinfo request failed.",
        )
    info = resp.json()
    # `iss` claim validation guards against token mix-up across providers.
    expected_issuer = _validate_issuer(issuer_url)
    if info.get("iss") and info["iss"] != expected_issuer:
        raise api_error(
            "sso.userinfo_issuer_mismatch",
            status.HTTP_400_BAD_REQUEST,
            "OIDC userinfo issuer mismatch.",
        )
    return info


def verify_id_token(
    issuer_url: str,
    id_token: str,
    client_id: str,
    nonce: str | None = None,
) -> dict:
    """Verify an OIDC id_token's signature and claims, returning its payload.

    Fetches the IdP's JWKS (from the SSRF-validated, admin-configured discovery
    document), verifies the RS/ES signature, and validates ``aud`` (== our
    client_id), ``iss``, ``exp``, and — when provided — the ``nonce`` binding.
    Raises HTTP 400 on any failure. This replaces the previous
    ``verify_signature=False`` decode, which trusted attacker-influenceable
    token contents for account provisioning.
    """
    doc = discover(issuer_url)
    jwks_uri = doc.get("jwks_uri")
    issuer = doc.get("issuer") or _validate_issuer(issuer_url)
    if not jwks_uri:
        raise api_error(
            "sso.no_jwks_uri",
            status.HTTP_400_BAD_REQUEST,
            "OIDC discovery document has no jwks_uri; cannot verify id_token.",
        )
    try:
        jwk_client = jwt.PyJWKClient(jwks_uri)
        signing_key = jwk_client.get_signing_key_from_jwt(id_token)
        payload = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
            audience=client_id,
            issuer=issuer,
        )
    except jwt.PyJWTError as e:
        logger.warning("OIDC id_token verification failed (%s): %s", issuer_url, e)
        raise api_error(
            "sso.id_token_verification_failed",
            status.HTTP_400_BAD_REQUEST,
            "OIDC id_token verification failed.",
        )
    if nonce is not None and payload.get("nonce") != nonce:
        raise api_error(
            "sso.id_token_nonce_mismatch",
            status.HTTP_400_BAD_REQUEST,
            "OIDC id_token nonce mismatch.",
        )
    return payload


def decode_state(state: str) -> dict:
    """Public wrapper for the router to extract verifier + redirect."""
    return _verify_state(state)
