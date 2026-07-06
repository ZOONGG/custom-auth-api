from __future__ import annotations

from flask import Flask, current_app, has_app_context

from app import create_app
from app.db import db
from app.models import Permission, Resource, Role, User, UserRole
from app.security import hash_password, verify_password


def get_or_create(model, defaults: dict | None = None, **filters):
    instance = model.query.filter_by(**filters).first()
    if instance:
        return instance
    params = {**filters, **(defaults or {})}
    instance = model(**params)
    db.session.add(instance)
    return instance


def ensure_seed_password(user: User, password: str) -> None:
    if not verify_password(password, user.password_hash):
        user.password_hash = hash_password(password)


def seed(app: Flask | None = None) -> None:
    app = app or (current_app._get_current_object() if has_app_context() else create_app())
    with app.app_context():
        db.create_all()

        admin = get_or_create(
            Role,
            code="admin",
            defaults={
                "name": "Administrator",
                "description": "Can manage users and access rules",
            },
        )
        manager = get_or_create(
            Role,
            code="manager",
            defaults={"name": "Manager", "description": "Can read and change business data"},
        )
        user_role = get_or_create(
            Role,
            code="user",
            defaults={"name": "User", "description": "Can read public business data"},
        )

        projects = get_or_create(
            Resource,
            code="projects",
            defaults={"name": "Projects", "description": "Mock project list"},
        )
        reports = get_or_create(
            Resource,
            code="reports",
            defaults={"name": "Reports", "description": "Mock report list"},
        )
        access_rules = get_or_create(
            Resource,
            code="access_rules",
            defaults={
                "name": "Access rules",
                "description": "Roles, resources and permissions management",
            },
        )

        for role, resource, action in [
            (user_role, projects, "read"),
            (manager, projects, "read"),
            (manager, projects, "write"),
            (manager, reports, "read"),
            (admin, projects, "read"),
            (admin, projects, "write"),
            (admin, reports, "read"),
            (admin, reports, "write"),
            (admin, access_rules, "manage"),
        ]:
            get_or_create(
                Permission,
                role_id=role.id,
                resource_id=resource.id,
                action=action,
                defaults={"is_allowed": True},
            )

        admin_user = get_or_create(
            User,
            email="admin@example.com",
            defaults={
                "password_hash": hash_password("Admin12345"),
                "first_name": "Alice",
                "last_name": "Admin",
                "middle_name": None,
            },
        )
        manager_user = get_or_create(
            User,
            email="manager@example.com",
            defaults={
                "password_hash": hash_password("Manager12345"),
                "first_name": "Mark",
                "last_name": "Manager",
                "middle_name": None,
            },
        )
        regular_user = get_or_create(
            User,
            email="user@example.com",
            defaults={
                "password_hash": hash_password("User12345"),
                "first_name": "Uma",
                "last_name": "User",
                "middle_name": None,
            },
        )
        ensure_seed_password(admin_user, "Admin12345")
        ensure_seed_password(manager_user, "Manager12345")
        ensure_seed_password(regular_user, "User12345")

        for user, role in [
            (admin_user, admin),
            (manager_user, manager),
            (regular_user, user_role),
        ]:
            get_or_create(UserRole, user_id=user.id, role_id=role.id)

        db.session.commit()


if __name__ == "__main__":
    seed()
    print("Database seeded")
