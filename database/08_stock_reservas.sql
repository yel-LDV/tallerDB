-- ============================================================
--  TallerDB — Inventario y reservas (Tema 4)
--  Archivo: database/08_stock_reservas.sql
--  Motor: MariaDB 11+
--  Descripción:
--    Agrega la columna modelos.stock, la restricción CHECK
--    stock >= 0, la tabla reservas con FK a modelos y users,
--    y las tablas de auditoría usadas por los triggers.
--  Uso:
--    mariadb -h 127.0.0.1 -u "$MARIADB_USER" tallerdb \
--      < database/08_stock_reservas.sql
--  Rollback: database/08_stock_reservas_rollback.sql
-- ============================================================

USE tallerdb;

-- ------------------------------------------------------------
-- 1. Columna stock en modelos
--    DEFAULT 1 para no romper las filas existentes. El valor se
--    ajusta en los datos de demostración, no en producción.
-- ------------------------------------------------------------
ALTER TABLE modelos
    ADD COLUMN IF NOT EXISTS stock INT NOT NULL DEFAULT 1
    AFTER disponible;

-- ------------------------------------------------------------
-- 2. Restricciones CHECK (idempotentes)
--    MariaDB aplica CHECK desde 10.2.1; en 11 es obligatorio.
-- ------------------------------------------------------------
SET @chk_exists := (
    SELECT COUNT(*)
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'modelos'
      AND CONSTRAINT_NAME = 'chk_modelos_stock'
);
SET @sql := IF(
    @chk_exists = 0,
    'ALTER TABLE modelos ADD CONSTRAINT chk_modelos_stock CHECK (stock >= 0)',
    'DO 0'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @chk_exists := (
    SELECT COUNT(*)
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'modelos'
      AND CONSTRAINT_NAME = 'chk_modelos_precio'
);
SET @sql := IF(
    @chk_exists = 0,
    'ALTER TABLE modelos ADD CONSTRAINT chk_modelos_precio CHECK (precio >= 0)',
    'DO 0'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Coherencia inicial: un modelo no disponible no debe tener stock.
UPDATE modelos
SET stock = 0
WHERE disponible = 0 AND stock <> 0;

-- ------------------------------------------------------------
-- 3. Tabla reservas
--    Primera relación FK del modelo: reservas.modelo_id -> modelos.id
--    y reservas.usuario_id -> users.id.
--    ON DELETE CASCADE evita romper el CRUD actual de modelos.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reservas (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    modelo_id   INT NOT NULL,
    usuario_id  INT NOT NULL,
    cantidad    INT NOT NULL DEFAULT 1,
    estado      ENUM('pendiente', 'confirmada', 'cancelada')
                NOT NULL DEFAULT 'pendiente',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_reservas_modelo
        FOREIGN KEY (modelo_id) REFERENCES modelos (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_reservas_usuario
        FOREIGN KEY (usuario_id) REFERENCES users (id)
        ON DELETE CASCADE,
    CONSTRAINT chk_reservas_cantidad CHECK (cantidad > 0),
    KEY ix_reservas_modelo_estado (modelo_id, estado),
    KEY ix_reservas_usuario (usuario_id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 4. Tablas de auditoría (usadas por database/06_triggers.sql)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auditoria_modelos (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY,
    modelo_id        INT NOT NULL,
    accion           ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    precio_anterior  DECIMAL(12,2) NULL,
    precio_nuevo     DECIMAL(12,2) NULL,
    stock_anterior   INT NULL,
    stock_nuevo      INT NULL,
    usuario_bd       VARCHAR(100) NOT NULL,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_auditoria_modelo (modelo_id, created_at)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS auditoria_reservas (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY,
    reserva_id       INT NOT NULL,
    accion           VARCHAR(50) NOT NULL,
    estado_anterior  VARCHAR(20) NULL,
    estado_nuevo     VARCHAR(20) NULL,
    cantidad         INT NULL,
    usuario_bd       VARCHAR(100) NOT NULL,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_auditoria_reserva (reserva_id, created_at)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 5. Inicialización de los datos de ejemplo
--    Los modelos disponibles parten con 5 unidades. Solo se aplica
--    a modelos que aún no tienen reservas, para que el script sea
--    seguro de reejecutar. En producción este bloque no debe usarse:
--    el stock se gestiona con reservas y ajustes de inventario.
-- ------------------------------------------------------------
UPDATE modelos m
SET m.stock = 5
WHERE m.disponible = 1
  AND m.stock = 1
  AND NOT EXISTS (
      SELECT 1 FROM reservas r WHERE r.modelo_id = m.id
  );

-- ------------------------------------------------------------
-- 6. Verificación
-- ------------------------------------------------------------
SELECT 'stock_reservas: esquema aplicado' AS resultado;

SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'modelos'
  AND COLUMN_NAME = 'stock';

SELECT TABLE_NAME
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('reservas', 'auditoria_modelos', 'auditoria_reservas')
ORDER BY TABLE_NAME;
