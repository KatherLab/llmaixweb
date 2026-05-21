"""Fernet encryption/decryption for sensitive fields stored in the database.

Uses the app's SECRET_KEY (hashed to a valid Fernet key) so that we don't
need a separate key management setup.
"""

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from backend.src.core.config import settings


def _derive_fernet_key() -> bytes:
    """Derive a 32-byte url-safe base64-encoded Fernet key from SECRET_KEY."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"llmaixweb-fernet-key-v1",
    )
    raw_key = hkdf.derive(settings.SECRET_KEY.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)


def _get_fernet() -> Fernet:
    return Fernet(_derive_fernet_key())


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a base64-encoded Fernet token."""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string back to plaintext."""
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception:
        # If it's not valid ciphertext, return as-is (backward compat)
        return ciphertext
