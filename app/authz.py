from __future__ import annotations

from datetime import UTC, datetime
from functools import wraps

from flask import g, request
from werkzeug.exceptions import Forbidden, Unauthorized

from app.models import Permission, Resource, Role, SessionToken, User, UserRole
from app.security import hash_token


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _bearer_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header.removeprefix("Bearer ").strip()
    return token or None


def get_current_user() -> User | None:
    token = _bearer_token()
    if not token:
        return None

    session = SessionToken.query.filter_by(token_hash=hash_token(token)).first()
    if not session or session.revoked_at or session.expires_at <= _now():
        return None
    if not session.user or not session.user.is_active:
        return None

    g.current_session = session
    return session.user


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            raise Unauthorized("Login is required")
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def user_has_role(user: User, role_code: str) -> bool:
    return (
        UserRole.query.join(Role)
        .filter(UserRole.user_id == user.id, Role.code == role_code)
        .first()
        is not None
    )


def user_has_permission(user: User, resource_code: str, action: str) -> bool:
    if user_has_role(user, "admin"):
        return True

    return (
        Permission.query.join(Resource)
        .join(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(
            UserRole.user_id == user.id,
            Resource.code == resource_code,
            Permission.action == action,
            Permission.is_allowed.is_(True),
        )
        .first()
        is not None
    )


def require_permission(resource_code: str, action: str):
    def decorator(fn):
        @wraps(fn)
        @require_auth
        def wrapper(*args, **kwargs):
            if not user_has_permission(g.current_user, resource_code, action):
                raise Forbidden("You do not have access to this resource")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def require_admin(fn):
    @wraps(fn)
    @require_auth
    def wrapper(*args, **kwargs):
        if not user_has_role(g.current_user, "admin"):
            raise Forbidden("Admin role is required")
        return fn(*args, **kwargs)

    return wrapper
