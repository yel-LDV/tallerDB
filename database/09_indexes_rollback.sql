-- ============================================================
--  TallerDB — Rollback de índices adicionales
--  Archivo: database/09_indexes_rollback.sql
-- ============================================================

USE tallerdb;

DROP INDEX IF EXISTS idx_reservas_created_at ON reservas;
DROP INDEX IF EXISTS idx_reservas_estado ON reservas;
DROP INDEX IF EXISTS idx_modelos_tipo_disponible ON modelos;
DROP INDEX IF EXISTS idx_modelos_anio ON modelos;
DROP INDEX IF EXISTS idx_modelos_precio ON modelos;
DROP INDEX IF EXISTS idx_modelos_disponible ON modelos;
DROP INDEX IF EXISTS idx_modelos_tipo ON modelos;

SELECT 'indexes: rollback aplicado' AS resultado;
