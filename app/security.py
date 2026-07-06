from __future__ import annotations

import hashlib
import secrets

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    try:
        return check_password_hash(stored_hash, password)
    except ValueError:
        return False


def issue_plain_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
