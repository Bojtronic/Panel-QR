ALTER TABLE panel
    ADD CONSTRAINT fk_panel_grupo
    FOREIGN KEY (id_grupo) REFERENCES grupo_panel(id_grupo) ON DELETE SET NULL;

ALTER TABLE usuario_rol
    ADD CONSTRAINT fk_usuario_rol_usuario
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    ADD CONSTRAINT fk_usuario_rol_rol
    FOREIGN KEY (id_rol) REFERENCES rol(id_rol) ON DELETE CASCADE;

ALTER TABLE rol_permiso
    ADD CONSTRAINT fk_rol_permiso_rol
    FOREIGN KEY (id_rol) REFERENCES rol(id_rol) ON DELETE CASCADE,
    ADD CONSTRAINT fk_rol_permiso_permiso
    FOREIGN KEY (id_permiso) REFERENCES permiso(id_permiso) ON DELETE CASCADE;

ALTER TABLE usuario_panel
    ADD CONSTRAINT fk_usuario_panel_usuario
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    ADD CONSTRAINT fk_usuario_panel_panel
    FOREIGN KEY (id_panel) REFERENCES panel(id_panel) ON DELETE CASCADE;

ALTER TABLE usuario_grupo_panel
    ADD CONSTRAINT fk_usuario_grupo_usuario
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    ADD CONSTRAINT fk_usuario_grupo_grupo
    FOREIGN KEY (id_grupo) REFERENCES grupo_panel(id_grupo) ON DELETE CASCADE;

ALTER TABLE documento
    ADD CONSTRAINT fk_documento_panel
    FOREIGN KEY (id_panel) REFERENCES panel(id_panel) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_documento_tipo
    FOREIGN KEY (id_tipo_documento) REFERENCES tipo_documento(id_tipo_documento) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_documento_creador
    FOREIGN KEY (id_usuario_creador) REFERENCES usuario(id_usuario) ON DELETE SET NULL;

ALTER TABLE documento_version
    ADD CONSTRAINT fk_version_documento
    FOREIGN KEY (id_documento) REFERENCES documento(id_documento) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_version_repositorio
    FOREIGN KEY (id_repositorio) REFERENCES repositorio(id_repositorio) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_version_usuario
    FOREIGN KEY (id_usuario_subida) REFERENCES usuario(id_usuario) ON DELETE SET NULL;

ALTER TABLE auditoria
    ADD CONSTRAINT fk_auditoria_usuario
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE SET NULL;

CREATE UNIQUE INDEX uq_documento_version_actual
    ON documento_version(id_documento)
    WHERE es_actual = TRUE;
CREATE INDEX idx_documento_panel ON documento(id_panel);
CREATE INDEX idx_version_documento ON documento_version(id_documento);
CREATE INDEX idx_auditoria_usuario_fecha ON auditoria(id_usuario, fecha_evento);
CREATE INDEX idx_auditoria_entidad ON auditoria(entidad, id_entidad);
