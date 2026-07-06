from __future__ import annotations

import re

from werkzeug.exceptions import BadRequest

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def json_body() -> dict:
    from flask import request

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequest("JSON object is required")
    return data


def required_str(data: dict, field: str, min_length: int = 1, max_length: int = 255) -> str:
    value = data.get(field)
    if not isinstance(value, str):
        raise BadRequest(f"Field '{field}' is required")
    value = value.strip()
    if len(value) < min_length:
        raise BadRequest(f"Field '{field}' is too short")
    if len(value) > max_length:
        raise BadRequest(f"Field '{field}' is too long")
    return value


def optional_str(data: dict, field: str, max_length: int = 255) -> str | None:
    value = data.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise BadRequest(f"Field '{field}' must be a string")
    value = value.strip()
    if not value:
        return None
    if len(value) > max_length:
        raise BadRequest(f"Field '{field}' is too long")
    return value


def valid_email(data: dict) -> str:
    email = required_str(data, "email", max_length=255).lower()
    if not EMAIL_RE.match(email):
        raise BadRequest("Invalid email")
    return email


def bool_value(data: dict, field: str, default: bool = True) -> bool:
    value = data.get(field, default)
    if not isinstance(value, bool):
        raise BadRequest(f"Field '{field}' must be boolean")
    return value


def int_value(data: dict, field: str) -> int:
    value = data.get(field)
    if isinstance(value, bool):
        raise BadRequest(f"Field '{field}' must be integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    raise BadRequest(f"Field '{field}' must be integer")
