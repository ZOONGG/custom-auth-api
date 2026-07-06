# Original Employer Assignment

Implement a backend API with custom authentication and role-based access control.

Functional requirements:

- Provide user registration.
- Provide user login by email and password.
- Provide logout.
- Provide an authenticated user profile endpoint.
- Allow an authenticated user to update profile data.
- Soft-delete users instead of physically deleting user records.
- Store passwords securely; do not store plaintext passwords.
- Implement a custom RBAC authorization model.
- Support roles, protected resources, permissions, user-role assignments, and role-permission rules.
- Protect administrative access-control endpoints so ordinary users cannot manage roles or permissions.
- Protect mock business resources with RBAC checks.
- Return `401 Unauthorized` when a user is not authenticated or the token is invalid.
- Return `403 Forbidden` when a user is authenticated but does not have the required permission.
- Include seed/demo data for checking the API.
- Include instructions for setup, launch, tests, and manual verification.

Frontend, mobile application, and executable desktop application are not required.
