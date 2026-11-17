-- ============================================================
--  TallerDB — Rollback de procedimientos
--  Archivo: database/04_procedures_rollback.sql
-- ============================================================

USE tallerdb;

DROP PROCEDURE IF EXISTS sp_cancelar_reserva;
DROP PROCEDURE IF EXISTS sp_reservar_modelo;
DROP PROCEDURE IF EXISTS sp_actualizar_precio;
DROP PROCEDURE IF EXISTS sp_crear_modelo;

SELECT 'procedures: rollback aplicado' AS resultado;
