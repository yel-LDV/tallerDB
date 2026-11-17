-- ============================================================
--  TallerDB — Preparación de las demos de transacciones
--  Archivo: database/transacciones/00_setup.sql
--  Motor: MariaDB 11+
--  Descripción:
--    Crea un usuario y un modelo temporales (marca __TX__) para
--    las demos. No toca los 18 modelos reales del catálogo.
--  Uso:
--    mariadb -h 127.0.0.1 -u "$MARIADB_USER" tallerdb \
--      < database/transacciones/00_setup.sql
-- ============================================================

USE tallerdb;

-- Usuario temporal para las reservas (FK users.id).
INSERT INTO users (email, hashed_password, is_active, is_admin)
VALUES ('__tx__@example.invalid', 'x', 1, 0)
ON DUPLICATE KEY UPDATE is_active = 1;

SET @usuario_id := (
    SELECT id FROM users WHERE email = '__tx__@example.invalid'
);

-- Modelo temporal. stock = 5 para la demo de READ COMMITTED.
INSERT INTO modelos (
    marca, nombre, anio, precio, color, tipo, transmision,
    disponible, descripcion, stock
) VALUES (
    '__TX__', 'Demo Transacciones', 2026, 10000.00, 'Gris',
    'sedan', 'manual', 1, 'Modelo temporal para demos de transacciones', 5
)
ON DUPLICATE KEY UPDATE
    precio = 10000.00,
    stock = 5,
    disponible = 1;

SET @modelo_id := (
    SELECT id FROM modelos
    WHERE marca = '__TX__' AND nombre = 'Demo Transacciones' AND anio = 2026
);

DELETE ar
FROM auditoria_reservas ar
JOIN reservas r ON r.id = ar.reserva_id
WHERE r.modelo_id = @modelo_id;

DELETE FROM reservas WHERE modelo_id = @modelo_id;

SELECT
    @modelo_id AS modelo_id,
    @usuario_id AS usuario_id,
    precio,
    stock,
    disponible
FROM modelos
WHERE id = @modelo_id;
