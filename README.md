# Custom Auth API

Backend API for a test assignment with custom authentication and custom role-based access control.

The project intentionally uses Flask, Flask-SQLAlchemy, and SQLite. This stack was selected and approved for the assignment because it keeps the submission small, easy to run locally, and focused on the authentication/authorization logic instead of infrastructure.

## What It Does

- Registers users by email and password.
- Logs users in and returns an opaque bearer session token.
- Logs users out by revoking the current server-side session.
- Lets an authenticated user read and update their profile.
- Soft-deletes a user by setting `is_active=False` while keeping the database row.
- Protects mock business endpoints with custom RBAC checks.
- Exposes an admin API for roles, resources, permissions, and user-role assignments.

## Authentication Versus Authorization

Authentication answers "who is the caller?"

- The API reads `Authorization: Bearer <token>`.
- It looks up a non-revoked, non-expired server-side session in `session_tokens`.
- It rejects missing, invalid, expired, revoked, or inactive-user sessions with `401 Unauthorized`.

Authorization answers "is this caller allowed to do this?"

- Protected business endpoints declare a required `resource + action`.
- The RBAC checker verifies that at least one assigned user role has an allowed permission.
- Authenticated users without the required access receive `403 Forbidden`.

## Bearer Sessions

Login returns a random opaque token and `token_type: Bearer`. The plaintext token is shown only once in the login response.

The database stores only `sha256(token)` in `session_tokens`, along with:

- `user_id`
- `created_at`
- `expires_at`
- `revoked_at`

Logout sets `revoked_at` on the current session. Soft delete revokes all active sessions for that user.

## Database Tables

| Table | Purpose |
| --- | --- |
| `users` | User profile, email, password hash, `is_active`, and soft-delete timestamp. |
| `session_tokens` | Server-side bearer sessions; stores token digests, expiry, and revocation. |
| `roles` | RBAC roles such as `admin`, `manager`, and `user`. |
| `user_roles` | Many-to-many assignments between users and roles. |
| `resources` | Protected resource codes such as `projects`, `reports`, and `access_rules`. |
| `permissions` | RBAC rules: `role_id + resource_id + action -> is_allowed`. |

RBAC relationship:

```text
users -> user_roles -> roles -> permissions -> resources
```

## Seeded Users

Run `python seed.py` to create or update demo data.

These are development credentials only:

| Email | Password | Role |
| --- | --- | --- |
| `admin@example.com` | `Admin12345` | `admin` |
| `manager@example.com` | `Manager12345` | `manager` |
| `user@example.com` | `User12345` | `user` |

Seeded access:

| Role | Access |
| --- | --- |
| `admin` | Full admin API access and seeded business permissions. |
| `manager` | `projects:read`, `projects:write`, `reports:read`. |
| `user` | `projects:read`. |

## Setup And Launch

```powershell
python -m pip install -r requirements.txt
python seed.py
python -m app
```

Default base URL:

```text
http://127.0.0.1:5000
```

The default SQLite database is created under Flask's `instance/` directory.

## API Routes

### Health

| Method | URL | Access | Description |
| --- | --- | --- | --- |
| `GET` | `/api/health` | Public | Health check. |

### Authentication And Profile

| Method | URL | Access | Description |
| --- | --- | --- | --- |
| `POST` | `/api/auth/register` | Public | Register with `email`, `password`, `password_repeat`, `first_name`, `last_name`, optional `middle_name`. |
| `POST` | `/api/auth/login` | Public | Login with `email` and `password`; returns bearer token. |
| `POST` | `/api/auth/logout` | Bearer token | Revoke current token. |
| `GET` | `/api/auth/me` | Bearer token | Return current user. |
| `PATCH` | `/api/auth/me` | Bearer token | Update profile fields and/or password. |
| `DELETE` | `/api/auth/me` | Bearer token | Soft-delete current user and revoke sessions. |

### Admin API

Admin routes require the `admin` role.

| Method | URL | Description |
| --- | --- | --- |
| `GET` | `/api/admin/rules` | List roles, resources, permissions, and user-role assignments. |
| `GET` | `/api/admin/users` | List users, including inactive users. |
| `POST` | `/api/admin/roles` | Create role. |
| `PATCH` | `/api/admin/roles/<id>` | Update role. |
| `DELETE` | `/api/admin/roles/<id>` | Delete role except `admin`. |
| `POST` | `/api/admin/resources` | Create resource. |
| `PATCH` | `/api/admin/resources/<id>` | Update resource. |
| `DELETE` | `/api/admin/resources/<id>` | Delete resource. |
| `POST` | `/api/admin/permissions` | Create permission rule. |
| `PATCH` | `/api/admin/permissions/<id>` | Update permission rule. |
| `DELETE` | `/api/admin/permissions/<id>` | Delete permission rule. |
| `POST` | `/api/admin/user-roles` | Assign role to user. |
| `DELETE` | `/api/admin/user-roles/<id>` | Remove role assignment. |

### Mock Business Resources

| Method | URL | Required Access | Description |
| --- | --- | --- | --- |
| `GET` | `/api/projects` | `projects:read` | Return static project data. |
| `POST` | `/api/projects` | `projects:write` | Mock project creation. |
| `GET` | `/api/reports` | `reports:read` | Return static report data. |
| `POST` | `/api/reports` | `reports:write` | Mock report creation. |

## Automated Tests

```powershell
python -m unittest discover -s tests -v
```

## Manual Smoke Test

Start the API:

```powershell
python seed.py
python -m app
```

In another PowerShell terminal:

```powershell
.\scripts\manual_smoke_test.ps1
```

Use a custom base URL when needed:

```powershell
.\scripts\manual_smoke_test.ps1 -BaseUrl "http://127.0.0.1:5000"
```

The smoke test checks registration, login, authenticated profile access, `401`, `403`, admin role assignment, permission changes taking effect immediately, logout token revocation, and soft delete.

## 401 And 403 Behavior

Expected `401 Unauthorized` cases:

- no bearer token;
- malformed or unknown bearer token;
- revoked token;
- expired token;
- token belongs to an inactive user;
- login with wrong credentials or inactive user.

Expected `403 Forbidden` cases:

- authenticated ordinary user calls admin API;
- authenticated user calls a business endpoint without the required permission;
- ordinary user attempts to assign a role, including to themselves.

## Known Limitations

- SQLite is used for local test-assignment simplicity, not production deployment.
- Bearer tokens must be copied by clients; there is no browser cookie flow.
- There is no rate limiting or account lockout.
- There is no email verification or password reset flow.
- There is no pagination on admin list endpoints.
- Mock business resources are static JSON and do not have separate business tables.
- Admin API access is currently tied to the `admin` role.
