-- ============================================================
--  TallerDB — Procedimientos almacenados (Tema 3 / Tema 4)
--  Archivo: database/04_procedures.sql
--  Motor: MariaDB 11+
--  Descripción:
--    Encapsula operaciones de negocio sobre modelos y reservas.
--    Los procedimientos NO hacen COMMIT: la transacción la controla
--    el llamador, para poder demostrar aislamiento y rollback.
--  Uso:
--    mariadb -h 127.0.0.1 -u "$MARIADB_USER" tallerdb \
--      < database/04_procedures.sql
--  Rollback: database/04_procedures_rollback.sql
-- ============================================================

USE tallerdb;

DROP PROCEDURE IF EXISTS sp_crear_modelo;
DROP PROCEDURE IF EXISTS sp_actualizar_precio;
DROP PROCEDURE IF EXISTS sp_reservar_modelo;
DROP PROCEDURE IF EXISTS sp_cancelar_reserva;

DELIMITER $$

-- 1. Alta de modelo con validación de precio, año y stock.
CREATE PROCEDURE sp_crear_modelo(
    IN  p_marca VARCHAR(100),
    IN  p_nombre VARCHAR(120),
    IN  p_anio INT,
    IN  p_precio DECIMAL(12,2),
    IN  p_tipo VARCHAR(40),
    IN  p_transmision VARCHAR(30),
    IN  p_stock INT,
    OUT p_id INT
)
BEGIN
    DECLARE EXIT HANDLER FOR 1062
    BEGIN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Ya existe un modelo con esa marca, nombre y año';
    END;

    IF p_precio < 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El precio no puede ser negativo';
    END IF;
    IF p_stock < 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El stock no puede ser negativo';
    END IF;
    IF p_anio < 1900 OR p_anio > 2100 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El año debe estar entre 1900 y 2100';
    END IF;

    INSERT INTO modelos (
        marca, nombre, anio, precio, tipo, transmision, disponible, stock
    ) VALUES (
        p_marca,
        p_nombre,
        p_anio,
        p_precio,
        COALESCE(p_tipo, 'sedan'),
        COALESCE(p_transmision, 'manual'),
        IF(p_stock > 0, 1, 0),
        p_stock
    );

    SET p_id = LAST_INSERT_ID();
END$$

-- 2. Actualización controlada de precio.
CREATE PROCEDURE sp_actualizar_precio(
    IN p_id INT,
    IN p_precio DECIMAL(12,2)
)
BEGIN
    DECLARE v_exists INT DEFAULT 0;

    IF p_precio < 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El precio no puede ser negativo';
    END IF;

    SELECT COUNT(*) INTO v_exists FROM modelos WHERE id = p_id;
    IF v_exists = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Modelo no encontrado';
    END IF;

    UPDATE modelos SET precio = p_precio WHERE id = p_id;
END$$

-- 3. Reserva con bloqueo pesimista.
--    SELECT ... FOR UPDATE serializa las reservas del mismo modelo.
--    Si el stock no alcanza, SIGNAL revierte la operación en el llamador.
CREATE PROCEDURE sp_reservar_modelo(
    IN  p_modelo_id INT,
    IN  p_usuario_id INT,
    IN  p_cantidad INT,
    OUT p_reserva_id INT
)
BEGIN
    DECLARE v_stock INT DEFAULT NULL;

    DECLARE EXIT HANDLER FOR 1452
    BEGIN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Usuario o modelo inexistente (FK)';
    END;

    IF p_cantidad <= 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'La cantidad debe ser mayor que cero';
    END IF;

    SELECT stock
      INTO v_stock
      FROM modelos
     WHERE id = p_modelo_id
       FOR UPDATE;

    IF v_stock IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Modelo no encontrado';
    END IF;
    IF v_stock < p_cantidad THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Stock insuficiente';
    END IF;

    UPDATE modelos
       SET stock = stock - p_cantidad
     WHERE id = p_modelo_id;

    INSERT INTO reservas (modelo_id, usuario_id, cantidad, estado)
    VALUES (p_modelo_id, p_usuario_id, p_cantidad, 'confirmada');

    SET p_reserva_id = LAST_INSERT_ID();
END$$

-- 4. Cancelación de reserva y devolución de stock.
CREATE PROCEDURE sp_cancelar_reserva(IN p_reserva_id INT)
BEGIN
    DECLARE v_modelo_id INT DEFAULT NULL;
    DECLARE v_cantidad INT DEFAULT NULL;
    DECLARE v_estado VARCHAR(20) DEFAULT NULL;

    SELECT modelo_id, cantidad, estado
      INTO v_modelo_id, v_cantidad, v_estado
      FROM reservas
     WHERE id = p_reserva_id
       FOR UPDATE;

    IF v_modelo_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Reserva no encontrada';
    END IF;
    IF v_estado = 'cancelada' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'La reserva ya está cancelada';
    END IF;

    UPDATE reservas SET estado = 'cancelada' WHERE id = p_reserva_id;
    UPDATE modelos SET stock = stock + v_cantidad WHERE id = v_modelo_id;
END$$

DELIMITER ;

SELECT 'procedures: 4 procedimientos creados' AS resultado;

SELECT ROUTINE_NAME, ROUTINE_TYPE
FROM information_schema.ROUTINES
WHERE ROUTINE_SCHEMA = DATABASE()
  AND ROUTINE_TYPE = 'PROCEDURE'
ORDER BY ROUTINE_NAME;
