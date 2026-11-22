from __future__ import annotations

import re

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .auth import login_required
from .database import execute, fetch_all, fetch_one, get_db
from .security import hash_password
from .services import record_audit, require_permission

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/users")
@login_required
def users():
    require_permission("usuario.gestionar")
    rows = fetch_all(
        """
        SELECT u.id_usuario, u.nombre, u.email, u.activo, u.fecha_alta,
               COALESCE(string_agg(r.nombre, ', ' ORDER BY r.nombre), '') AS roles
        FROM usuario u
        LEFT JOIN usuario_rol ur ON ur.id_usuario = u.id_usuario
        LEFT JOIN rol r ON r.id_rol = ur.id_rol
        GROUP BY u.id_usuario
        ORDER BY u.nombre
        """
    )
    return render_template("admin/users.html", users=rows)


@bp.route("/users/new", methods=("GET", "POST"))
@login_required
def new_user():
    require_permission("usuario.gestionar")
    roles = fetch_all("SELECT id_rol, nombre FROM rol ORDER BY nombre")
    groups = fetch_all("SELECT id_grupo, nombre FROM grupo_panel ORDER BY nombre")
    panels = fetch_all(
        "SELECT id_panel, codigo_qr, nombre FROM panel ORDER BY codigo_qr"
    )
    if request.method == "POST":
        name = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role_ids = _selected_ids("roles")
        group_ids = _selected_ids("groups")
        panel_ids = _selected_ids("panels")
        if not name or len(name) > 150 or not _valid_email(email):
            flash("Nombre y correo son obligatorios y deben tener longitud válida.", "error")
        elif len(password) < 12:
            flash("La contraseña inicial debe tener al menos 12 caracteres.", "error")
        elif not role_ids or not _ids_exist("rol", "id_rol", role_ids):
            flash("Selecciona al menos un rol válido.", "error")
        elif not _ids_exist("grupo_panel", "id_grupo", group_ids):
            flash("La selección contiene un grupo inexistente.", "error")
        elif not _ids_exist("panel", "id_panel", panel_ids):
            flash("La selección contiene un panel inexistente.", "error")
        elif not _email_available(email):
            flash("Ya existe una cuenta con ese correo.", "error")
        else:
            user = execute(
                """
                INSERT INTO usuario (nombre, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id_usuario
                """,
                (name, email, hash_password(password)),
            )
            _replace_links("usuario_rol", "id_usuario", user["id_usuario"], "id_rol", role_ids)
            _replace_links(
                "usuario_grupo_panel", "id_usuario", user["id_usuario"], "id_grupo", group_ids
            )
            _replace_links(
                "usuario_panel", "id_usuario", user["id_usuario"], "id_panel", panel_ids
            )
            record_audit("CREAR_USUARIO", "usuario", str(user["id_usuario"]))
            flash("Usuario creado correctamente.", "success")
            return redirect(url_for("admin.users"))
    return render_template(
        "admin/user_form.html",
        user=None,
        roles=roles,
        groups=groups,
        panels=panels,
        selected_roles=[],
        selected_groups=[],
        selected_panels=[],
    )


@bp.route("/users/<int:user_id>", methods=("GET", "POST"))
@login_required
def edit_user(user_id: int):
    require_permission("usuario.gestionar")
    user = fetch_one(
        """
        SELECT id_usuario, nombre, email, activo
        FROM usuario WHERE id_usuario = %s
        """,
        (user_id,),
    )
    if user is None:
        return "Usuario no encontrado.", 404

    roles = fetch_all("SELECT id_rol, nombre FROM rol ORDER BY nombre")
    groups = fetch_all("SELECT id_grupo, nombre FROM grupo_panel ORDER BY nombre")
    panels = fetch_all(
        "SELECT id_panel, codigo_qr, nombre FROM panel ORDER BY codigo_qr"
    )
    if request.method == "POST":
        name = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        active = request.form.get("activo") == "on"
        password = request.form.get("password", "")
        role_ids = _selected_ids("roles")
        group_ids = _selected_ids("groups")
        panel_ids = _selected_ids("panels")
        if not name or len(name) > 150 or not _valid_email(email):
            flash("Nombre y correo son obligatorios y deben tener longitud válida.", "error")
        elif user_id == g.user["id_usuario"] and not active:
            flash("No puedes desactivar tu propia cuenta.", "error")
        elif _removes_last_admin(user_id, role_ids, active):
            flash("Debe quedar al menos una cuenta ADMIN activa.", "error")
        elif not role_ids or not _ids_exist("rol", "id_rol", role_ids):
            flash("Selecciona al menos un rol válido.", "error")
        elif not _email_available(email, except_user_id=user_id):
            flash("Ya existe una cuenta con ese correo.", "error")
        elif password and len(password) < 12:
            flash("La nueva contraseña debe tener al menos 12 caracteres.", "error")
        elif not _ids_exist("grupo_panel", "id_grupo", group_ids):
            flash("La selección contiene un grupo inexistente.", "error")
        elif not _ids_exist("panel", "id_panel", panel_ids):
            flash("La selección contiene un panel inexistente.", "error")
        else:
            if password:
                execute(
                    """
                    UPDATE usuario
                    SET nombre = %s, email = %s, activo = %s, password_hash = %s
                    WHERE id_usuario = %s
                    """,
                    (name, email, active, hash_password(password), user_id),
                )
            else:
                execute(
                    """
                    UPDATE usuario SET nombre = %s, email = %s, activo = %s
                    WHERE id_usuario = %s
                    """,
                    (name, email, active, user_id),
                )
            _replace_links("usuario_rol", "id_usuario", user_id, "id_rol", role_ids)
            _replace_links("usuario_grupo_panel", "id_usuario", user_id, "id_grupo", group_ids)
            _replace_links("usuario_panel", "id_usuario", user_id, "id_panel", panel_ids)
            record_audit("EDITAR_USUARIO", "usuario", str(user_id))
            flash("Cambios guardados.", "success")
            return redirect(url_for("admin.users"))

    selected_roles = [
        row["id_rol"]
        for row in fetch_all(
            "SELECT id_rol FROM usuario_rol WHERE id_usuario = %s", (user_id,)
        )
    ]
    selected_groups = [
        row["id_grupo"]
        for row in fetch_all(
            "SELECT id_grupo FROM usuario_grupo_panel WHERE id_usuario = %s",
            (user_id,),
        )
    ]
    selected_panels = [
        row["id_panel"]
        for row in fetch_all(
            "SELECT id_panel FROM usuario_panel WHERE id_usuario = %s", (user_id,)
        )
    ]
    return render_template(
        "admin/user_form.html",
        user=user,
        roles=roles,
        groups=groups,
        panels=panels,
        selected_roles=selected_roles,
        selected_groups=selected_groups,
        selected_panels=selected_panels,
    )


@bp.route("/permissions", methods=("GET", "POST"))
@login_required
def permissions():
    require_permission("permiso.gestionar")
    roles = fetch_all("SELECT id_rol, nombre FROM rol ORDER BY nombre")
    permissions = fetch_all(
        "SELECT id_permiso, codigo, descripcion FROM permiso ORDER BY codigo"
    )
    if request.method == "POST":
        updates: dict[int, list[int]] = {}
        all_permission_ids = {row["id_permiso"] for row in permissions}
        for role in roles:
            selected = _selected_ids(f"role_{role['id_rol']}")
            if any(permission_id not in all_permission_ids for permission_id in selected):
                flash("La selección contiene permisos inexistentes.", "error")
                return render_template(
                    "admin/permissions.html",
                    roles=roles,
                    permissions=permissions,
                    selected=_role_permissions(roles),
                )
            updates[role["id_rol"]] = selected
        admin_role = next((role for role in roles if role["nombre"] == "ADMIN"), None)
        required_admin_permissions = {
            row["id_permiso"]
            for row in permissions
            if row["codigo"]
            in {
                "usuario.gestionar",
                "permiso.gestionar",
                "panel.gestionar",
                "documento.gestionar",
            }
        }
        if admin_role and not required_admin_permissions.issubset(
            set(updates[admin_role["id_rol"]])
        ):
            flash(
                "ADMIN debe conservar los permisos básicos de administración.",
                "error",
            )
        else:
            connection = get_db()
            with connection.transaction():
                for role_id, permission_ids in updates.items():
                    execute(
                        "DELETE FROM rol_permiso WHERE id_rol = %s", (role_id,)
                    )
                    for permission_id in permission_ids:
                        execute(
                            """
                            INSERT INTO rol_permiso (id_rol, id_permiso)
                            VALUES (%s, %s)
                            """,
                            (role_id, permission_id),
                        )
            record_audit("ACTUALIZAR_PERMISOS", "rol")
            flash("Permisos por rol actualizados.", "success")
            return redirect(url_for("admin.permissions"))

    return render_template(
        "admin/permissions.html",
        roles=roles,
        permissions=permissions,
        selected=_role_permissions(roles),
    )


@bp.get("/audit")
@login_required
def audit():
    require_permission("auditoria.ver")
    events = fetch_all(
        """
        SELECT a.fecha_evento, a.accion, a.entidad, a.id_entidad, a.resultado,
               a.ip, u.email, a.detalle
        FROM auditoria a
        LEFT JOIN usuario u ON u.id_usuario = a.id_usuario
        ORDER BY a.fecha_evento DESC
        LIMIT 200
        """
    )
    return render_template("admin/audit.html", events=events)


def _selected_ids(field: str) -> list[int]:
    result: list[int] = []
    for raw_value in request.form.getlist(field):
        try:
            value = int(raw_value)
        except ValueError:
            continue
        if value > 0 and value not in result:
            result.append(value)
    return result


def _ids_exist(table: str, column: str, ids: list[int]) -> bool:
    if not ids:
        return True
    allowed = {
        ("rol", "id_rol"),
        ("grupo_panel", "id_grupo"),
        ("panel", "id_panel"),
    }
    if (table, column) not in allowed:
        raise ValueError("Entidad no permitida para validación de IDs.")
    rows = fetch_all(
        f"SELECT {column} FROM {table} WHERE {column} = ANY(%s)",
        (ids,),
    )
    return len(rows) == len(ids)


def _email_available(email: str, except_user_id: int | None = None) -> bool:
    if except_user_id is None:
        row = fetch_one(
            "SELECT 1 AS existe FROM usuario WHERE lower(email) = lower(%s)",
            (email,),
        )
    else:
        row = fetch_one(
            """
            SELECT 1 AS existe FROM usuario
            WHERE lower(email) = lower(%s) AND id_usuario <> %s
            """,
            (email, except_user_id),
        )
    return row is None


def _valid_email(email: str) -> bool:
    return len(email) <= 255 and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) is not None


def _removes_last_admin(user_id: int, role_ids: list[int], active: bool) -> bool:
    admin = fetch_one("SELECT id_rol FROM rol WHERE nombre = 'ADMIN'")
    if admin is None:
        return False
    current_admin = fetch_one(
        """
        SELECT 1 AS is_admin FROM usuario_rol
        WHERE id_usuario = %s AND id_rol = %s
        """,
        (user_id, admin["id_rol"]),
    )
    if current_admin is None:
        return False
    if active and admin["id_rol"] in role_ids:
        return False
    other_admin = fetch_one(
        """
        SELECT 1 AS tiene_registro
        FROM usuario u
        JOIN usuario_rol ur ON ur.id_usuario = u.id_usuario
        WHERE u.activo = TRUE AND ur.id_rol = %s AND u.id_usuario <> %s
        LIMIT 1
        """,
        (admin["id_rol"], user_id),
    )
    return other_admin is None


def _replace_links(
    table: str, owner_column: str, owner_id: int, link_column: str, ids: list[int]
) -> None:
    allowed = {
        ("usuario_rol", "id_usuario", "id_rol"),
        ("usuario_grupo_panel", "id_usuario", "id_grupo"),
        ("usuario_panel", "id_usuario", "id_panel"),
    }
    if (table, owner_column, link_column) not in allowed:
        raise ValueError("Relación no permitida.")
    execute(f"DELETE FROM {table} WHERE {owner_column} = %s", (owner_id,))
    for linked_id in ids:
        execute(
            f"INSERT INTO {table} ({owner_column}, {link_column}) VALUES (%s, %s)",
            (owner_id, linked_id),
        )


def _role_permissions(roles: list[dict]) -> dict[int, set[int]]:
    result = {role["id_rol"]: set() for role in roles}
    for row in fetch_all("SELECT id_rol, id_permiso FROM rol_permiso"):
        if row["id_rol"] in result:
            result[row["id_rol"]].add(row["id_permiso"])
    return result
