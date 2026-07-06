from __future__ import annotations

from flask import Blueprint
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest

from app.authz import require_admin
from app.db import db
from app.models import Permission, Resource, Role, User, UserRole
from app.serializers import (
    permission_to_dict,
    resource_to_dict,
    role_to_dict,
    user_role_to_dict,
    user_to_dict,
)
from app.validation import bool_value, int_value, json_body, optional_str, required_str

admin_bp = Blueprint("admin", __name__)


def _commit_or_bad_request(message: str):
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise BadRequest(message) from exc


@admin_bp.get("/rules")
@require_admin
def get_rules():
    return {
        "roles": [role_to_dict(role) for role in Role.query.order_by(Role.id)],
        "resources": [
            resource_to_dict(resource) for resource in Resource.query.order_by(Resource.id)
        ],
        "permissions": [
            permission_to_dict(permission)
            for permission in Permission.query.order_by(Permission.id)
        ],
        "user_roles": [
            user_role_to_dict(user_role) for user_role in UserRole.query.order_by(UserRole.id)
        ],
    }


@admin_bp.get("/users")
@require_admin
def get_users():
    return {"items": [user_to_dict(user) for user in User.query.order_by(User.id)]}


@admin_bp.post("/roles")
@require_admin
def create_role():
    data = json_body()
    role = Role(
        code=required_str(data, "code", max_length=80),
        name=required_str(data, "name", max_length=120),
        description=optional_str(data, "description", max_length=255),
    )
    db.session.add(role)
    _commit_or_bad_request("Role code must be unique")
    return {"role": role_to_dict(role)}, 201


@admin_bp.patch("/roles/<int:role_id>")
@require_admin
def update_role(role_id: int):
    role = db.session.get(Role, role_id)
    if not role:
        raise BadRequest("Role not found")
    data = json_body()
    if "code" in data:
        role.code = required_str(data, "code", max_length=80)
    if "name" in data:
        role.name = required_str(data, "name", max_length=120)
    if "description" in data:
        role.description = optional_str(data, "description", max_length=255)
    _commit_or_bad_request("Role code must be unique")
    return {"role": role_to_dict(role)}


@admin_bp.delete("/roles/<int:role_id>")
@require_admin
def delete_role(role_id: int):
    role = db.session.get(Role, role_id)
    if not role:
        raise BadRequest("Role not found")
    if role.code == "admin":
        raise BadRequest("Admin role cannot be deleted")
    db.session.delete(role)
    db.session.commit()
    return {"status": "deleted"}


@admin_bp.post("/resources")
@require_admin
def create_resource():
    data = json_body()
    resource = Resource(
        code=required_str(data, "code", max_length=100),
        name=required_str(data, "name", max_length=120),
        description=optional_str(data, "description", max_length=255),
    )
    db.session.add(resource)
    _commit_or_bad_request("Resource code must be unique")
    return {"resource": resource_to_dict(resource)}, 201


@admin_bp.patch("/resources/<int:resource_id>")
@require_admin
def update_resource(resource_id: int):
    resource = db.session.get(Resource, resource_id)
    if not resource:
        raise BadRequest("Resource not found")
    data = json_body()
    if "code" in data:
        resource.code = required_str(data, "code", max_length=100)
    if "name" in data:
        resource.name = required_str(data, "name", max_length=120)
    if "description" in data:
        resource.description = optional_str(data, "description", max_length=255)
    _commit_or_bad_request("Resource code must be unique")
    return {"resource": resource_to_dict(resource)}


@admin_bp.delete("/resources/<int:resource_id>")
@require_admin
def delete_resource(resource_id: int):
    resource = db.session.get(Resource, resource_id)
    if not resource:
        raise BadRequest("Resource not found")
    db.session.delete(resource)
    db.session.commit()
    return {"status": "deleted"}


@admin_bp.post("/permissions")
@require_admin
def create_permission():
    data = json_body()
    role = db.session.get(Role, int_value(data, "role_id"))
    resource = db.session.get(Resource, int_value(data, "resource_id"))
    if not role or not resource:
        raise BadRequest("Role and resource must exist")

    permission = Permission(
        role=role,
        resource=resource,
        action=required_str(data, "action", max_length=40),
        is_allowed=bool_value(data, "is_allowed", True),
    )
    db.session.add(permission)
    _commit_or_bad_request("Permission for this role/resource/action already exists")
    return {"permission": permission_to_dict(permission)}, 201


@admin_bp.patch("/permissions/<int:permission_id>")
@require_admin
def update_permission(permission_id: int):
    permission = db.session.get(Permission, permission_id)
    if not permission:
        raise BadRequest("Permission not found")
    data = json_body()
    if "role_id" in data:
        role = db.session.get(Role, int_value(data, "role_id"))
        if not role:
            raise BadRequest("Role must exist")
        permission.role = role
    if "resource_id" in data:
        resource = db.session.get(Resource, int_value(data, "resource_id"))
        if not resource:
            raise BadRequest("Resource must exist")
        permission.resource = resource
    if "action" in data:
        permission.action = required_str(data, "action", max_length=40)
    if "is_allowed" in data:
        permission.is_allowed = bool_value(data, "is_allowed")
    _commit_or_bad_request("Permission for this role/resource/action already exists")
    return {"permission": permission_to_dict(permission)}


@admin_bp.delete("/permissions/<int:permission_id>")
@require_admin
def delete_permission(permission_id: int):
    permission = db.session.get(Permission, permission_id)
    if not permission:
        raise BadRequest("Permission not found")
    db.session.delete(permission)
    db.session.commit()
    return {"status": "deleted"}


@admin_bp.post("/user-roles")
@require_admin
def assign_user_role():
    data = json_body()
    user = db.session.get(User, int_value(data, "user_id"))
    role = db.session.get(Role, int_value(data, "role_id"))
    if not user or not role:
        raise BadRequest("User and role must exist")

    user_role = UserRole(user=user, role=role)
    db.session.add(user_role)
    _commit_or_bad_request("User already has this role")
    return {"user_role": user_role_to_dict(user_role)}, 201


@admin_bp.delete("/user-roles/<int:user_role_id>")
@require_admin
def delete_user_role(user_role_id: int):
    user_role = db.session.get(UserRole, user_role_id)
    if not user_role:
        raise BadRequest("User role not found")
    db.session.delete(user_role)
    db.session.commit()
    return {"status": "deleted"}
