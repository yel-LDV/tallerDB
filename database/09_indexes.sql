-- ============================================================
--  TallerDB — Índices adicionales (Tema 3)
--  Archivo: database/09_indexes.sql
--  Motor: MariaDB 11+
--  Descripción:
--    Índices para los filtros y ordenamientos usados por el catálogo.
--    Cada bloque es idempotente: consulta information_schema antes
--    de crear el índice.
--  Uso:
--    mariadb -h 127.0.0.1 -u "$MARIADB_USER" tallerdb \
--      < database/09_indexes.sql
--  Rollback: database/09_indexes_rollback.sql
-- ============================================================

USE tallerdb;

-- idx_modelos_tipo
SET @idx_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'modelos'
      AND INDEX_NAME = 'idx_modelos_tipo'
);
SET @sql := IF(@idx_exists = 0,
    'CREATE INDEX idx_modelos_tipo ON modelos (tipo)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_modelos_disponible
SET @idx_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'modelos'
      AND INDEX_NAME = 'idx_modelos_disponible'
);
SET @sql := IF(@idx_exists = 0,
    'CREATE INDEX idx_modelos_disponible ON modelos (disponible)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_modelos_precio
SET @idx_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'modelos'
      AND INDEX_NAME = 'idx_modelos_precio'
);
SET @sql := IF(@idx_exists = 0,
    'CREATE INDEX idx_modelos_precio ON modelos (precio)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_modelos_anio
SET @idx_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'modelos'
      AND INDEX_NAME = 'idx_modelos_anio'
);
SET @sql := IF(@idx_exists = 0,
    'CREATE INDEX idx_modelos_anio ON modelos (anio)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_modelos_tipo_disponible
SET @idx_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'modelos'
      AND INDEX_NAME = 'idx_modelos_tipo_disponible'
);
SET @sql := IF(@idx_exists = 0,
    'CREATE INDEX idx_modelos_tipo_disponible ON modelos (tipo, disponible)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_reservas_estado
SET @idx_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'reservas'
      AND INDEX_NAME = 'idx_reservas_estado'
);
SET @sql := IF(@idx_exists = 0,
    'CREATE INDEX idx_reservas_estado ON reservas (estado)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_reservas_created_at
SET @idx_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'reservas'
      AND INDEX_NAME = 'idx_reservas_created_at'
);
SET @sql := IF(@idx_exists = 0,
    'CREATE INDEX idx_reservas_created_at ON reservas (created_at)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SELECT 'indexes: índices aplicados' AS resultado;

SELECT TABLE_NAME, INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columnas
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND INDEX_NAME LIKE 'idx_%'
GROUP BY TABLE_NAME, INDEX_NAME
ORDER BY TABLE_NAME, INDEX_NAME;
