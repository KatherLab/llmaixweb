"""Fernet encryption/decryption for sensitive fields stored in the database.

Uses the app's SECRET_KEY (hashed to a valid Fernet key) so that we don't
need a separate key management setup.
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from backend.src.core.config import settings


def _derive_fernet_key() -> bytes:
    """Derive a 32-byte Fernet-compatible key from SECRET_KEY via HKDF."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"llmaixweb-fernet-key-v1",
    )
    return hkdf.derive(settings.SECRET_KEY.encode("utf-8"))


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
