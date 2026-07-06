import unittest

from app import create_app
from app.db import db
from app.models import Resource, Role, SessionToken, User, UserRole
from seed import seed


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            }
        )
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        seed()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, email, password):
        response = self.client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return response.get_json()["token"]

    def auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def admin_token(self):
        return self.login("admin@example.com", "Admin12345")

    def role_id(self, code):
        role = Role.query.filter_by(code=code).one()
        return role.id

    def user_id(self, email):
        user = User.query.filter_by(email=email).one()
        return user.id

    def resource_id(self, code):
        resource = Resource.query.filter_by(code=code).one()
        return resource.id

    def valid_registration_payload(self, email="new@example.com"):
        return {
            "email": email,
            "password": "Password123",
            "password_repeat": "Password123",
            "first_name": "New",
            "last_name": "Person",
            "middle_name": "Test",
        }

    def test_register_login_update_logout(self):
        response = self.client.post(
            "/api/auth/register", json=self.valid_registration_payload()
        )
        self.assertEqual(response.status_code, 201)

        token = self.login("new@example.com", "Password123")
        response = self.client.patch(
            "/api/auth/me",
            json={"first_name": "Updated"},
            headers=self.auth(token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user"]["first_name"], "Updated")

        response = self.client.post("/api/auth/logout", headers=self.auth(token))
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/api/auth/me", headers=self.auth(token))
        self.assertEqual(response.status_code, 401)

    def test_registration_rejects_duplicate_email(self):
        response = self.client.post(
            "/api/auth/register",
            json=self.valid_registration_payload(email="user@example.com"),
        )
        self.assertEqual(response.status_code, 400)

    def test_registration_rejects_mismatched_passwords(self):
        payload = self.valid_registration_payload()
        payload["password_repeat"] = "Different123"
        response = self.client.post("/api/auth/register", json=payload)
        self.assertEqual(response.status_code, 400)

    def test_registration_rejects_missing_required_fields(self):
        for field in ["email", "password", "password_repeat", "first_name", "last_name"]:
            with self.subTest(field=field):
                payload = self.valid_registration_payload(email=f"{field}@example.com")
                payload.pop(field)
                response = self.client.post("/api/auth/register", json=payload)
                self.assertEqual(response.status_code, 400)

    def test_login_rejects_wrong_password(self):
        response = self.client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "WrongPassword123"},
        )
        self.assertEqual(response.status_code, 401)

    def test_inactive_user_cannot_login(self):
        user = User.query.filter_by(email="user@example.com").one()
        user.is_active = False
        db.session.commit()

        response = self.client.post(
            "/api/auth/login", json={"email": "user@example.com", "password": "User12345"}
        )
        self.assertEqual(response.status_code, 401)

    def test_invalid_bearer_token_returns_401(self):
        response = self.client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid-token"}
        )
        self.assertEqual(response.status_code, 401)

    def test_soft_delete_blocks_next_login(self):
        token = self.login("user@example.com", "User12345")
        response = self.client.delete("/api/auth/me", headers=self.auth(token))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/auth/login", json={"email": "user@example.com", "password": "User12345"}
        )
        self.assertEqual(response.status_code, 401)

    def test_soft_deleted_user_record_remains_in_database(self):
        token = self.login("user@example.com", "User12345")
        response = self.client.delete("/api/auth/me", headers=self.auth(token))
        self.assertEqual(response.status_code, 200)

        user = User.query.filter_by(email="user@example.com").one()
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.deleted_at)

    def test_revoked_token_cannot_be_reused(self):
        token = self.login("user@example.com", "User12345")
        response = self.client.post("/api/auth/logout", headers=self.auth(token))
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/auth/me", headers=self.auth(token))
        self.assertEqual(response.status_code, 401)
        session = SessionToken.query.first()
        self.assertIsNotNone(session.revoked_at)

    def test_business_access_401_403_and_success(self):
        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 401)

        user_token = self.login("user@example.com", "User12345")
        response = self.client.get("/api/projects", headers=self.auth(user_token))
        self.assertEqual(response.status_code, 200)

        response = self.client.post("/api/projects", headers=self.auth(user_token))
        self.assertEqual(response.status_code, 403)

        manager_token = self.login("manager@example.com", "Manager12345")
        response = self.client.post("/api/projects", headers=self.auth(manager_token))
        self.assertEqual(response.status_code, 201)

    def test_ordinary_user_cannot_access_admin_api(self):
        user_token = self.login("user@example.com", "User12345")
        response = self.client.get("/api/admin/rules", headers=self.auth(user_token))
        self.assertEqual(response.status_code, 403)

    def test_ordinary_user_cannot_assign_role_to_themselves(self):
        user_token = self.login("user@example.com", "User12345")
        response = self.client.post(
            "/api/admin/user-roles",
            json={
                "user_id": self.user_id("user@example.com"),
                "role_id": self.role_id("manager"),
            },
            headers=self.auth(user_token),
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_change_access_rules(self):
        admin_token = self.admin_token()
        response = self.client.get("/api/admin/rules", headers=self.auth(admin_token))
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        user_role = next(role for role in payload["roles"] if role["code"] == "user")
        reports = next(
            resource for resource in payload["resources"] if resource["code"] == "reports"
        )

        response = self.client.post(
            "/api/admin/permissions",
            json={
                "role_id": str(user_role["id"]),
                "resource_id": str(reports["id"]),
                "action": "read",
                "is_allowed": True,
            },
            headers=self.auth(admin_token),
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))

        user_token = self.login("user@example.com", "User12345")
        response = self.client.get("/api/reports", headers=self.auth(user_token))
        self.assertEqual(response.status_code, 200)

    def test_duplicate_user_role_assignment_is_rejected_safely(self):
        admin_token = self.admin_token()
        user_id = self.user_id("user@example.com")
        role_id = self.role_id("user")

        response = self.client.post(
            "/api/admin/user-roles",
            json={"user_id": user_id, "role_id": role_id},
            headers=self.auth(admin_token),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            UserRole.query.filter_by(user_id=user_id, role_id=role_id).count(), 1
        )

    def test_invalid_role_resource_permission_and_user_ids_are_rejected(self):
        admin_token = self.admin_token()
        headers = self.auth(admin_token)
        valid_user_id = self.user_id("user@example.com")
        valid_role_id = self.role_id("user")
        valid_resource_id = self.resource_id("projects")

        checks = [
            self.client.patch("/api/admin/roles/9999", json={"name": "Missing"}, headers=headers),
            self.client.delete("/api/admin/roles/9999", headers=headers),
            self.client.patch(
                "/api/admin/resources/9999", json={"name": "Missing"}, headers=headers
            ),
            self.client.delete("/api/admin/resources/9999", headers=headers),
            self.client.post(
                "/api/admin/permissions",
                json={"role_id": 9999, "resource_id": valid_resource_id, "action": "read"},
                headers=headers,
            ),
            self.client.post(
                "/api/admin/permissions",
                json={"role_id": valid_role_id, "resource_id": 9999, "action": "read"},
                headers=headers,
            ),
            self.client.patch(
                "/api/admin/permissions/9999", json={"action": "read"}, headers=headers
            ),
            self.client.delete("/api/admin/permissions/9999", headers=headers),
            self.client.post(
                "/api/admin/user-roles",
                json={"user_id": 9999, "role_id": valid_role_id},
                headers=headers,
            ),
            self.client.post(
                "/api/admin/user-roles",
                json={"user_id": valid_user_id, "role_id": 9999},
                headers=headers,
            ),
            self.client.delete("/api/admin/user-roles/9999", headers=headers),
        ]

        for response in checks:
            self.assertEqual(response.status_code, 400, response.get_data(as_text=True))

        response = self.client.post(
            "/api/admin/permissions",
            json={"role_id": "not-an-id", "resource_id": valid_resource_id, "action": "read"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_removing_role_immediately_removes_access(self):
        manager_token = self.login("manager@example.com", "Manager12345")
        response = self.client.post("/api/projects", headers=self.auth(manager_token))
        self.assertEqual(response.status_code, 201)

        user_role = (
            UserRole.query.join(User)
            .join(Role)
            .filter(User.email == "manager@example.com", Role.code == "manager")
            .one()
        )
        admin_token = self.admin_token()
        response = self.client.delete(
            f"/api/admin/user-roles/{user_role.id}", headers=self.auth(admin_token)
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post("/api/projects", headers=self.auth(manager_token))
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
