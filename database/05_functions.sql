-- ============================================================
--  TallerDB — Funciones almacenadas (Tema 3)
--  Archivo: database/05_functions.sql
--  Motor: MariaDB 11+
--  Uso:
--    mariadb -h 127.0.0.1 -u "$MARIADB_USER" tallerdb \
--      < database/05_functions.sql
--  Rollback: database/05_functions_rollback.sql
-- ============================================================

USE tallerdb;

DROP FUNCTION IF EXISTS fn_precio_con_impuesto;
DROP FUNCTION IF EXISTS fn_stock_disponible;
DROP FUNCTION IF EXISTS fn_total_reservas;

DELIMITER $$

-- 1. Precio con impuesto: precio * (1 + tasa/100), redondeado a 2 decimales.
CREATE FUNCTION fn_precio_con_impuesto(
    p_precio DECIMAL(12,2),
    p_tasa DECIMAL(5,2)
)
RETURNS DECIMAL(12,2)
DETERMINISTIC
BEGIN
    RETURN ROUND(p_precio * (1 + p_tasa / 100), 2);
END$$

-- 2. Stock actual de un modelo; 0 si el modelo no existe.
CREATE FUNCTION fn_stock_disponible(p_modelo_id INT)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_stock INT DEFAULT 0;
    SELECT COALESCE(stock, 0)
      INTO v_stock
      FROM modelos
     WHERE id = p_modelo_id;
    RETURN COALESCE(v_stock, 0);
END$$

-- 3. Total de reservas de un modelo, opcionalmente filtradas por estado.
CREATE FUNCTION fn_total_reservas(
    p_modelo_id INT,
    p_estado VARCHAR(20)
)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_total INT DEFAULT 0;
    SELECT COUNT(*)
      INTO v_total
      FROM reservas
     WHERE modelo_id = p_modelo_id
       AND (p_estado IS NULL OR estado = p_estado);
    RETURN v_total;
END$$

DELIMITER ;

SELECT 'functions: 3 funciones creadas' AS resultado;

SELECT ROUTINE_NAME, ROUTINE_TYPE
FROM information_schema.ROUTINES
WHERE ROUTINE_SCHEMA = DATABASE()
  AND ROUTINE_TYPE = 'FUNCTION'
ORDER BY ROUTINE_NAME;
