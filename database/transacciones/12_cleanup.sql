-- ============================================================
--  TallerDB — Limpieza de las demos de transacciones
--  Archivo: database/transacciones/12_cleanup.sql
--  Elimina el modelo y el usuario temporales, sus reservas y
--  los registros de auditoría asociados.
-- ============================================================

USE tallerdb;

SET @modelo_id := (
    SELECT id FROM modelos
    WHERE marca = '__TX__' AND nombre = 'Demo Transacciones' AND anio = 2026
);

-- 1. Auditoría de reservas del modelo temporal.
DELETE ar
FROM auditoria_reservas ar
JOIN reservas r ON r.id = ar.reserva_id
WHERE r.modelo_id = @modelo_id;

-- 2. Reservas (no hay trigger de DELETE en reservas).
DELETE FROM reservas WHERE modelo_id = @modelo_id;

-- 3. Modelo (el trigger AFTER DELETE escribe una última auditoría).
DELETE FROM modelos WHERE id = @modelo_id;

-- 4. Auditoría del modelo, incluida la fila del DELETE.
DELETE FROM auditoria_modelos WHERE modelo_id = @modelo_id;

-- 5. Usuario temporal.
DELETE FROM users WHERE email = '__tx__@example.invalid';

SELECT 'LIMPIEZA: datos temporales eliminados' AS resultado;

SELECT
    (SELECT COUNT(*) FROM modelos WHERE marca = '__TX__') AS modelos_tx,
    (SELECT COUNT(*) FROM users WHERE email = '__tx__@example.invalid') AS usuarios_tx,
    (SELECT COUNT(*) FROM reservas) AS reservas_totales;
