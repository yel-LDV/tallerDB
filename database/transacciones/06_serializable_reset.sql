-- ============================================================
--  TallerDB — Reset para la demo SERIALIZABLE
--  Archivo: database/transacciones/06_serializable_reset.sql
-- ============================================================

USE tallerdb;

SET @modelo_id := (
    SELECT id FROM modelos
    WHERE marca = '__TX__' AND nombre = 'Demo Transacciones' AND anio = 2026
);

DELETE ar
FROM auditoria_reservas ar
JOIN reservas r ON r.id = ar.reserva_id
WHERE r.modelo_id = @modelo_id;

DELETE FROM reservas WHERE modelo_id = @modelo_id;

UPDATE modelos
SET precio = 10000.00,
    stock = 1,
    disponible = 1
WHERE id = @modelo_id;

SELECT 'SERIALIZABLE: estado inicial' AS paso,
       precio, stock, disponible
FROM modelos
WHERE id = @modelo_id;

SELECT COUNT(*) AS reservas_confirmadas
FROM reservas
WHERE modelo_id = @modelo_id AND estado = 'confirmada';
