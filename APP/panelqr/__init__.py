from __future__ import annotations

import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, Response, current_app, g, redirect, render_template, session, url_for
from flask_wtf.csrf import CSRFProtect

from .database import fetch_all, fetch_one, init_app

csrf = CSRFProtect()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE_URL=os.environ.get(
            "DATABASE_URL", "postgresql://localhost/panel_qr"
        ),
        UPLOAD_FOLDER=os.environ.get(
            "UPLOAD_FOLDER", str(Path(app.root_path).parent / "storage")
        ),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower()
        == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
        WTF_CSRF_TIME_LIMIT=3600,
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    csrf.init_app(app)
    init_app(app)

    from .admin import bp as admin_bp
    from .auth import bp as auth_bp
    from .main import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    @app.before_request
    def load_logged_in_user() -> None:
        user_id = session.get("user_id")
        g.user = None
        if user_id is None:
            return

        user = fetch_one(
            """
            SELECT id_usuario, nombre, email, activo
            FROM usuario
            WHERE id_usuario = %s
            """,
            (user_id,),
        )
        if user is None or not user["activo"]:
            session.clear()
            return

        roles = fetch_all(
            """
            SELECT r.nombre
            FROM rol r
            JOIN usuario_rol ur ON ur.id_rol = r.id_rol
            WHERE ur.id_usuario = %s
            ORDER BY r.nombre
            """,
            (user_id,),
        )
        permissions = fetch_all(
            """
            SELECT DISTINCT p.codigo
            FROM usuario_rol ur
            JOIN rol_permiso rp ON rp.id_rol = ur.id_rol
            JOIN permiso p ON p.id_permiso = rp.id_permiso
            WHERE ur.id_usuario = %s
            ORDER BY p.codigo
            """,
            (user_id,),
        )
        g.user = {
            **user,
            "roles": [role["nombre"] for role in roles],
            "permissions": {permission["codigo"] for permission in permissions},
        }

    @app.context_processor
    def inject_template_values() -> dict:
        user = getattr(g, "user", None)
        return {
            "current_user": user,
            "permissions": lambda: user["permissions"] if user else set(),
        }

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; object-src 'self'; base-uri 'self'; "
            "form-action 'self'; frame-ancestors 'self'",
        )
        return response

    @app.errorhandler(413)
    def file_too_large(error: Exception):
        current_app.logger.info("Rejected upload above the configured size limit: %s", error)
        return render_template(
            "error.html",
            title="Archivo demasiado grande",
            message="El tamaño máximo permitido por archivo es 20 MB.",
        ), 413

    @app.get("/")
    def index():
        if getattr(g, "user", None):
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("auth.login"))

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
