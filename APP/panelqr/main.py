from __future__ import annotations

import re
from io import BytesIO

import qrcode
from flask import (
    Blueprint,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from .auth import login_required
from .database import execute, fetch_all, fetch_one
from .services import (
    INLINE_MIME_TYPES,
    can_access_panel,
    has_permission,
    register_document_version,
    record_audit,
    require_permission,
    save_uploaded_document,
    storage_path,
)

bp = Blueprint("main", __name__)


@bp.get("/dashboard")
@login_required
def dashboard():
    stats = fetch_one(
        """
        SELECT
            (SELECT count(*) FROM panel) AS paneles,
            (SELECT count(*) FROM panel WHERE estado = 'MANTENIMIENTO') AS mantenimiento,
            (SELECT count(*) FROM usuario WHERE activo) AS usuarios_activos,
            (SELECT count(*) FROM auditoria
             WHERE resultado = 'DENEGADO'
               AND fecha_evento >= CURRENT_TIMESTAMP - INTERVAL '7 days') AS denegados
        """
    )
    if has_permission("auditoria.ver"):
        activity = fetch_all(
            """
            SELECT a.fecha_evento, a.accion, a.entidad, a.id_entidad,
                   a.resultado, u.email
            FROM auditoria a
            LEFT JOIN usuario u ON u.id_usuario = a.id_usuario
            ORDER BY a.fecha_evento DESC
            LIMIT 10
            """
        )
    else:
        activity = []
    return render_template("dashboard/index.html", stats=stats, activity=activity)


@bp.get("/panels")
@login_required
def panel_list():
    require_permission("panel.ver")
    query = request.args.get("q", "").strip()
    panels = fetch_all(
        """
        SELECT p.id_panel, p.codigo_qr, p.nombre, p.ubicacion, p.estado,
               gp.nombre AS grupo
        FROM panel p
        LEFT JOIN grupo_panel gp ON gp.id_grupo = p.id_grupo
        WHERE (p.codigo_qr ILIKE %s OR p.nombre ILIKE %s OR COALESCE(p.ubicacion, '') ILIKE %s)
          AND (
            EXISTS (
                SELECT 1 FROM usuario_rol ur
                JOIN rol_permiso rp ON rp.id_rol = ur.id_rol
                JOIN permiso pe ON pe.id_permiso = rp.id_permiso
                WHERE ur.id_usuario = %s AND pe.codigo = 'panel.ver_todos'
            )
            OR EXISTS (
                SELECT 1 FROM usuario_panel up
                WHERE up.id_usuario = %s AND up.id_panel = p.id_panel
            )
            OR EXISTS (
                SELECT 1 FROM usuario_grupo_panel ug
                WHERE ug.id_usuario = %s AND ug.id_grupo = p.id_grupo
            )
          )
        ORDER BY p.codigo_qr
        """,
        (
            f"%{query}%",
            f"%{query}%",
            f"%{query}%",
            g.user["id_usuario"],
            g.user["id_usuario"],
            g.user["id_usuario"],
        ),
    )
    groups = fetch_all(
        "SELECT id_grupo, nombre FROM grupo_panel ORDER BY nombre"
    ) if has_permission("panel.gestionar") else []
    return render_template(
        "panels/list.html",
        panels=panels,
        query=query,
        groups=groups,
        can_manage=has_permission("panel.gestionar"),
    )


@bp.post("/panels")
@login_required
def create_panel():
    require_permission("panel.gestionar")
    code = request.form.get("codigo_qr", "").strip()
    name = request.form.get("nombre", "").strip()
    location = request.form.get("ubicacion", "").strip()
    raw_group_id = request.form.get("id_grupo", "").strip()
    try:
        group_id = int(raw_group_id) if raw_group_id else None
    except ValueError:
        group_id = -1
    if not code or not name:
        flash("El código y el nombre del panel son obligatorios.", "error")
        return redirect(url_for("main.panel_list"))
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", code):
        flash("El código solo puede contener letras, números, punto, guion y guion bajo.", "error")
        return redirect(url_for("main.panel_list"))
    if len(code) > 128 or len(name) > 150 or len(location) > 255:
        flash("Uno o más campos superan la longitud permitida.", "error")
        return redirect(url_for("main.panel_list"))
    if group_id and not fetch_one(
        "SELECT id_grupo FROM grupo_panel WHERE id_grupo = %s",
        (group_id,),
    ):
        flash("El grupo seleccionado no existe.", "error")
        return redirect(url_for("main.panel_list"))

    panel = execute(
        """
        INSERT INTO panel (codigo_qr, nombre, ubicacion, id_grupo)
        VALUES (%s, %s, %s, %s)
        RETURNING id_panel, codigo_qr
        """,
        (code, name, location or None, group_id),
    )
    record_audit("CREAR_PANEL", "panel", code)
    flash("Panel registrado correctamente.", "success")
    return redirect(url_for("main.panel_detail", code=panel["codigo_qr"]))


@bp.post("/panel/<string:code>/edit")
@login_required
def edit_panel(code: str):
    require_permission("panel.gestionar")
    panel = fetch_one(
        "SELECT id_panel FROM panel WHERE codigo_qr = %s",
        (code,),
    )
    if panel is None:
        abort(404)
    name = request.form.get("nombre", "").strip()
    location = request.form.get("ubicacion", "").strip()
    raw_group_id = request.form.get("id_grupo", "").strip()
    status = request.form.get("estado", "")
    try:
        group_id = int(raw_group_id) if raw_group_id else None
    except ValueError:
        group_id = -1
    if not name or len(name) > 150 or len(location) > 255:
        flash("El nombre es obligatorio y los campos deben tener longitud válida.", "error")
    elif status not in {"ACTIVO", "INACTIVO", "MANTENIMIENTO"}:
        flash("El estado seleccionado no es válido.", "error")
    elif group_id is not None and not fetch_one(
        "SELECT id_grupo FROM grupo_panel WHERE id_grupo = %s",
        (group_id,),
    ):
        flash("El grupo seleccionado no existe.", "error")
    else:
        execute(
            """
            UPDATE panel
            SET nombre = %s, ubicacion = %s, id_grupo = %s, estado = %s
            WHERE id_panel = %s
            """,
            (name, location or None, group_id, status, panel["id_panel"]),
        )
        record_audit("EDITAR_PANEL", "panel", code)
        flash("Información del panel actualizada.", "success")
    return redirect(url_for("main.panel_detail", code=code))


@bp.get("/panel/<string:code>")
@login_required
def panel_detail(code: str):
    require_permission("panel.ver")
    panel = fetch_one(
        """
        SELECT p.*, gp.nombre AS grupo
        FROM panel p
        LEFT JOIN grupo_panel gp ON gp.id_grupo = p.id_grupo
        WHERE p.codigo_qr = %s
        """,
        (code,),
    )
    if panel is None:
        abort(404)
    if not can_access_panel(panel["id_panel"]):
        record_audit("CONSULTA_PANEL", "panel", code, "DENEGADO")
        abort(404)
    record_audit("CONSULTA_PANEL", "panel", code)
    documents = fetch_all(
        """
        SELECT d.id_documento, d.titulo, d.descripcion, td.nombre AS tipo,
               v.numero_version, v.id_version, v.nombre_archivo, v.mime_type,
               v.fecha_subida
        FROM documento d
        JOIN tipo_documento td ON td.id_tipo_documento = d.id_tipo_documento
        LEFT JOIN documento_version v
          ON v.id_documento = d.id_documento AND v.es_actual = TRUE
        WHERE d.id_panel = %s AND d.activo = TRUE
        ORDER BY d.titulo
        """,
        (panel["id_panel"],),
    ) if has_permission("documento.ver") else []
    return render_template(
        "panels/detail.html",
        panel=panel,
        documents=documents,
        can_manage=has_permission("documento.gestionar"),
        can_edit=has_permission("panel.gestionar"),
        groups=fetch_all("SELECT id_grupo, nombre FROM grupo_panel ORDER BY nombre")
        if has_permission("panel.gestionar")
        else [],
    )


@bp.get("/panel/<string:code>/qr")
@login_required
def panel_qr(code: str):
    require_permission("panel.ver")
    panel = fetch_one(
        "SELECT id_panel, codigo_qr FROM panel WHERE codigo_qr = %s",
        (code,),
    )
    if panel is None:
        abort(404)
    if not can_access_panel(panel["id_panel"]):
        record_audit("CONSULTA_QR", "panel", code, "DENEGADO")
        abort(404)
    target = url_for("main.panel_detail", code=code, _external=True)
    image = qrcode.make(target)
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return send_file(output, mimetype="image/png", max_age=0)


@bp.route("/panel/<string:code>/documents/new", methods=("GET", "POST"))
@login_required
def upload_document(code: str):
    require_permission("documento.gestionar")
    panel = fetch_one(
        "SELECT id_panel, codigo_qr FROM panel WHERE codigo_qr = %s",
        (code,),
    )
    if panel is None:
        abort(404)
    if request.method == "POST":
        title = request.form.get("titulo", "").strip()
        description = request.form.get("descripcion", "").strip()
        try:
            document_type = int(request.form.get("id_tipo_documento", ""))
        except ValueError:
            document_type = 0
        version = request.form.get("numero_version", "").strip()
        upload = request.files.get("archivo")
        if not title or not version or upload is None or not upload.filename:
            flash("Completa el título, la versión y selecciona un archivo.", "error")
        elif len(title) > 200 or len(version) > 20:
            flash("El título o la versión superan la longitud permitida.", "error")
        elif not fetch_one(
            "SELECT id_tipo_documento FROM tipo_documento WHERE id_tipo_documento = %s",
            (document_type,),
        ):
            flash("El tipo de documento seleccionado no existe.", "error")
        else:
            try:
                relative_path, filename, mime_type, size, digest = (
                    save_uploaded_document(upload)
                )
            except ValueError as error:
                flash(str(error), "error")
            else:
                try:
                    register_document_version(
                        panel_id=panel["id_panel"],
                        title=title,
                        description=description or None,
                        document_type_id=document_type,
                        version=version,
                        relative_path=relative_path,
                        filename=filename,
                        mime_type=mime_type,
                        size=size,
                        digest=digest,
                        notes=request.form.get("notas", "").strip() or None,
                    )
                except ValueError as error:
                    flash(str(error), "error")
                except LookupError as error:
                    flash(str(error), "error")
                else:
                    flash("Documento y versión registrados.", "success")
                    return redirect(url_for("main.panel_detail", code=code))

    types = fetch_all(
        "SELECT id_tipo_documento, nombre FROM tipo_documento ORDER BY nombre"
    )
    return render_template("documents/upload.html", panel=panel, types=types)


@bp.get("/documents/<int:document_id>")
@login_required
def document_history(document_id: int):
    document = fetch_one(
        """
        SELECT d.id_documento, d.id_panel, d.titulo, d.descripcion,
               p.codigo_qr, p.nombre AS panel
        FROM documento d JOIN panel p ON p.id_panel = d.id_panel
        WHERE d.id_documento = %s AND d.activo = TRUE
        """,
        (document_id,),
    )
    if document is None:
        abort(404)
    if not has_permission("documento.ver") or not can_access_panel(document["id_panel"]):
        record_audit("CONSULTA_DOCUMENTO", "documento", str(document_id), "DENEGADO")
        abort(404)
    versions = fetch_all(
        """
        SELECT id_version, numero_version, nombre_archivo, mime_type,
               fecha_subida, notas, es_actual
        FROM documento_version
        WHERE id_documento = %s
        ORDER BY fecha_subida DESC, id_version DESC
        """,
        (document_id,),
    )
    return render_template(
        "documents/history.html", document=document, versions=versions
    )


@bp.get("/documents/version/<int:version_id>")
@login_required
def serve_document(version_id: int):
    version = fetch_one(
        """
        SELECT v.*, d.id_panel, d.id_documento, d.titulo
        FROM documento_version v
        JOIN documento d ON d.id_documento = v.id_documento
        WHERE v.id_version = %s AND d.activo = TRUE
        """,
        (version_id,),
    )
    if version is None:
        abort(404)
    if not has_permission("documento.ver") or not can_access_panel(version["id_panel"]):
        record_audit(
            "ABRIR_DOCUMENTO",
            "documento",
            str(version["id_documento"]),
            "DENEGADO",
        )
        abort(404)
    if version["mime_type"] not in INLINE_MIME_TYPES:
        abort(415)
    file_path = storage_path(version["ruta_externa"])
    if not file_path.is_file():
        abort(404)
    record_audit(
        "ABRIR_DOCUMENTO",
        "documento",
        str(version["id_documento"]),
        detail=f"Versión {version['numero_version']}",
    )
    response = send_file(
        file_path,
        mimetype=version["mime_type"],
        as_attachment=False,
        download_name=version["nombre_archivo"],
        conditional=True,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'"
    return response
