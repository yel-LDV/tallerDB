-- ============================================================
--  TallerDB — READ COMMITTED, Sesión A
--  Archivo: database/transacciones/02_read_committed_sesion_a.sql
--  Demuestra lectura no repetible: A lee 10000, B actualiza y
--  confirma a 12000, y A vuelve a leer 12000 dentro de la misma
--  transacción. READ COMMITTED lo permite.
--  Ejecutar en la Terminal 1; la Terminal 2 ejecuta el script B
--  mientras A está en SELECT SLEEP(5).
-- ============================================================

USE tallerdb;

SET @modelo_id := (
    SELECT id FROM modelos
    WHERE marca = '__TX__' AND nombre = 'Demo Transacciones' AND anio = 2026
);

SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
START TRANSACTION;

SELECT 'A1: lectura inicial' AS paso, precio, stock
FROM modelos
WHERE id = @modelo_id;

-- Da tiempo a que la Sesión B actualice y confirme.
SELECT SLEEP(5) AS espera_para_sesion_b;

SELECT 'A2: segunda lectura (misma transacción)' AS paso, precio, stock
FROM modelos
WHERE id = @modelo_id;

COMMIT;

SELECT 'A3: después del COMMIT' AS paso, precio, stock
FROM modelos
WHERE id = @modelo_id;
