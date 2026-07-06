from __future__ import annotations

from flask import Blueprint

from app.authz import require_permission

business_bp = Blueprint("business", __name__)

PROJECTS = [
    {"id": 1, "name": "Payroll migration", "status": "active"},
    {"id": 2, "name": "Internal CRM", "status": "planning"},
]

REPORTS = [
    {"id": 1, "title": "Quarter revenue", "period": "2026-Q2"},
    {"id": 2, "title": "Security audit", "period": "2026-Q2"},
]


@business_bp.get("/projects")
@require_permission("projects", "read")
def list_projects():
    return {"items": PROJECTS}


@business_bp.post("/projects")
@require_permission("projects", "write")
def create_project_mock():
    return {"status": "accepted", "message": "Project creation is mocked"}, 201


@business_bp.get("/reports")
@require_permission("reports", "read")
def list_reports():
    return {"items": REPORTS}


@business_bp.post("/reports")
@require_permission("reports", "write")
def create_report_mock():
    return {"status": "accepted", "message": "Report creation is mocked"}, 201
