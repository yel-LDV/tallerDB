-- ============================================================
--  TallerDB — Vistas (Tema 3)
--  Archivo: database/03_views.sql
--  Motor: MariaDB 11+
--  Descripción: vistas de consulta para catálogo, estadísticas,
--               reservas activas y modelos con stock bajo.
--  Uso:
--    mariadb -h 127.0.0.1 -u "$MARIADB_USER" tallerdb \
--      < database/03_views.sql
--  Rollback: database/03_views_rollback.sql
-- ============================================================

USE tallerdb;

-- 1. Catálogo visible: solo modelos disponibles y con stock.
CREATE OR REPLACE VIEW vw_modelos_disponibles AS
SELECT
    id,
    marca,
    nombre,
    anio,
    precio,
    stock,
    tipo,
    transmision
FROM modelos
WHERE disponible = 1
  AND stock > 0;

-- 2. Estadísticas agregadas por marca.
CREATE OR REPLACE VIEW vw_estadisticas_marca AS
SELECT
    marca,
    COUNT(*) AS total_modelos,
    SUM(CASE WHEN disponible = 1 AND stock > 0 THEN 1 ELSE 0 END) AS disponibles,
    SUM(stock) AS stock_total,
    ROUND(AVG(precio), 2) AS precio_promedio,
    MIN(precio) AS precio_min,
    MAX(precio) AS precio_max
FROM modelos
GROUP BY marca;

-- 3. Resumen por tipo de carrocería.
CREATE OR REPLACE VIEW vw_resumen_tipos AS
SELECT
    tipo,
    COUNT(*) AS cantidad,
    SUM(CASE WHEN disponible = 1 AND stock > 0 THEN 1 ELSE 0 END) AS disponibles,
    ROUND(AVG(precio), 2) AS precio_promedio,
    SUM(stock) AS stock_total
FROM modelos
GROUP BY tipo;

-- 4. Reservas activas con datos del modelo y del usuario.
CREATE OR REPLACE VIEW vw_reservas_activas AS
SELECT
    r.id AS reserva_id,
    r.modelo_id,
    m.marca,
    m.nombre,
    m.anio,
    r.usuario_id,
    u.email,
    r.cantidad,
    r.estado,
    r.created_at
FROM reservas r
JOIN modelos m ON m.id = r.modelo_id
JOIN users u ON u.id = r.usuario_id
WHERE r.estado IN ('pendiente', 'confirmada');

-- 5. Modelos con stock bajo o agotado.
CREATE OR REPLACE VIEW vw_modelos_bajo_stock AS
SELECT
    id,
    marca,
    nombre,
    anio,
    stock,
    disponible
FROM modelos
WHERE stock <= 2
ORDER BY stock ASC, marca ASC;

SELECT 'views: 5 vistas creadas' AS resultado;

SELECT TABLE_NAME
FROM information_schema.VIEWS
WHERE TABLE_SCHEMA = DATABASE()
ORDER BY TABLE_NAME;
