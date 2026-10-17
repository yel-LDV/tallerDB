-- ============================================================
--  TallerDB — Script de creación de esquema (MariaDB 10.6+)
--  Archivo: database/schema_mariadb.sql
--  Descripción: crea la base de datos `tallerdb` y las tablas
--               `users` (usuarios) y `modelos` (catálogo de autos).
--  Uso: mariadb -u root -p < database/schema_mariadb.sql
--       (también se ejecuta automáticamente al levantar el
--        contenedor MariaDB de docker-compose, ver database/init/)
-- ============================================================

CREATE DATABASE IF NOT EXISTS tallerdb
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE tallerdb;

-- ------------------------------------------------------------
-- Tabla: usuarios del sistema (autenticación)
-- ------------------------------------------------------------
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

-- ------------------------------------------------------------
-- Tabla: catálogo de modelos de autos (categoría principal)
-- ------------------------------------------------------------
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
    created_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    -- Un modelo se identifica por (marca, nombre, año)
    UNIQUE KEY uq_modelo_marca_nombre_anio (marca, nombre, anio),
    -- Índices para acelerar las consultas por marca y por nombre
    KEY ix_modelos_marca  (marca),
    KEY ix_modelos_nombre (nombre)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
