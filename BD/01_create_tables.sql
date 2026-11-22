CREATE TABLE grupo_panel (
    id_grupo SERIAL PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL UNIQUE,
    descripcion TEXT
);

CREATE TABLE panel (
    id_panel SERIAL PRIMARY KEY,
    id_grupo INT,
    codigo_qr VARCHAR(128) NOT NULL UNIQUE,
    nombre VARCHAR(150) NOT NULL,
    ubicacion VARCHAR(255),
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO'
        CHECK (estado IN ('ACTIVO', 'INACTIVO', 'MANTENIMIENTO')),
    fecha_alta TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE usuario (
    id_usuario SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_alta TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rol (
    id_rol SERIAL PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL UNIQUE,
    descripcion TEXT
);

CREATE TABLE permiso (
    id_permiso SERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT
);

CREATE TABLE usuario_rol (
    id_usuario INT NOT NULL,
    id_rol INT NOT NULL,
    PRIMARY KEY (id_usuario, id_rol)
);

CREATE TABLE rol_permiso (
    id_rol INT NOT NULL,
    id_permiso INT NOT NULL,
    PRIMARY KEY (id_rol, id_permiso)
);

CREATE TABLE usuario_panel (
    id_usuario INT NOT NULL,
    id_panel INT NOT NULL,
    PRIMARY KEY (id_usuario, id_panel)
);

CREATE TABLE usuario_grupo_panel (
    id_usuario INT NOT NULL,
    id_grupo INT NOT NULL,
    PRIMARY KEY (id_usuario, id_grupo)
);

CREATE TABLE tipo_documento (
    id_tipo_documento SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT
);

CREATE TABLE repositorio (
    id_repositorio SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    tipo VARCHAR(30) NOT NULL
        CHECK (tipo IN ('LOCAL', 'GOOGLE_DRIVE', 'ONEDRIVE', 'SHAREPOINT', 'OTRO')),
    url_base VARCHAR(500),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE documento (
    id_documento SERIAL PRIMARY KEY,
    id_panel INT NOT NULL,
    id_tipo_documento INT NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT,
    id_usuario_creador INT,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE documento_version (
    id_version SERIAL PRIMARY KEY,
    id_documento INT NOT NULL,
    numero_version VARCHAR(20) NOT NULL,
    id_repositorio INT NOT NULL,
    ruta_externa VARCHAR(1000) NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    tamano_bytes BIGINT CHECK (tamano_bytes IS NULL OR tamano_bytes >= 0),
    hash_sha256 CHAR(64),
    id_usuario_subida INT,
    fecha_subida TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notas TEXT,
    es_actual BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (id_documento, numero_version)
);

CREATE TABLE auditoria (
    id_evento BIGSERIAL PRIMARY KEY,
    id_usuario INT,
    fecha_evento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accion VARCHAR(80) NOT NULL,
    entidad VARCHAR(50),
    id_entidad VARCHAR(100),
    resultado VARCHAR(20) NOT NULL
        CHECK (resultado IN ('OK', 'DENEGADO', 'ERROR')),
    ip VARCHAR(45),
    user_agent VARCHAR(255),
    detalle TEXT
);
