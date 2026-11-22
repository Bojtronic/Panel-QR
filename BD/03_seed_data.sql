-- Acceso de prueba para las tres cuentas: PanelQR2026!
INSERT INTO usuario (nombre, email, password_hash) VALUES
    ('Administradora Demo', 'admin@panelqr.local',
     'pbkdf2_sha256$600000$cGFuZWxxci1kZW1vLTIwMjY$nwVnTfWyyxaQMHp-HWCyaNLrpLIbqguKENJuFbndVtw'),
    ('Técnico Uno', 'tecnico1@panelqr.local',
     'pbkdf2_sha256$600000$cGFuZWxxci1kZW1vLTIwMjY$nwVnTfWyyxaQMHp-HWCyaNLrpLIbqguKENJuFbndVtw'),
    ('Técnica Dos', 'tecnico2@panelqr.local',
     'pbkdf2_sha256$600000$cGFuZWxxci1kZW1vLTIwMjY$nwVnTfWyyxaQMHp-HWCyaNLrpLIbqguKENJuFbndVtw');

INSERT INTO rol (nombre, descripcion) VALUES
    ('ADMIN', 'Administración completa del sistema'),
    ('TECNICO', 'Consulta de paneles asignados y sus documentos');

INSERT INTO permiso (codigo, descripcion) VALUES
    ('panel.ver', 'Consultar paneles autorizados'),
    ('panel.ver_todos', 'Consultar todos los paneles'),
    ('panel.gestionar', 'Crear y editar paneles'),
    ('documento.ver', 'Consultar documentos autorizados'),
    ('documento.gestionar', 'Subir nuevas versiones de documentos'),
    ('usuario.gestionar', 'Administrar usuarios, roles y asignaciones'),
    ('permiso.gestionar', 'Administrar permisos por rol'),
    ('auditoria.ver', 'Consultar el registro de auditoría');

INSERT INTO grupo_panel (nombre, descripcion) VALUES
    ('Edificio principal', 'Paneles del edificio principal'),
    ('Taller', 'Paneles del área de taller');

INSERT INTO panel (id_grupo, codigo_qr, nombre, ubicacion, estado) VALUES
    ((SELECT id_grupo FROM grupo_panel WHERE nombre = 'Edificio principal'),
     'P-001', 'Panel principal de distribución', 'Planta baja', 'ACTIVO'),
    ((SELECT id_grupo FROM grupo_panel WHERE nombre = 'Taller'),
     'P-002', 'Panel de iluminación', 'Taller, zona norte', 'MANTENIMIENTO'),
    ((SELECT id_grupo FROM grupo_panel WHERE nombre = 'Edificio principal'),
     'P-003', 'Panel de tomacorrientes', 'Segundo nivel', 'ACTIVO');

INSERT INTO usuario_rol (id_usuario, id_rol)
SELECT u.id_usuario, r.id_rol
FROM usuario u CROSS JOIN rol r
WHERE (u.email = 'admin@panelqr.local' AND r.nombre = 'ADMIN')
   OR (u.email IN ('tecnico1@panelqr.local', 'tecnico2@panelqr.local') AND r.nombre = 'TECNICO');

INSERT INTO rol_permiso (id_rol, id_permiso)
SELECT r.id_rol, p.id_permiso
FROM rol r CROSS JOIN permiso p
WHERE r.nombre = 'ADMIN'
   OR (r.nombre = 'TECNICO' AND p.codigo IN ('panel.ver', 'documento.ver'));

INSERT INTO usuario_panel (id_usuario, id_panel)
SELECT u.id_usuario, p.id_panel
FROM usuario u CROSS JOIN panel p
WHERE (u.email = 'tecnico1@panelqr.local' AND p.codigo_qr IN ('P-001', 'P-003'))
   OR (u.email = 'tecnico2@panelqr.local' AND p.codigo_qr = 'P-002');

INSERT INTO usuario_grupo_panel (id_usuario, id_grupo)
SELECT u.id_usuario, g.id_grupo
FROM usuario u CROSS JOIN grupo_panel g
WHERE (u.email = 'tecnico1@panelqr.local' AND g.nombre = 'Edificio principal')
   OR (u.email = 'tecnico2@panelqr.local' AND g.nombre = 'Taller');

INSERT INTO tipo_documento (nombre, descripcion) VALUES
    ('Ficha técnica', 'Datos técnicos generales del panel'),
    ('Procedimiento de mantenimiento', 'Instrucciones para mantenimiento'),
    ('Diagrama eléctrico', 'Esquema eléctrico del panel');

INSERT INTO repositorio (nombre, tipo, activo) VALUES
    ('Repositorio local', 'LOCAL', TRUE),
    ('Repositorio externo de ejemplo', 'OTRO', FALSE);

INSERT INTO documento (id_panel, id_tipo_documento, titulo, descripcion, id_usuario_creador)
SELECT p.id_panel, t.id_tipo_documento, seed.titulo, seed.descripcion, u.id_usuario
FROM (VALUES
    ('P-001', 'Ficha técnica', 'Ficha técnica P-001', 'Datos generales del panel principal.'),
    ('P-001', 'Diagrama eléctrico', 'Diagrama eléctrico P-001', 'Diagrama del panel principal.'),
    ('P-002', 'Procedimiento de mantenimiento', 'Mantenimiento P-002', 'Procedimiento de mantenimiento del panel de iluminación.')
) AS seed(codigo_panel, tipo, titulo, descripcion)
JOIN panel p ON p.codigo_qr = seed.codigo_panel
JOIN tipo_documento t ON t.nombre = seed.tipo
CROSS JOIN usuario u
WHERE u.email = 'admin@panelqr.local';

INSERT INTO documento_version (
    id_documento, numero_version, id_repositorio, ruta_externa, nombre_archivo,
    mime_type, tamano_bytes, hash_sha256, id_usuario_subida, notas, es_actual
)
SELECT d.id_documento, seed.numero, r.id_repositorio, seed.ruta, seed.archivo,
       'text/plain', seed.tamano, seed.hash_sha256, u.id_usuario, seed.notas, seed.es_actual
FROM (VALUES
    ('Ficha técnica P-001', '1.0', 'demo/ficha-p001-v1.txt', 'ficha-p001.txt', 206, '58f243d763ca4749316be1ac4309449fd70f822f3b8ccea6148daeef58e9c373', 'Versión inicial', FALSE),
    ('Ficha técnica P-001', '1.1', 'demo/ficha-p001-v2.txt', 'ficha-p001.txt', 285, '3192e883314f1944386109ef0cd84bf67a8e8b61e51aa3893638dbbb8f363faa', 'Actualización de ejemplo', TRUE),
    ('Diagrama eléctrico P-001', '1.0', 'demo/diagrama-p001.txt', 'diagrama-p001.txt', 202, 'a2edee9415652cb693b5d5aa5571fe0c69255c3f350e5498130cf730f6833869', 'Versión inicial', TRUE),
    ('Mantenimiento P-002', '1.0', 'demo/mantenimiento-p002.txt', 'mantenimiento-p002.txt', 251, 'a7de28c9f1602a487fef5011d5a80a1e24057f0c97b22b330c3e6d08bab25a3c', 'Versión inicial', TRUE)
) AS seed(titulo, numero, ruta, archivo, tamano, hash_sha256, notas, es_actual)
JOIN documento d ON d.titulo = seed.titulo
JOIN repositorio r ON r.nombre = 'Repositorio local'
CROSS JOIN usuario u
WHERE u.email = 'admin@panelqr.local';

INSERT INTO auditoria (id_usuario, accion, entidad, id_entidad, resultado, detalle)
SELECT u.id_usuario, seed.accion, seed.entidad, seed.id_entidad, seed.resultado, seed.detalle
FROM (VALUES
    ('INICIO_SESION', 'usuario', 'admin@panelqr.local', 'OK', 'Inicio de sesión de prueba'),
    ('CONSULTA_PANEL', 'panel', 'P-001', 'OK', 'Consulta de panel de prueba'),
    ('CONSULTA_PANEL', 'panel', 'P-002', 'DENEGADO', 'Consulta denegada de ejemplo')
) AS seed(accion, entidad, id_entidad, resultado, detalle)
CROSS JOIN usuario u
WHERE u.email = 'admin@panelqr.local';
