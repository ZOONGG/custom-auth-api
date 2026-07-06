from __future__ import annotations

from app.models import Permission, Resource, Role, SessionToken, User, UserRole


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "middle_name": user.middle_name,
        "is_active": user.is_active,
        "roles": [link.role.code for link in user.role_links],
    }


def role_to_dict(role: Role) -> dict:
    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
    }


def resource_to_dict(resource: Resource) -> dict:
    return {
        "id": resource.id,
        "code": resource.code,
        "name": resource.name,
        "description": resource.description,
    }


def permission_to_dict(permission: Permission) -> dict:
    return {
        "id": permission.id,
        "role": role_to_dict(permission.role),
        "resource": resource_to_dict(permission.resource),
        "action": permission.action,
        "is_allowed": permission.is_allowed,
    }


def user_role_to_dict(user_role: UserRole) -> dict:
    return {
        "id": user_role.id,
        "user_id": user_role.user_id,
        "role": role_to_dict(user_role.role),
    }


def session_to_dict(session: SessionToken) -> dict:
    return {
        "id": session.id,
        "user_id": session.user_id,
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "revoked_at": session.revoked_at.isoformat() if session.revoked_at else None,
    }
