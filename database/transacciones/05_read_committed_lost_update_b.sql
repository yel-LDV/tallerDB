-- ============================================================
--  TallerDB — READ COMMITTED, pérdida de actualización, Sesión B
--  Archivo: database/transacciones/05_read_committed_lost_update_b.sql
--  B intenta bloquear la misma fila. Queda esperando a que A
--  confirme; después lee 10500 y suma 1000. Resultado: 11500.
--  Ejecutar en la Terminal 2.
-- ============================================================

USE tallerdb;

SET @modelo_id := (
    SELECT id FROM modelos
    WHERE marca = '__TX__' AND nombre = 'Demo Transacciones' AND anio = 2026
);

SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
START TRANSACTION;

SELECT 'B1: esperando el bloqueo de A' AS paso, precio
FROM modelos
WHERE id = @modelo_id
FOR UPDATE;

UPDATE modelos
SET precio = precio + 1000
WHERE id = @modelo_id;

COMMIT;

SELECT 'B2: después del COMMIT' AS paso, precio
FROM modelos
WHERE id = @modelo_id;
