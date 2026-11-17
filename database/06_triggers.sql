-- ============================================================
--  TallerDB — Triggers de auditoría (Tema 3)
--  Archivo: database/06_triggers.sql
--  Motor: MariaDB 11+
--  Requiere: database/08_stock_reservas.sql (tablas de auditoría)
--  Uso:
--    mariadb -h 127.0.0.1 -u "$MARIADB_USER" tallerdb \
--      < database/06_triggers.sql
--  Rollback: database/06_triggers_rollback.sql
-- ============================================================

USE tallerdb;

DROP TRIGGER IF EXISTS trg_modelos_auditoria_ai;
DROP TRIGGER IF EXISTS trg_modelos_auditoria_au;
DROP TRIGGER IF EXISTS trg_modelos_auditoria_ad;
DROP TRIGGER IF EXISTS trg_reservas_auditoria_ai;
DROP TRIGGER IF EXISTS trg_reservas_auditoria_au;

DELIMITER $$

-- 1. Auditoría de altas de modelos.
CREATE TRIGGER trg_modelos_auditoria_ai
AFTER INSERT ON modelos
FOR EACH ROW
BEGIN
    INSERT INTO auditoria_modelos (
        modelo_id, accion, precio_anterior, precio_nuevo,
        stock_anterior, stock_nuevo, usuario_bd
    ) VALUES (
        NEW.id, 'INSERT', NULL, NEW.precio,
        NULL, NEW.stock, CURRENT_USER()
    );
END$$

-- 2. Auditoría de cambios de precio, stock o disponibilidad.
CREATE TRIGGER trg_modelos_auditoria_au
AFTER UPDATE ON modelos
FOR EACH ROW
BEGIN
    IF OLD.precio <> NEW.precio
       OR OLD.stock <> NEW.stock
       OR OLD.disponible <> NEW.disponible THEN
        INSERT INTO auditoria_modelos (
            modelo_id, accion, precio_anterior, precio_nuevo,
            stock_anterior, stock_nuevo, usuario_bd
        ) VALUES (
            NEW.id, 'UPDATE', OLD.precio, NEW.precio,
            OLD.stock, NEW.stock, CURRENT_USER()
        );
    END IF;
END$$

-- 3. Auditoría de bajas de modelos.
CREATE TRIGGER trg_modelos_auditoria_ad
AFTER DELETE ON modelos
FOR EACH ROW
BEGIN
    INSERT INTO auditoria_modelos (
        modelo_id, accion, precio_anterior, precio_nuevo,
        stock_anterior, stock_nuevo, usuario_bd
    ) VALUES (
        OLD.id, 'DELETE', OLD.precio, NULL,
        OLD.stock, NULL, CURRENT_USER()
    );
END$$

-- 4. Auditoría de creación de reservas.
CREATE TRIGGER trg_reservas_auditoria_ai
AFTER INSERT ON reservas
FOR EACH ROW
BEGIN
    INSERT INTO auditoria_reservas (
        reserva_id, accion, estado_anterior, estado_nuevo,
        cantidad, usuario_bd
    ) VALUES (
        NEW.id, 'CREADA', NULL, NEW.estado,
        NEW.cantidad, CURRENT_USER()
    );
END$$

-- 5. Auditoría de cambios de estado de una reserva.
CREATE TRIGGER trg_reservas_auditoria_au
AFTER UPDATE ON reservas
FOR EACH ROW
BEGIN
    IF OLD.estado <> NEW.estado THEN
        INSERT INTO auditoria_reservas (
            reserva_id, accion, estado_anterior, estado_nuevo,
            cantidad, usuario_bd
        ) VALUES (
            NEW.id, 'ESTADO_CAMBIADO', OLD.estado, NEW.estado,
            NEW.cantidad, CURRENT_USER()
        );
    END IF;
END$$

DELIMITER ;

SELECT 'triggers: 5 triggers creados' AS resultado;

SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE, ACTION_TIMING
FROM information_schema.TRIGGERS
WHERE TRIGGER_SCHEMA = DATABASE()
ORDER BY EVENT_OBJECT_TABLE, ACTION_TIMING, EVENT_MANIPULATION;
