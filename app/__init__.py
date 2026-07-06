from __future__ import annotations

from flask import Flask, jsonify

from app.db import db
from app.routes.admin import admin_bp
from app.routes.auth import auth_bp
from app.routes.business import business_bp


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite:///custom_auth.sqlite3",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)

    db.init_app(app)

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(business_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "bad_request", "message": str(error.description)}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "unauthorized", "message": str(error.description)}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"error": "forbidden", "message": str(error.description)}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "not_found", "message": "Resource not found"}), 404

    return app
