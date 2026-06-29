# backend/src/utils/crypto.py
"""Fernet encryption/decryption for sensitive fields stored in the database.

Uses the app's SECRET_KEY (hashed to a valid Fernet key) so that we don't
need a separate key management setup.
"""

import base64
import logging
from functools import lru_cache

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from ..core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _derive_fernet_key() -> bytes:
    """Derive a 32-byte url-safe base64-encoded Fernet key from SECRET_KEY.

    Cached because SECRET_KEY is constant for the process lifetime; deriving it
    (HKDF) on every encrypt/decrypt call was wasted CPU.

    A fixed application salt is used (rather than ``salt=None``) per RFC 5869:
    the input key material (SECRET_KEY) is not guaranteed to be uniformly
    random, and a non-empty salt strengthens the HKDF-Extract step. NOTE: this
    salt is part of the key derivation — changing it (or the ``info`` version
    tag) rotates the derived key and invalidates existing ciphertexts.
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"llmaixweb-fernet-salt-v1",
        info=b"llmaixweb-fernet-key-v1",
    )
    raw_key = hkdf.derive(settings.SECRET_KEY.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    return Fernet(_derive_fernet_key())


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a base64-encoded Fernet token."""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string back to plaintext.

    On any failure (corrupted token, rotated SECRET_KEY, or a value that was
    never encrypted) we log a warning and return an empty string rather than
    the raw input. Returning the raw value as-is would silently bypass the
    encryption layer: anything written to an encrypted column as plaintext
    would decrypt to plaintext, defeating the purpose of encrypting at rest.
    Returning "" makes the failure observable (the key simply won't work)
    instead of leaking the stored bytes as if they were a valid secret.
    """
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.warning(
            "Failed to decrypt an encrypted field (%s); returning empty. "
            "This usually means SECRET_KEY was rotated or the value was not "
            "written through the encrypt() path.",
            type(e).__name__,
        )
        return ""
