-- ============================================================
--  TallerDB — Verificación final de las demos
--  Archivo: database/transacciones/11_verify.sql
-- ============================================================

USE tallerdb;

SET @modelo_id := (
    SELECT id FROM modelos
    WHERE marca = '__TX__' AND nombre = 'Demo Transacciones' AND anio = 2026
);

SELECT 'ESTADO DEL MODELO' AS bloque;
SELECT id, marca, nombre, anio, precio, stock, disponible
FROM modelos
WHERE id = @modelo_id;

SELECT 'RESERVAS DEL MODELO' AS bloque;
SELECT id, modelo_id, usuario_id, cantidad, estado, created_at
FROM reservas
WHERE modelo_id = @modelo_id
ORDER BY id;

SELECT 'AUDITORÍA DE MODELO' AS bloque;
SELECT id, modelo_id, accion, precio_anterior, precio_nuevo,
       stock_anterior, stock_nuevo, usuario_bd, created_at
FROM auditoria_modelos
WHERE modelo_id = @modelo_id
ORDER BY id;

SELECT 'AUDITORÍA DE RESERVAS' AS bloque;
SELECT ar.id, ar.reserva_id, ar.accion, ar.estado_anterior,
       ar.estado_nuevo, ar.cantidad, ar.usuario_bd, ar.created_at
FROM auditoria_reservas ar
JOIN reservas r ON r.id = ar.reserva_id
WHERE r.modelo_id = @modelo_id
ORDER BY ar.id;
