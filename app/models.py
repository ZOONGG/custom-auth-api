from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db import db


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    middle_name = db.Column(db.String(80), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
    deleted_at = db.Column(db.DateTime, nullable=True)

    sessions = db.relationship("SessionToken", back_populates="user")
    role_links = db.relationship("UserRole", back_populates="user", cascade="all, delete-orphan")


class SessionToken(db.Model):
    __tablename__ = "session_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(255), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: utcnow() + timedelta(days=7),
    )
    revoked_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="sessions")


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), nullable=False, unique=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    user_links = db.relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    permissions = db.relationship("Permission", back_populates="role", cascade="all, delete-orphan")


class UserRole(db.Model):
    __tablename__ = "user_roles"
    __table_args__ = (db.UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)

    user = db.relationship("User", back_populates="role_links")
    role = db.relationship("Role", back_populates="user_links")


class Resource(db.Model):
    __tablename__ = "resources"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), nullable=False, unique=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    permissions = db.relationship(
        "Permission", back_populates="resource", cascade="all, delete-orphan"
    )


class Permission(db.Model):
    __tablename__ = "permissions"
    __table_args__ = (
        db.UniqueConstraint("role_id", "resource_id", "action", name="uq_role_resource_action"),
    )

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id"), nullable=False)
    action = db.Column(db.String(40), nullable=False)
    is_allowed = db.Column(db.Boolean, nullable=False, default=True)

    role = db.relationship("Role", back_populates="permissions")
    resource = db.relationship("Resource", back_populates="permissions")
