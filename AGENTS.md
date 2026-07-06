# AGENTS.md

## Project Purpose

This is a test backend application with custom authentication and custom role-based access control.

The original employer assignment is stored in `docs/TASK.md`. Check it before changing behavior.

Frontend, mobile application, and `.exe` deliverables are not required.

## Approved Stack

The current Flask + SQLite architecture is approved for this test assignment. Do not rewrite the project to Django, DRF, PostgreSQL, JWT, or Docker unless the assignment is explicitly changed.

Use the current stack:

- Python
- Flask
- Flask-SQLAlchemy
- SQLite
- Werkzeug password hashing
- Opaque server-side bearer sessions
- Custom RBAC
- `unittest`
- PowerShell manual smoke test

## Architecture

Current structure:

```text
app/                  Flask application, routes, models, authorization, validation
app/routes/auth.py    registration, login, logout, profile, soft delete
app/routes/admin.py   administrative RBAC API
app/routes/business.py protected mock business endpoints
tests/                unittest API tests
scripts/              manual smoke-test scripts
docs/                 assignment documentation
seed.py               demo data seeding
```

## Authentication

Do not create custom password cryptography. Use Werkzeug:

- `generate_password_hash`
- `check_password_hash`

Sessions are opaque bearer tokens:

- the plaintext token is returned only at login;
- only a SHA-256 token digest is stored in `session_tokens`;
- logout marks the current session as revoked;
- soft delete revokes active user sessions.

An inactive user with `is_active=False` cannot log in or access protected resources.

User deletion is soft deletion:

```text
is_active=False
deleted_at=<timestamp>
```

The user row must remain in the database.

## Authorization

Do not use Flask-Login, Django Groups, Django Permissions, or framework permissions as the main access system.

The project uses custom RBAC tables:

```text
Role
Resource
Permission
UserRole
```

Permissions are defined by:

```text
role + resource + action
```

Examples:

```text
projects:read
projects:write
reports:read
reports:write
access_rules:manage
```

A user has access when at least one assigned role contains the required allowed permission. The centralized access-checking logic lives in `app/authz.py`; do not duplicate equivalent checks in each view.

The current administrative API is restricted to users with the `admin` role.

## HTTP Responses

Keep authentication and authorization errors distinct:

- missing user, missing bearer token, invalid token, revoked token, expired token, or inactive user: `401 Unauthorized`;
- authenticated user without the required access: `403 Forbidden`;
- valid access: return the requested resource.

## Administrative API

An administrator can:

- manage roles;
- manage resources;
- manage permissions;
- assign roles to users;
- remove user-role assignments.

An ordinary user cannot assign roles, assign permissions, or change privileged access-control data, including their own role assignment.

## Mock Resources

Protected mock endpoints currently cover:

```text
projects
reports
```

These objects do not require business tables; static JSON responses are acceptable. Each protected endpoint must specify its required resource and action through the centralized authorization decorator.

## Working Order

For each change:

1. Read `docs/TASK.md` and this file.
2. Inspect the existing code.
3. Make a short, scoped plan.
4. Implement the minimal complete change.
5. Add or update `unittest` tests.
6. Run focused tests.
7. Run the full test suite.
8. Check relevant `401` and `403` behavior.
9. Update `README.md` when behavior or commands change.
10. Keep commits small when a Git repository is available.

Do not implement unrelated features outside the assignment.

## Checks

After behavior changes, run applicable commands:

```powershell
python seed.py
python -m unittest discover -s tests -v
.\scripts\manual_smoke_test.ps1
```

Run the smoke test against a running local server.

## Restrictions

Do not add without a clear assignment need:

- frontend;
- Celery;
- Redis;
- Kafka;
- Kubernetes;
- microservices;
- GraphQL;
- custom password cryptography;
- JWT;
- Docker;
- functionality outside the test assignment.

Do not commit:

- `.env`;
- secrets;
- real passwords or production credentials;
- generated SQLite databases;
- bearer tokens;
- virtual environments;
- Python caches;
- logs;
- temporary files.

Prefer simple, explicit, readable code.
