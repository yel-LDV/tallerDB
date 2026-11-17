-- ============================================================
--  TallerDB — SERIALIZABLE, sobreventa, Sesión B
--  Archivo: database/transacciones/10_serializable_overselling_b.sql
--  B intenta reservar la misma unidad. Espera el bloqueo de A;
--  cuando A confirma, el stock es 0 y el procedimiento lanza
--  "Stock insuficiente" (SQLSTATE 45000).
--  Ejecutar en la Terminal 2.
-- ============================================================

USE tallerdb;

SET @modelo_id := (
    SELECT id FROM modelos
    WHERE marca = '__TX__' AND nombre = 'Demo Transacciones' AND anio = 2026
);
SET @usuario_id := (
    SELECT id FROM users WHERE email = '__tx__@example.invalid'
);
SET @reserva_id := NULL;

SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
START TRANSACTION;

CALL sp_reservar_modelo(@modelo_id, @usuario_id, 1, @reserva_id);

COMMIT;

SELECT 'B: reserva creada' AS paso,
       @reserva_id AS reserva_id,
       stock
FROM modelos
WHERE id = @modelo_id;
