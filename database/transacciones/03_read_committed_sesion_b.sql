-- ============================================================
--  TallerDB — READ COMMITTED, Sesión B
--  Archivo: database/transacciones/03_read_committed_sesion_b.sql
--  Actualiza el precio de 10000 a 12000 y confirma.
--  Ejecutar en la Terminal 2 mientras la Sesión A duerme.
-- ============================================================

USE tallerdb;

SET @modelo_id := (
    SELECT id FROM modelos
    WHERE marca = '__TX__' AND nombre = 'Demo Transacciones' AND anio = 2026
);

SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
START TRANSACTION;

UPDATE modelos
SET precio = 12000.00
WHERE id = @modelo_id;

COMMIT;

SELECT 'B: actualización confirmada' AS paso, precio, stock
FROM modelos
WHERE id = @modelo_id;
