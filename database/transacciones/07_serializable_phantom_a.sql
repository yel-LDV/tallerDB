-- ============================================================
--  TallerDB — SERIALIZABLE, lectura fantasma, Sesión A
--  Archivo: database/transacciones/07_serializable_phantom_a.sql
--  A cuenta las reservas confirmadas, espera y vuelve a contar.
--  En SERIALIZABLE, el SELECT toma bloqueos de rango (next-key);
--  la inserción de B queda bloqueada hasta que A confirme, por lo
--  que A no ve la fila fantasma.
--  Ejecutar en la Terminal 1.
-- ============================================================

USE tallerdb;

SET @modelo_id := (
    SELECT id FROM modelos
    WHERE marca = '__TX__' AND nombre = 'Demo Transacciones' AND anio = 2026
);

SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
START TRANSACTION;

SELECT 'A1: conteo inicial' AS paso, COUNT(*) AS reservas_confirmadas
FROM reservas
WHERE modelo_id = @modelo_id AND estado = 'confirmada';

SELECT SLEEP(5) AS espera_para_sesion_b;

SELECT 'A2: conteo final (misma transacción)' AS paso, COUNT(*) AS reservas_confirmadas
FROM reservas
WHERE modelo_id = @modelo_id AND estado = 'confirmada';

COMMIT;

SELECT 'A3: después del COMMIT' AS paso, COUNT(*) AS reservas_confirmadas
FROM reservas
WHERE modelo_id = @modelo_id AND estado = 'confirmada';
