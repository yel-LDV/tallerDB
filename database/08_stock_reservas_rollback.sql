-- ============================================================
--  TallerDB — Rollback de inventario y reservas
--  Archivo: database/08_stock_reservas_rollback.sql
--  Descripción:
--    Elimina triggers, tablas de auditoría, tabla reservas,
--    restricciones CHECK y la columna modelos.stock.
--    Ejecutar solo si se quiere volver al esquema del Tema 3.
--  Uso:
--    mariadb -h 127.0.0.1 -u "$MARIADB_USER" tallerdb \
--      < database/08_stock_reservas_rollback.sql
-- ============================================================

USE tallerdb;

DROP TRIGGER IF EXISTS trg_modelos_auditoria_ai;
DROP TRIGGER IF EXISTS trg_modelos_auditoria_au;
DROP TRIGGER IF EXISTS trg_modelos_auditoria_ad;
DROP TRIGGER IF EXISTS trg_reservas_auditoria_ai;
DROP TRIGGER IF EXISTS trg_reservas_auditoria_au;

DROP TABLE IF EXISTS auditoria_reservas;
DROP TABLE IF EXISTS auditoria_modelos;
DROP TABLE IF EXISTS reservas;

SET @chk_exists := (
    SELECT COUNT(*)
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'modelos'
      AND CONSTRAINT_NAME = 'chk_modelos_stock'
);
SET @sql := IF(
    @chk_exists > 0,
    'ALTER TABLE modelos DROP CONSTRAINT chk_modelos_stock',
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
    @chk_exists > 0,
    'ALTER TABLE modelos DROP CONSTRAINT chk_modelos_precio',
    'DO 0'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE modelos DROP COLUMN IF EXISTS stock;

SELECT 'stock_reservas: rollback aplicado' AS resultado;
