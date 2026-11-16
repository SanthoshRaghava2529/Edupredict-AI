"""Password hashing using PBKDF2-HMAC-SHA256. Passwords are never stored in plain text."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

ITERATIONS = 200_000
SALT_BYTES = 16
HASH_NAME = "sha256"


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty.")
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(HASH_NAME, password.encode("utf-8"), salt, ITERATIONS)
    return f"{HASH_NAME}${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt_hex, digest_hex = stored_hash.split("$", 3)
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(algorithm, password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def generate_temp_password(length: int = 10) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))
