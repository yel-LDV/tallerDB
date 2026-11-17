-- ============================================================
--  TallerDB — SERIALIZABLE, sobreventa, Sesión A
--  Archivo: database/transacciones/09_serializable_overselling_a.sql
--  A reserva la única unidad disponible. El procedimiento usa
--  SELECT ... FOR UPDATE, por lo que B queda esperando. A duerme
--  5 segundos antes de confirmar para que se vea el bloqueo.
--  Ejecutar en la Terminal 1.
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

SELECT 'A1: reserva creada' AS paso,
       @reserva_id AS reserva_id,
       precio, stock
FROM modelos
WHERE id = @modelo_id;

SELECT SLEEP(5) AS espera_para_sesion_b;

COMMIT;

SELECT 'A2: después del COMMIT' AS paso,
       @reserva_id AS reserva_id,
       precio, stock
FROM modelos
WHERE id = @modelo_id;
