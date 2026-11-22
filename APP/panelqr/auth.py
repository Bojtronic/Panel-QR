from __future__ import annotations

from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from .database import fetch_one
from .security import verify_password
from .services import record_audit

bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.full_path))
        return view(**kwargs)

    return wrapped_view


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = fetch_one(
            """
            SELECT id_usuario, password_hash, activo
            FROM usuario
            WHERE lower(email) = lower(%s)
            """,
            (email,),
        )
        authenticated = bool(
            user
            and user["activo"]
            and verify_password(password, user["password_hash"])
        )
        record_audit(
            "INICIO_SESION",
            "usuario",
            email,
            "OK" if authenticated else "DENEGADO",
            user_id=user["id_usuario"] if user else None,
        )
        if authenticated:
            session.clear()
            session["user_id"] = user["id_usuario"]
            session.permanent = True
            return redirect(url_for("main.dashboard"))
        flash("Correo o contraseña incorrectos.", "error")

    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    record_audit("CIERRE_SESION", "usuario", str(g.user["id_usuario"]))
    session.clear()
    return redirect(url_for("auth.login"))
