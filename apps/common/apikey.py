"""
Secure API key utilities.

Key format: <prefix>.<secret>
  - prefix: 8-character URL-safe string used for fast DB lookup
  - secret: 48-character URL-safe random string

Storage: only the prefix and a SHA-256 hash of the full key are stored.
The raw key is returned once at creation time and never stored.

Verification uses hmac.compare_digest to prevent timing attacks.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

# Key structure constants
PREFIX_LENGTH = 8
SECRET_LENGTH = 48


def generate_key() -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        (raw_key, prefix, key_hash) - raw_key is shown to the user once,
        prefix and key_hash are stored in the database.
    """
    prefix = secrets.token_urlsafe(PREFIX_LENGTH)[:PREFIX_LENGTH]
    secret = secrets.token_urlsafe(SECRET_LENGTH)
    raw_key = f"{prefix}.{secret}"
    key_hash = _hash_key(raw_key)
    return raw_key, prefix, key_hash


def verify_key(raw_key: str, stored_hash: str) -> bool:
    """
    Verify a raw API key against a stored hash using constant-time comparison.

    Args:
        raw_key: The full key provided by the client.
        stored_hash: The SHA-256 hash stored in the database.

    Returns:
        True if the key matches, False otherwise.
    """
    computed_hash = _hash_key(raw_key)
    return hmac.compare_digest(computed_hash, stored_hash)


def parse_prefix(raw_key: str) -> str | None:
    """
    Extract the prefix from a raw API key.

    Returns:
        The prefix string, or None if the key format is invalid.
    """
    if '.' not in raw_key:
        return None
    prefix = raw_key.split('.', 1)[0]
    if not prefix:
        return None
    return prefix


def _hash_key(raw_key: str) -> str:
    """Compute a SHA-256 hex digest of the raw key."""
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

