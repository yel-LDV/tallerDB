-- ============================================================
--  TallerDB — Rollback de vistas
--  Archivo: database/03_views_rollback.sql
-- ============================================================

USE tallerdb;

DROP VIEW IF EXISTS vw_modelos_bajo_stock;
DROP VIEW IF EXISTS vw_reservas_activas;
DROP VIEW IF EXISTS vw_resumen_tipos;
DROP VIEW IF EXISTS vw_estadisticas_marca;
DROP VIEW IF EXISTS vw_modelos_disponibles;

SELECT 'views: rollback aplicado' AS resultado;
