-- ============================================================
--  TallerDB — Esquema para PostgreSQL 13+
--  Archivo: database/schema_postgresql.sql
--  Uso: psql -U taller -d tallerdb -f database/schema_postgresql.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    is_admin        BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ix_users_email UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS modelos (
    id          SERIAL PRIMARY KEY,
    marca       VARCHAR(100)   NOT NULL,
    nombre      VARCHAR(120)   NOT NULL,
    anio        INTEGER        NOT NULL,
    precio      NUMERIC(12,2)  NOT NULL,
    color       VARCHAR(50)    NULL,
    tipo        VARCHAR(40)    NOT NULL DEFAULT 'sedan',
    transmision VARCHAR(30)    NOT NULL DEFAULT 'manual',
    disponible  BOOLEAN        NOT NULL DEFAULT TRUE,
    descripcion TEXT           NULL,
    imagen_url  VARCHAR(500)   NULL,
    modelo_3d_key       VARCHAR(255) NULL,
    modelo_3d_url       VARCHAR(500) NULL,
    modelo_3d_formato   VARCHAR(10)  NULL,
    modelo_3d_tamano    INTEGER      NULL,
    modelo_3d_subido_at TIMESTAMP WITH TIME ZONE NULL,
    created_at  TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_modelo_marca_nombre_anio UNIQUE (marca, nombre, anio)
);

CREATE INDEX IF NOT EXISTS ix_modelos_marca ON modelos (marca);
CREATE INDEX IF NOT EXISTS ix_modelos_nombre ON modelos (nombre);
