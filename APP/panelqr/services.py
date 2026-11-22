from __future__ import annotations

import hashlib
import secrets
from pathlib import Path

import psycopg
from flask import abort, current_app, g, request
from werkzeug.utils import secure_filename

from .database import execute, fetch_one, get_db

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
INLINE_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
}


def has_permission(permission: str) -> bool:
    if g.user is None:
        return False
    row = fetch_one(
        """
        SELECT EXISTS (
            SELECT 1
            FROM usuario_rol ur
            JOIN rol_permiso rp ON rp.id_rol = ur.id_rol
            JOIN permiso p ON p.id_permiso = rp.id_permiso
            WHERE ur.id_usuario = %s AND p.codigo = %s
        ) AS permitido
        """,
        (g.user["id_usuario"], permission),
    )
    return bool(row and row["permitido"])


def require_permission(permission: str) -> None:
    if not has_permission(permission):
        abort(403)


def can_access_panel(panel_id: int) -> bool:
    if g.user is None:
        return False
    row = fetch_one(
        """
        SELECT EXISTS (
            SELECT 1
            FROM usuario_rol ur
            JOIN rol_permiso rp ON rp.id_rol = ur.id_rol
            JOIN permiso p ON p.id_permiso = rp.id_permiso
            WHERE ur.id_usuario = %s AND p.codigo = 'panel.ver_todos'
        ) OR EXISTS (
            SELECT 1 FROM usuario_panel up
            WHERE up.id_usuario = %s AND up.id_panel = %s
        ) OR EXISTS (
            SELECT 1
            FROM usuario_grupo_panel ug
            JOIN panel pa ON pa.id_grupo = ug.id_grupo
            WHERE ug.id_usuario = %s AND pa.id_panel = %s
        ) AS permitido
        """,
        (
            g.user["id_usuario"],
            g.user["id_usuario"],
            panel_id,
            g.user["id_usuario"],
            panel_id,
        ),
    )
    return bool(row and row["permitido"])


def record_audit(
    action: str,
    entity: str | None = None,
    entity_id: str | None = None,
    result: str = "OK",
    detail: str | None = None,
    user_id: int | None = None,
) -> None:
    if user_id is None and g.get("user"):
        user_id = g.user["id_usuario"]
    execute(
        """
        INSERT INTO auditoria (
            id_usuario, accion, entidad, id_entidad, resultado,
            ip, user_agent, detalle
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            action[:80],
            entity[:50] if entity else None,
            entity_id[:100] if entity_id else None,
            result,
            request.remote_addr,
            request.user_agent.string[:255],
            detail,
        ),
    )


def storage_path(relative_path: str) -> Path:
    if relative_path.startswith("demo/"):
        root = (Path(current_app.root_path).parent / "storage" / "demo").resolve()
        relative_path = relative_path.removeprefix("demo/")
    else:
        root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    path = (root / relative_path).resolve()
    if root not in path.parents:
        abort(404)
    return path


def save_uploaded_document(upload) -> tuple[str, str, str, int, str]:
    filename = secure_filename(upload.filename or "")
    extension = Path(filename).suffix.lower()
    if not filename or extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Solo se permiten archivos PDF, PNG y JPEG.")

    mime_type = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }[extension]
    relative_path = f"uploads/{secrets.token_urlsafe(24)}{extension}"
    destination = storage_path(relative_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    upload.save(destination)
    size = destination.stat().st_size
    if size == 0:
        destination.unlink()
        raise ValueError("El archivo está vacío.")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return relative_path, filename, mime_type, size, digest


def register_document_version(
    *,
    panel_id: int,
    title: str,
    description: str | None,
    document_type_id: int,
    version: str,
    relative_path: str,
    filename: str,
    mime_type: str,
    size: int,
    digest: str,
    notes: str | None,
) -> None:
    try:
        with get_db().transaction():
            repository = fetch_one(
                """
                SELECT id_repositorio FROM repositorio
                WHERE tipo = 'LOCAL' AND activo = TRUE
                ORDER BY id_repositorio LIMIT 1
                """
            )
            if repository is None:
                raise LookupError("No hay un repositorio local activo.")

            document = fetch_one(
                """
                SELECT id_documento, id_tipo_documento
                FROM documento
                WHERE id_panel = %s AND titulo = %s AND activo = TRUE
                """,
                (panel_id, title),
            )
            if document is None:
                document = execute(
                    """
                    INSERT INTO documento (
                        id_panel, id_tipo_documento, titulo, descripcion,
                        id_usuario_creador
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id_documento
                    """,
                    (
                        panel_id,
                        document_type_id,
                        title,
                        description,
                        g.user["id_usuario"],
                    ),
                )
            elif document["id_tipo_documento"] != document_type_id:
                raise ValueError(
                    "El tipo de un documento existente no se puede cambiar al subir una versión."
                )

            execute(
                """
                UPDATE documento_version SET es_actual = FALSE
                WHERE id_documento = %s
                """,
                (document["id_documento"],),
            )
            execute(
                """
                INSERT INTO documento_version (
                    id_documento, numero_version, id_repositorio,
                    ruta_externa, nombre_archivo, mime_type, tamano_bytes,
                    hash_sha256, id_usuario_subida, notas, es_actual
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                """,
                (
                    document["id_documento"],
                    version,
                    repository["id_repositorio"],
                    relative_path,
                    filename,
                    mime_type,
                    size,
                    digest,
                    g.user["id_usuario"],
                    notes,
                ),
            )
            record_audit(
                "SUBIR_DOCUMENTO",
                "documento",
                str(document["id_documento"]),
                detail=f"Panel {panel_id}; versión {version}",
            )
            return None
    except psycopg.errors.UniqueViolation as error:
        storage_path(relative_path).unlink(missing_ok=True)
        raise ValueError(
            "Ese número de versión ya existe para el documento."
        ) from error
    except ValueError:
        storage_path(relative_path).unlink(missing_ok=True)
        raise
    except (LookupError, psycopg.Error):
        storage_path(relative_path).unlink(missing_ok=True)
        raise
