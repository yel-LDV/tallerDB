-- ============================================================
--  TallerDB — Rollback de funciones
--  Archivo: database/05_functions_rollback.sql
-- ============================================================

USE tallerdb;

DROP FUNCTION IF EXISTS fn_total_reservas;
DROP FUNCTION IF EXISTS fn_stock_disponible;
DROP FUNCTION IF EXISTS fn_precio_con_impuesto;

SELECT 'functions: rollback aplicado' AS resultado;
