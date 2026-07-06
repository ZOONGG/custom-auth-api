from __future__ import annotations

from flask import Blueprint, g
from werkzeug.exceptions import BadRequest, Unauthorized

from app.authz import require_auth
from app.db import db
from app.models import Role, SessionToken, User, UserRole, utcnow
from app.security import hash_password, hash_token, issue_plain_token, verify_password
from app.serializers import user_to_dict
from app.validation import json_body, optional_str, required_str, valid_email

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    data = json_body()
    email = valid_email(data)
    password = required_str(data, "password", min_length=8)
    password_repeat = required_str(data, "password_repeat", min_length=8)
    if password != password_repeat:
        raise BadRequest("Passwords do not match")
    if User.query.filter_by(email=email).first():
        raise BadRequest("User with this email already exists")

    user = User(
        email=email,
        password_hash=hash_password(password),
        first_name=required_str(data, "first_name", max_length=80),
        last_name=required_str(data, "last_name", max_length=80),
        middle_name=optional_str(data, "middle_name", max_length=80),
    )
    user_role = Role.query.filter_by(code="user").first()
    if user_role:
        user.role_links.append(UserRole(role=user_role))

    db.session.add(user)
    db.session.commit()
    return {"user": user_to_dict(user)}, 201


@auth_bp.post("/login")
def login():
    data = json_body()
    email = valid_email(data)
    password = required_str(data, "password", min_length=1)

    user = User.query.filter_by(email=email).first()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise Unauthorized("Invalid email or password")

    token = issue_plain_token()
    session = SessionToken(user=user, token_hash=hash_token(token))
    db.session.add(session)
    db.session.commit()
    return {"token": token, "token_type": "Bearer", "user": user_to_dict(user)}


@auth_bp.post("/logout")
@require_auth
def logout():
    g.current_session.revoked_at = utcnow()
    db.session.commit()
    return {"status": "logged_out"}


@auth_bp.get("/me")
@require_auth
def me():
    return {"user": user_to_dict(g.current_user)}


@auth_bp.patch("/me")
@require_auth
def update_me():
    data = json_body()
    user = g.current_user

    if "email" in data:
        email = valid_email(data)
        existing = User.query.filter(User.email == email, User.id != user.id).first()
        if existing:
            raise BadRequest("User with this email already exists")
        user.email = email
    if "first_name" in data:
        user.first_name = required_str(data, "first_name", max_length=80)
    if "last_name" in data:
        user.last_name = required_str(data, "last_name", max_length=80)
    if "middle_name" in data:
        user.middle_name = optional_str(data, "middle_name", max_length=80)
    if "password" in data or "password_repeat" in data:
        password = required_str(data, "password", min_length=8)
        password_repeat = required_str(data, "password_repeat", min_length=8)
        if password != password_repeat:
            raise BadRequest("Passwords do not match")
        user.password_hash = hash_password(password)

    db.session.commit()
    return {"user": user_to_dict(user)}


@auth_bp.delete("/me")
@require_auth
def delete_me():
    user = g.current_user
    user.is_active = False
    user.deleted_at = utcnow()
    SessionToken.query.filter_by(user_id=user.id, revoked_at=None).update(
        {"revoked_at": utcnow()}, synchronize_session=False
    )
    db.session.commit()
    return {"status": "deleted"}
