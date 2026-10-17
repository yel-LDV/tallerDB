-- ============================================================
--  TallerDB — Pruebas de operaciones CRUD sobre `modelos`
--  Archivo: database/pruebas_crud.sql
--  Descripción: script de pruebas de inserción, consulta,
--               actualización y borrado sobre la tabla `modelos`.
--  Nota: se ejecuta dentro de una transacción y se revierte al
--        final, por lo que NO modifica los datos reales.
--  Nota: incluye una prueba negativa (violación de UNIQUE) a
--        propósito; por eso se debe ejecutar con la opción --force
--        para que el cliente continúe tras ese error esperado.
--  Uso: mariadb -u taller -ptallerpass --force tallerdb < database/pruebas_crud.sql
-- ============================================================

USE tallerdb;

-- Se usa una transacción para poder hacer ROLLBACK y no dejar
-- residuos de las pruebas.
START TRANSACTION;

SELECT '=========== ESTADO INICIAL ===========' AS prueba;

SELECT COUNT(*) AS total_modelos FROM modelos;


-- ------------------------------------------------------------
-- PRUEBA 1: INSERCIÓN (CREATE)
-- ------------------------------------------------------------
SELECT '=========== PRUEBA 1: INSERCIÓN ===========' AS prueba;

INSERT INTO modelos
    (marca, nombre, anio, precio, color, tipo, transmision, disponible, descripcion)
VALUES
    ('Prueba', 'Test Coupé', 2026, 55000.00, 'Rojo', 'coupe', 'manual', 1, 'Modelo creado por el script de pruebas.');

-- Verificación: el modelo insertado debe aparecer (id asignado por AUTO_INCREMENT)
SELECT id, marca, nombre, anio, precio, disponible
FROM modelos
WHERE marca = 'Prueba' AND nombre = 'Test Coupé';

-- Prueba de restricción UNIQUE (debe fallar: misma marca+nombre+año)
-- MariaDB debe responder con error 1062 y el script continuará en modo --force
INSERT INTO modelos (marca, nombre, anio, precio)
VALUES ('Prueba', 'Test Coupé', 2026, 100.00);
-- Esperado: ERROR 1062 (23000): Duplicate entry 'Prueba-Test Coupé-2026' ...


-- ------------------------------------------------------------
-- PRUEBA 2: CONSULTA / LECTURA (READ)
-- ------------------------------------------------------------
SELECT '=========== PRUEBA 2: CONSULTAS ===========' AS prueba;

-- 2.1 Selección con filtro por marca
SELECT marca, nombre, anio, precio
FROM modelos
WHERE marca = 'Toyota'
ORDER BY anio DESC;

-- 2.2 Búsqueda parcial (LIKE) + filtro de disponibilidad
SELECT marca, nombre, anio, disponible
FROM modelos
WHERE (nombre LIKE '%Coroll%' OR descripcion LIKE '%Coroll%')
  AND disponible = 1;

-- 2.3 Rango de años + ordenamiento por precio
SELECT marca, nombre, anio, precio
FROM modelos
WHERE anio BETWEEN 2024 AND 2025
ORDER BY precio ASC
LIMIT 5;

-- 2.4 Agregados: total, promedio, mín y máx
SELECT COUNT(*)               AS total,
       ROUND(AVG(precio), 2)  AS precio_promedio,
       MIN(precio)            AS precio_min,
       MAX(precio)            AS precio_max
FROM modelos;

-- 2.5 Conteo por tipo de carrocería (GROUP BY)
SELECT tipo, COUNT(*) AS cantidad
FROM modelos
GROUP BY tipo
ORDER BY cantidad DESC;


-- ------------------------------------------------------------
-- PRUEBA 3: ACTUALIZACIÓN (UPDATE)
-- ------------------------------------------------------------
SELECT '=========== PRUEBA 3: ACTUALIZACIÓN ===========' AS prueba;

-- Se guarda el precio anterior para comparar
SELECT nombre, precio AS precio_antes
FROM modelos
WHERE marca = 'Prueba' AND nombre = 'Test Coupé';

-- 3.1 Actualización simple de precio y disponibilidad
UPDATE modelos
SET precio = 49999.99,
    disponible = 0,
    descripcion = 'Precio actualizado por el script de pruebas.'
WHERE marca = 'Prueba' AND nombre = 'Test Coupé';

-- Verificación del cambio
SELECT nombre, precio AS precio_despues, disponible, descripcion
FROM modelos
WHERE marca = 'Prueba' AND nombre = 'Test Coupé';

-- 3.2 Actualización masiva con filtro (subida del 5% a todos los SUV)
UPDATE modelos
SET precio = ROUND(precio * 1.05, 2)
WHERE tipo = 'suv';

-- Verificación de la actualización masiva
SELECT marca, nombre, tipo, precio
FROM modelos
WHERE tipo = 'suv'
ORDER BY precio DESC;


-- ------------------------------------------------------------
-- PRUEBA 4: BORRADO (DELETE)
-- ------------------------------------------------------------
SELECT '=========== PRUEBA 4: BORRADO ===========' AS prueba;

-- Borrado específico por condiciones exactas
DELETE FROM modelos
WHERE marca = 'Prueba' AND nombre = 'Test Coupé';

-- Verificación: NO debe devolver filas
SELECT COUNT(*) AS filas_restantes_del_modelo_prueba
FROM modelos
WHERE marca = 'Prueba' AND nombre = 'Test Coupé';

-- Borrado de un modelo por id (se usa un id inexistente a modo de
-- prueba negativa: DELETE con id = 0 no debe afectar filas)
DELETE FROM modelos WHERE id = 0;
SELECT ROW_COUNT() AS filas_afectadas_por_id_inexistente;


-- ------------------------------------------------------------
-- ESTADO FINAL
-- ------------------------------------------------------------
SELECT '=========== ESTADO FINAL (antes del ROLLBACK) ===========' AS prueba;

SELECT COUNT(*) AS total_modelos_final FROM modelos;


-- Se revierte TODO lo hecho en este script para no alterar los datos.
ROLLBACK;

SELECT '=========== ROLLBACK EJECUTADO (datos intactos) ===========' AS prueba;

SELECT COUNT(*) AS total_modelos_final_real FROM modelos;
