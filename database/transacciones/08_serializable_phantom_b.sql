-- ============================================================
--  TallerDB — SERIALIZABLE, lectura fantasma, Sesión B
--  Archivo: database/transacciones/08_serializable_phantom_b.sql
--  B intenta insertar una reserva. Queda bloqueada hasta que A
--  confirme; después inserta. Esa fila es la que A no debe ver
--  dentro de su transacción (no hay lectura fantasma).
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

SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
START TRANSACTION;

INSERT INTO reservas (modelo_id, usuario_id, cantidad, estado)
VALUES (@modelo_id, @usuario_id, 1, 'confirmada');

COMMIT;

SELECT 'B: inserción confirmada' AS paso, COUNT(*) AS reservas_confirmadas
FROM reservas
WHERE modelo_id = @modelo_id AND estado = 'confirmada';
