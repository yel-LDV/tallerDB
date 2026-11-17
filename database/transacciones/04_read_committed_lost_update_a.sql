-- ============================================================
--  TallerDB — READ COMMITTED, pérdida de actualización, Sesión A
--  Archivo: database/transacciones/04_read_committed_lost_update_a.sql
--  A bloquea la fila con SELECT ... FOR UPDATE, espera y suma 500.
--  B queda bloqueada hasta que A confirme; luego B lee el valor
--  actualizado (10500) y suma 1000, evitando la actualización perdida.
--  Ejecutar en la Terminal 1.
-- ============================================================

USE tallerdb;

SET @modelo_id := (
    SELECT id FROM modelos
    WHERE marca = '__TX__' AND nombre = 'Demo Transacciones' AND anio = 2026
);

SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
START TRANSACTION;

SELECT 'A1: fila bloqueada' AS paso, precio
FROM modelos
WHERE id = @modelo_id
FOR UPDATE;

SELECT SLEEP(5) AS espera_para_sesion_b;

UPDATE modelos
SET precio = precio + 500
WHERE id = @modelo_id;

COMMIT;

SELECT 'A2: después del COMMIT' AS paso, precio
FROM modelos
WHERE id = @modelo_id;
