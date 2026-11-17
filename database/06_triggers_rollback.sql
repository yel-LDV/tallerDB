-- ============================================================
--  TallerDB — Rollback de triggers
--  Archivo: database/06_triggers_rollback.sql
-- ============================================================

USE tallerdb;

DROP TRIGGER IF EXISTS trg_reservas_auditoria_au;
DROP TRIGGER IF EXISTS trg_reservas_auditoria_ai;
DROP TRIGGER IF EXISTS trg_modelos_auditoria_ad;
DROP TRIGGER IF EXISTS trg_modelos_auditoria_au;
DROP TRIGGER IF EXISTS trg_modelos_auditoria_ai;

SELECT 'triggers: rollback aplicado' AS resultado;
