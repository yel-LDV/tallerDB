-- ============================================================
--  TallerDB — Init automático para el contenedor MariaDB
--  Archivo: database/init/01_schema.sql
--  Este archivo se ejecuta automáticamente por la imagen oficial
--  de MariaDB (/docker-entrypoint-initdb.d) la primera vez que se
--  levanta el volumen de datos. La base de datos y el usuario ya
--  fueron creados por la imagen con las variables MARIADB_DATABASE
--  y MARIADB_USER, por lo que aquí solo se crea el esquema.
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT 1,
    is_admin        BOOLEAN      NOT NULL DEFAULT 0,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY ix_users_email (email)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS modelos (
    id          INT            AUTO_INCREMENT PRIMARY KEY,
    marca       VARCHAR(100)   NOT NULL,
    nombre      VARCHAR(120)   NOT NULL,
    anio        INT            NOT NULL,
    precio      DECIMAL(12,2)  NOT NULL,
    color       VARCHAR(50)    NULL,
    tipo        VARCHAR(40)    NOT NULL DEFAULT 'sedan',
    transmision VARCHAR(30)    NOT NULL DEFAULT 'manual',
    disponible  BOOLEAN        NOT NULL DEFAULT 1,
    descripcion  TEXT           NULL,
    imagen_url  VARCHAR(500)   NULL,
    modelo_3d_key        VARCHAR(255) NULL,
    modelo_3d_url        VARCHAR(500) NULL,
    modelo_3d_formato    VARCHAR(10)  NULL,
    modelo_3d_tamano     INT          NULL,
    modelo_3d_subido_at  DATETIME     NULL,
    created_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_modelo_marca_nombre_anio (marca, nombre, anio),
    KEY ix_modelos_marca  (marca),
    KEY ix_modelos_nombre (nombre)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
