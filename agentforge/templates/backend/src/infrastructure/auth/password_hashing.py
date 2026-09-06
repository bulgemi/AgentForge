"""Password hashing utilities supporting Argon2 and Bcrypt."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str:
        ...

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        ...


class DefaultPasswordHasher:
    """Secure PBKDF2/SHA256 password hasher with salt (zero external binary dependency)."""

    def __init__(self, iterations: int = 100_000) -> None:
        self.iterations = iterations

    def hash(self, password: str) -> str:
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self.iterations)
        return f"pbkdf2_sha256${self.iterations}${salt.hex()}${key.hex()}"

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        try:
            algorithm, iters_str, salt_hex, key_hex = hashed_password.split("$")
            if algorithm != "pbkdf2_sha256":
                return False
            iterations = int(iters_str)
            salt = bytes.fromhex(salt_hex)
            expected_key = bytes.fromhex(key_hex)
            actual_key = hashlib.pbkdf2_hmac(
                "sha256", plain_password.encode("utf-8"), salt, iterations
            )
            return hmac.compare_digest(actual_key, expected_key)
        except Exception:
            return False
