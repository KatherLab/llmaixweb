# backend/tests/test_crypto.py
"""Pure-unit tests for ``utils/crypto.py`` (Fernet encrypt/decrypt at rest).

Covers round-trip fidelity, the empty-string short-circuits, the
fail-closed decrypt (garbage / rotated-key -> "" not the raw bytes), and the
``@lru_cache``d key derivation. The rotation test is careful to clear the
``_derive_fernet_key`` / ``_get_fernet`` caches both before mutating
``SECRET_KEY`` and afterwards, so cache state never leaks into other tests.
"""

import base64

import pytest

from backend.src.utils import crypto
from backend.src.utils.crypto import decrypt, encrypt


@pytest.fixture(autouse=True)
def _clean_key_caches():
    """Guarantee a pristine derived-key cache around every test."""
    crypto._derive_fernet_key.cache_clear()
    crypto._get_fernet.cache_clear()
    yield
    crypto._derive_fernet_key.cache_clear()
    crypto._get_fernet.cache_clear()


# --------------------------------------------------------------------------- #
# Round-trip
# --------------------------------------------------------------------------- #
class TestRoundTrip:
    @pytest.mark.parametrize(
        "plaintext",
        [
            "hello world",
            "sk-proj-abc123-secret-token",
            "unicode: café ünïcödé 日本語 🔐",
            "x" * 10000,  # long
            " leading/trailing spaces ",
            "line1\nline2\ttabbed",
        ],
    )
    def test_encrypt_then_decrypt_is_identity(self, plaintext):
        assert decrypt(encrypt(plaintext)) == plaintext

    def test_ciphertext_differs_from_plaintext(self):
        pt = "super-secret-value"
        ct = encrypt(pt)
        assert ct != pt
        assert pt not in ct

    def test_ciphertext_is_nondeterministic(self):
        # Fernet embeds a random IV + timestamp, so two encryptions differ...
        pt = "same-input"
        a, b = encrypt(pt), encrypt(pt)
        assert a != b
        # ...but both decrypt back to the original.
        assert decrypt(a) == pt
        assert decrypt(b) == pt


# --------------------------------------------------------------------------- #
# Empty-string short-circuits
# --------------------------------------------------------------------------- #
class TestEmptyShortCircuit:
    def test_encrypt_empty_returns_empty(self):
        assert encrypt("") == ""

    def test_decrypt_empty_returns_empty(self):
        assert decrypt("") == ""

    def test_round_trip_empty(self):
        assert decrypt(encrypt("")) == ""


# --------------------------------------------------------------------------- #
# Fail-closed decrypt
# --------------------------------------------------------------------------- #
class TestDecryptFailClosed:
    @pytest.mark.parametrize(
        "garbage",
        [
            "not-a-fernet-token",
            "plaintext-that-was-never-encrypted",
            base64.urlsafe_b64encode(b"random bytes not a fernet token").decode(),
            "!!!invalid base64!!!",
            "gAAAAABmZm-truncated",
        ],
    )
    def test_garbage_returns_empty_string_not_raw(self, garbage):
        # Must fail closed: return "" rather than leaking the stored bytes as
        # if they were a valid secret, and must not raise.
        assert decrypt(garbage) == ""

    def test_failure_is_logged(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING, logger=crypto.logger.name):
            assert decrypt("definitely-not-a-token") == ""
        assert any("Failed to decrypt" in r.message for r in caplog.records)

    def test_ciphertext_from_other_key_does_not_leak(self):
        # A token produced by a *different* Fernet key must not decrypt to
        # anything (fail closed), and must not round-trip the wrong plaintext.
        from cryptography.fernet import Fernet

        foreign = Fernet(Fernet.generate_key())
        foreign_token = foreign.encrypt(b"attacker-controlled").decode()
        assert decrypt(foreign_token) == ""


# --------------------------------------------------------------------------- #
# Key derivation (@lru_cache) + rotation
# --------------------------------------------------------------------------- #
class TestKeyDerivation:
    def test_derived_key_is_valid_fernet_key(self):
        key = crypto._derive_fernet_key()
        # url-safe base64 of 32 raw bytes -> 44 chars, decodes to 32 bytes.
        assert isinstance(key, bytes)
        assert len(key) == 44
        assert len(base64.urlsafe_b64decode(key)) == 32

    def test_derive_is_cached(self):
        # Same object returned from the lru_cache on repeat calls.
        assert crypto._derive_fernet_key() is crypto._derive_fernet_key()

    def test_get_fernet_is_cached(self):
        from cryptography.fernet import Fernet

        f = crypto._get_fernet()
        assert isinstance(f, Fernet)
        assert crypto._get_fernet() is f

    def test_key_rotation_invalidates_old_ciphertext(self, monkeypatch):
        """After rotating SECRET_KEY, previously-encrypted tokens no longer decrypt.

        ``_derive_fernet_key`` / ``_get_fernet`` are cached, so the caches must
        be cleared *after* mutating SECRET_KEY for the new key to take effect,
        and cleared again on teardown (handled by the autouse fixture) so a
        stale key never poisons later tests.
        """
        from backend.src.core import config

        # Encrypt under the original key.
        token = encrypt("rotate-me")
        assert token
        assert decrypt(token) == "rotate-me"

        inst = config._get_settings()
        original = inst.SECRET_KEY
        try:
            monkeypatch.setattr(
                inst, "SECRET_KEY", "an-entirely-different-secret-key-value-123456"
            )
            # New key must take effect: bust the derived-key caches.
            crypto._derive_fernet_key.cache_clear()
            crypto._get_fernet.cache_clear()

            # Old token can no longer be decrypted -> fail closed to "".
            assert decrypt(token) == ""

            # And a fresh round-trip works under the new key.
            new_token = encrypt("under-new-key")
            assert decrypt(new_token) == "under-new-key"
        finally:
            # Restore original key + caches (monkeypatch also auto-undoes).
            monkeypatch.setattr(inst, "SECRET_KEY", original)
            crypto._derive_fernet_key.cache_clear()
            crypto._get_fernet.cache_clear()
