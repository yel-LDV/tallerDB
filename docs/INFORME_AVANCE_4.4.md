# Informe de Avance de Proyecto — Actividad 4.4

**Proyecto:** TallerDB — Catálogo de Autos  
**Asignatura:** Bases de Datos  
**Actividad:** 4.4 — Informe de Avance de Proyecto (Temas 1, 2, 3 y 4)  
**Fecha:** 4 de noviembre de 2026  
**Integrante:** _(completar)_  
**Docente:** _(completar)_  
**Institución / grupo:** _(completar)_  
**Repositorio:** `/home/angedl_/Proyectos/tallerDB`

> **Nota metodológica.** El repositorio no contenía un temario formal de los
> Temas 1–3. La asignación usada en este informe es **tentativa** y se marca
> como `SUPUESTO`:
>
> - **Tema 1:** análisis de requerimientos y modelo conceptual (ER).
> - **Tema 2:** diseño lógico/físico, normalización y DDL.
> - **Tema 3:** SQL avanzado (índices, vistas, procedimientos, funciones,
>   triggers, roles/permisos).
> - **Tema 4:** nuevas funcionalidades de base de datos y transacciones con
>   niveles de aislamiento.
>
> Cada dato se etiqueta como `EXISTE`, `INFERIDO`, `PROPUESTO` o
> `NO ENCONTRADO`. Las salidas de SQL y de pruebas son **reales**, ejecutadas
> contra la instancia local de MariaDB; se indica cuando algo es solo esperado.

---

## 1. Introducción y objetivos

### 1.1 Problema

Un taller o concesionario necesita publicar su catálogo de autos, permitir que
los clientes consulten disponibilidad y precio, y reservar unidades sin vender
dos veces el mismo auto. La aplicación ya resolvía autenticación, administración
de usuarios, catálogo, filtros y visor 3D; el hueco era el **inventario** y las
**reservas**. `INFERIDO` de `README.md`, `app/` y `docs/INFORME_EVIDENCIA.md`.

### 1.2 Objetivo general

Implementar y documentar una base de datos relacional en MariaDB para el
catálogo TallerDB, con control de stock, reservas, objetos SQL avanzados y
transacciones que eviten la sobreventa y las actualizaciones perdidas.
`PROPUESTO`.

### 1.3 Objetivos específicos

1. Reconstruir los requerimientos y el modelo conceptual. `PROPUESTO`.
2. Documentar el modelo lógico/físico y la normalización. `PROPUESTO`.
3. Implementar el DDL con `users`, `modelos`, `reservas` y auditoría.
   `EXISTE` para las dos primeras; `PROPUESTO` para las demás.
4. Implementar vistas, funciones, procedimientos, triggers e índices.
   `PROPUESTO`.
5. Demostrar `READ COMMITTED` y `SERIALIZABLE` con dos terminales.
   `PROPUESTO`.
6. Verificar con `testdb`, `pytest` y scripts SQL reproducibles. `EXISTE` para
   las dos primeras; `PROPUESTO` para las demos.

---

## 2. Resumen de los Temas 1–3

### 2.1 Tema 1 — Requerimientos y modelo conceptual `SUPUESTO`

**Qué existe:** `README.md` describe el problema, las características y el
stack; `docs/INFORME_EVIDENCIA.md` contiene introducción, interfaces y alcance.
No había un documento formal de requerimientos ni un diagrama ER.
`NO ENCONTRADO`.

**Qué se completó en esta entrega:**

- `docs/REQUERIMIENTOS.md`: problema, objetivo general, objetivos específicos,
  alcance, actores, 13 requisitos funcionales, 8 no funcionales, 5 casos de uso
  y trazabilidad.
- `docs/MODELO_DATOS.md`: diagrama ER en Mermaid, modelo relacional,
  normalización 1NF/2NF/3NF, diccionario de datos e índices.

**Artefactos:**

| Artefacto | Ruta | Etiqueta |
|---|---|---|
| Requerimientos reconstruidos | `docs/REQUERIMIENTOS.md` | `PROPUESTO` |
| Modelo conceptual/ER | `docs/MODELO_DATOS.md` | `PROPUESTO` |
| Descripción inicial del proyecto | `README.md` | `EXISTE` |
| Informe de evidencia previo | `docs/INFORME_EVIDENCIA.md` | `EXISTE` |

[IMAGEN 1: diagrama ER renderizado desde el bloque Mermaid de `docs/MODELO_DATOS.md`]

### 2.2 Tema 2 — Diseño lógico/físico, normalización y DDL `SUPUESTO`

**Qué existe:** DDL para MariaDB/MySQL y PostgreSQL, ORM SQLAlchemy, semilla de
18 modelos y script de pruebas CRUD.

| Artefacto | Ruta | Etiqueta |
|---|---|---|
| DDL MariaDB | `database/schema_mariadb.sql` | `EXISTE` |
| DDL MariaDB para Docker | `database/init/01_schema.sql` | `EXISTE` |
| DDL PostgreSQL | `database/schema_postgresql.sql` | `EXISTE` |
| DDL PostgreSQL para Docker | `database/init_postgres/01_schema.sql` | `EXISTE` |
| Semilla | `database/seed_modelos.sql` | `EXISTE` (18 filas) |
| ORM `User` / `Modelo` | `app/models/user.py`, `app/models/modelo.py` | `EXISTE` |
| Pruebas CRUD | `database/pruebas_crud.sql` | `EXISTE` |

**Normalización:** las tablas base están en 3NF para el alcance actual. La
columna `marca` es texto; si se agregaran atributos de marca, correspondería una
tabla `marcas`. `disponible` es una bandera de exhibición derivable de
`stock > 0`, pero se conserva por compatibilidad con la UI. El análisis completo
está en `docs/MODELO_DATOS.md`.

**DDL físico consolidado de `modelos`** (incluye las columnas 3D y `stock`;
`stock` se agrega con `database/08_stock_reservas.sql`):

```sql
CREATE TABLE modelos (
    id          INT            AUTO_INCREMENT PRIMARY KEY,
    marca       VARCHAR(100)   NOT NULL,
    nombre      VARCHAR(120)   NOT NULL,
    anio        INT            NOT NULL,
    precio      DECIMAL(12,2)  NOT NULL,
    color       VARCHAR(50)    NULL,
    tipo        VARCHAR(40)    NOT NULL DEFAULT 'sedan',
    transmision VARCHAR(30)    NOT NULL DEFAULT 'manual',
    disponible  BOOLEAN        NOT NULL DEFAULT 1,
    stock       INT            NOT NULL DEFAULT 1,
    descripcion TEXT           NULL,
    imagen_url  VARCHAR(500)   NULL,
    modelo_3d_key        VARCHAR(255) NULL,
    modelo_3d_url        VARCHAR(500) NULL,
    modelo_3d_formato    VARCHAR(10)  NULL,
    modelo_3d_tamano     INT          NULL,
    modelo_3d_subido_at  DATETIME     NULL,
    created_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_modelo_marca_nombre_anio (marca, nombre, anio),
    KEY ix_modelos_marca  (marca),
    KEY ix_modelos_nombre (nombre),
    CONSTRAINT chk_modelos_precio CHECK (precio >= 0),
    CONSTRAINT chk_modelos_stock  CHECK (stock >= 0)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
```

**DDL de `users`:**

```sql
CREATE TABLE users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT 1,
    is_admin        BOOLEAN      NOT NULL DEFAULT 0,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY ix_users_email (email)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
```

**DDL de `reservas`:**

```sql
CREATE TABLE reservas (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    modelo_id   INT NOT NULL,
    usuario_id  INT NOT NULL,
    cantidad    INT NOT NULL DEFAULT 1,
    estado      ENUM('pendiente', 'confirmada', 'cancelada')
                NOT NULL DEFAULT 'pendiente',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_reservas_modelo
        FOREIGN KEY (modelo_id) REFERENCES modelos (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_reservas_usuario
        FOREIGN KEY (usuario_id) REFERENCES users (id)
        ON DELETE CASCADE,
    CONSTRAINT chk_reservas_cantidad CHECK (cantidad > 0),
    KEY ix_reservas_modelo_estado (modelo_id, estado),
    KEY ix_reservas_usuario (usuario_id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
```

**Verificación real del esquema:**

```sql
SHOW COLUMNS FROM modelos LIKE 'stock';
```

```text
Field   Type      Null  Key  Default  Extra
stock   int(11)   NO        1
```

```sql
SHOW TABLES;
```

```text
Tables_in_tallerdb
auditoria_modelos
auditoria_reservas
modelos
reservas
users
```

### 2.3 Tema 3 — SQL avanzado `SUPUESTO`

**Qué existía:** consultas con filtros y agregados en `app/modelos/router.py`,
índices `ix_modelos_marca` e `ix_modelos_nombre`, restricciones `UNIQUE`,
CRUD completo y transacciones mínimas en `database/pruebas_crud.sql` y
`app/main.py` (`testdb`). `EXISTE`.

**Qué faltaba:** vistas, procedimientos, funciones, triggers, roles/permisos
granulares y demos de aislamiento. `NO ENCONTRADO`.

**Qué se implementó:** cinco vistas, tres funciones, cuatro procedimientos,
cinco triggers, siete índices y dos demos de transacciones. `PROPUESTO` y
verificado.

| Objeto | Archivo | Cantidad |
|---|---|---|
| Vistas | `database/03_views.sql` | 5 |
| Funciones | `database/05_functions.sql` | 3 |
| Procedimientos | `database/04_procedures.sql` | 4 |
| Triggers | `database/06_triggers.sql` | 5 |
| Índices | `database/09_indexes.sql` | 7 |

**Roles/permisos:** el estado actual es `CREATE USER` + `GRANT ALL PRIVILEGES`
sobre `tallerdb` en `startdb.sh`. No se implementaron roles granulares en esta
entrega (P7 quedó fuera del alcance autorizado). `EXISTE` parcial;
`NO ENCONTRADO` para mínimo privilegio.

---

## 3. Tema 4 — Nuevas funcionalidades de base de datos

### 3.1 Inventario y reservas

**Objetivo:** agregar stock real por modelo y reservas con integridad
referencial, sin modificar `app/`.

**Tablas/objetos:** `modelos.stock`, `reservas`, `auditoria_modelos`,
`auditoria_reservas`, `chk_modelos_stock`, `chk_modelos_precio`,
`chk_reservas_cantidad`, `fk_reservas_modelo`, `fk_reservas_usuario`.

**Script:** `database/08_stock_reservas.sql` (rollback en
`database/08_stock_reservas_rollback.sql`).

**Código completo:** ver sección 2.2 y el archivo citado. El script es
idempotente: usa `ADD COLUMN IF NOT EXISTS` y consulta `information_schema`
antes de crear las restricciones `CHECK`.

**Cómo probarlo:**

```sql
-- Restricción de stock negativo (debe fallar)
UPDATE modelos SET stock = -1 WHERE id = 1;
-- ERROR 4025: CONSTRAINT `chk_modelos_stock` failed

-- Restricción UNIQUE (debe fallar)
INSERT INTO modelos (marca, nombre, anio, precio, tipo, transmision, disponible, stock)
VALUES ('Toyota','Corolla',2024,28900.00,'sedan','manual',1,5);
-- ERROR 1062: Duplicate entry 'Toyota-Corolla-2024'
```

**Resultado real:**

```text
ERROR 4025 (23000): CONSTRAINT `chk_modelos_stock` failed for `tallerdb`.`modelos`
ERROR 1062 (23000): Duplicate entry 'Toyota-Corolla-2024' for key 'uq_modelo_marca_nombre_anio'
```

### 3.2 Vistas

**Objetivo:** encapsular consultas de catálogo, estadísticas, reservas activas y
stock bajo.

**Script:** `database/03_views.sql` (rollback en `database/03_views_rollback.sql`).

**Código completo:**

```sql
CREATE OR REPLACE VIEW vw_modelos_disponibles AS
SELECT id, marca, nombre, anio, precio, stock, tipo, transmision
FROM modelos
WHERE disponible = 1 AND stock > 0;

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

CREATE OR REPLACE VIEW vw_resumen_tipos AS
SELECT
    tipo,
    COUNT(*) AS cantidad,
    SUM(CASE WHEN disponible = 1 AND stock > 0 THEN 1 ELSE 0 END) AS disponibles,
    ROUND(AVG(precio), 2) AS precio_promedio,
    SUM(stock) AS stock_total
FROM modelos
GROUP BY tipo;

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

CREATE OR REPLACE VIEW vw_modelos_bajo_stock AS
SELECT id, marca, nombre, anio, stock, disponible
FROM modelos
WHERE stock <= 2
ORDER BY stock ASC, marca ASC;
```

**Ejemplo real:**

```sql
SELECT * FROM vw_estadisticas_marca ORDER BY stock_total DESC LIMIT 5;
```

```text
marca       total_modelos  disponibles  stock_total  precio_promedio  precio_min  precio_max
Toyota      3              3            15           37100.00         28900.00    52500.00
Honda       2              2            10           33700.00         31500.00    35900.00
Volkswagen  2              2            10           35800.00         33400.00    38200.00
Kia         2              2            10           35350.00         22900.00    47800.00
Nissan      1              1            5            21500.00         21500.00    21500.00
```

```sql
SELECT * FROM vw_reservas_activas;
```

```text
reserva_id  marca    nombre              anio  email                    cantidad  estado
6           __TX__   Demo Transacciones  2026  __tx__@example.invalid   2         confirmada
```

[IMAGEN 2: resultado de `SELECT * FROM vw_estadisticas_marca ORDER BY stock_total DESC LIMIT 5;`]

### 3.3 Funciones

**Objetivo:** reutilizar cálculos de precio con impuesto, stock y reservas.

**Script:** `database/05_functions.sql` (rollback en
`database/05_functions_rollback.sql`).

> Los scripts de funciones, procedimientos y triggers usan `DELIMITER $$` para
> el cliente `mariadb`; en el informe se omite el delimitador por claridad.

**Código completo:**

```sql
CREATE FUNCTION fn_precio_con_impuesto(
    p_precio DECIMAL(12,2),
    p_tasa DECIMAL(5,2)
)
RETURNS DECIMAL(12,2)
DETERMINISTIC
BEGIN
    RETURN ROUND(p_precio * (1 + p_tasa / 100), 2);
END;

CREATE FUNCTION fn_stock_disponible(p_modelo_id INT)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_stock INT DEFAULT 0;
    SELECT COALESCE(stock, 0) INTO v_stock
      FROM modelos WHERE id = p_modelo_id;
    RETURN COALESCE(v_stock, 0);
END;

CREATE FUNCTION fn_total_reservas(
    p_modelo_id INT,
    p_estado VARCHAR(20)
)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_total INT DEFAULT 0;
    SELECT COUNT(*) INTO v_total
      FROM reservas
     WHERE modelo_id = p_modelo_id
       AND (p_estado IS NULL OR estado = p_estado);
    RETURN v_total;
END;
```

**Ejemplo real:**

```sql
SELECT fn_precio_con_impuesto(10000.00, 16.00) AS precio_con_iva,
       fn_stock_disponible(1) AS stock_modelo_1,
       fn_total_reservas(1, 'confirmada') AS reservas_modelo_1;
```

```text
precio_con_iva  stock_modelo_1  reservas_modelo_1
11600.00        5               0
```

### 3.4 Procedimientos almacenados

**Objetivo:** encapsular alta de modelos, cambio de precio, reserva y
cancelación. Los procedimientos **no** hacen `COMMIT`; la transacción la
controla el llamador.

**Script:** `database/04_procedures.sql` (rollback en
`database/04_procedures_rollback.sql`).

**Código completo:**

```sql
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
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El precio no puede ser negativo';
    END IF;
    IF p_stock < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El stock no puede ser negativo';
    END IF;
    IF p_anio < 1900 OR p_anio > 2100 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El año debe estar entre 1900 y 2100';
    END IF;

    INSERT INTO modelos (
        marca, nombre, anio, precio, tipo, transmision, disponible, stock
    ) VALUES (
        p_marca, p_nombre, p_anio, p_precio,
        COALESCE(p_tipo, 'sedan'), COALESCE(p_transmision, 'manual'),
        IF(p_stock > 0, 1, 0), p_stock
    );
    SET p_id = LAST_INSERT_ID();
END;

CREATE PROCEDURE sp_actualizar_precio(
    IN p_id INT,
    IN p_precio DECIMAL(12,2)
)
BEGIN
    DECLARE v_exists INT DEFAULT 0;
    IF p_precio < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El precio no puede ser negativo';
    END IF;
    SELECT COUNT(*) INTO v_exists FROM modelos WHERE id = p_id;
    IF v_exists = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Modelo no encontrado';
    END IF;
    UPDATE modelos SET precio = p_precio WHERE id = p_id;
END;

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
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La cantidad debe ser mayor que cero';
    END IF;

    SELECT stock INTO v_stock
      FROM modelos
     WHERE id = p_modelo_id
       FOR UPDATE;

    IF v_stock IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Modelo no encontrado';
    END IF;
    IF v_stock < p_cantidad THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Stock insuficiente';
    END IF;

    UPDATE modelos SET stock = stock - p_cantidad WHERE id = p_modelo_id;
    INSERT INTO reservas (modelo_id, usuario_id, cantidad, estado)
    VALUES (p_modelo_id, p_usuario_id, p_cantidad, 'confirmada');
    SET p_reserva_id = LAST_INSERT_ID();
END;

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
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Reserva no encontrada';
    END IF;
    IF v_estado = 'cancelada' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La reserva ya está cancelada';
    END IF;

    UPDATE reservas SET estado = 'cancelada' WHERE id = p_reserva_id;
    UPDATE modelos SET stock = stock + v_cantidad WHERE id = v_modelo_id;
END;
```

**Prueba real de ciclo completo:**

```sql
CALL sp_crear_modelo('__SP__','Demo Procedimiento',2026,20000.00,'sedan','manual',3,@mid);
CALL sp_actualizar_precio(@mid, 21000.00);
CALL sp_reservar_modelo(@mid, @uid, 2, @rid);
CALL sp_cancelar_reserva(@rid);
```

```text
sp_crear_modelo        modelo_id=25  precio=20000.00  stock=3
sp_actualizar_precio                 precio=21000.00
sp_reservar_modelo     reserva_id=5  cantidad=2       estado=confirmada
stock tras reserva                   stock=1
sp_cancelar_reserva                  estado=cancelada
stock tras cancelación               stock=3
```

**Prueba de duplicado real:**

```text
CALL sp_crear_modelo('Toyota','Corolla',2024,28900.00,'sedan','manual',5,@id);
ERROR 1644 (45000): Ya existe un modelo con esa marca, nombre y año
```

### 3.5 Triggers

**Objetivo:** auditar cambios de precio, stock, disponibilidad y estado de
reservas sin depender de la aplicación.

**Script:** `database/06_triggers.sql` (rollback en
`database/06_triggers_rollback.sql`).

**Código completo:**

```sql
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
END;

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
END;

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
END;

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
END;

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
END;
```

**Ejemplo real de auditoría:**

```sql
SELECT id, modelo_id, accion, precio_anterior, precio_nuevo,
       stock_anterior, stock_nuevo, usuario_bd
FROM auditoria_modelos
WHERE modelo_id = 25
ORDER BY id;
```

```text
id  modelo_id  accion  precio_anterior  precio_nuevo  stock_anterior  stock_nuevo  usuario_bd
30  25         INSERT  NULL             20000.00      NULL            3            taller@127.0.0.1
31  25         UPDATE  20000.00         21000.00      3               3            taller@127.0.0.1
32  25         UPDATE  21000.00         21000.00      3               1            taller@127.0.0.1
33  25         UPDATE  21000.00         21000.00      1               3            taller@127.0.0.1
```

```sql
SELECT ar.id, ar.reserva_id, ar.accion, ar.estado_anterior,
       ar.estado_nuevo, ar.cantidad
FROM auditoria_reservas ar
JOIN reservas r ON r.id = ar.reserva_id
WHERE r.modelo_id = 25
ORDER BY ar.id;
```

```text
id  reserva_id  accion            estado_anterior  estado_nuevo  cantidad
5   5           CREADA            NULL             confirmada    2
6   5           ESTADO_CAMBIADO   confirmada       cancelada     2
```

[IMAGEN 3: consulta de `auditoria_modelos` y `auditoria_reservas` para el modelo de prueba]

### 3.6 Índices

**Objetivo:** acelerar filtros y ordenamientos del catálogo.

**Script:** `database/09_indexes.sql` (rollback en
`database/09_indexes_rollback.sql`).

**Índices creados:** `idx_modelos_tipo`, `idx_modelos_disponible`,
`idx_modelos_precio`, `idx_modelos_anio`, `idx_modelos_tipo_disponible`,
`idx_reservas_estado`, `idx_reservas_created_at`.

**Evidencia real con `EXPLAIN`:**

```sql
EXPLAIN SELECT id, marca, nombre, precio
FROM modelos
WHERE tipo = 'suv' AND disponible = 1;
```

```text
id  select_type  table    type  possible_keys
1   SIMPLE       modelos  ref   idx_modelos_tipo,idx_modelos_disponible,idx_modelos_tipo_disponible
key                  key_len  ref    rows  Extra
idx_modelos_tipo     162      const  5     Using index condition; Using where
```

```sql
EXPLAIN SELECT id, marca, nombre, precio
FROM modelos
ORDER BY precio DESC
LIMIT 10;
```

```text
id  select_type  table    type   possible_keys  key                key_len  ref   rows  Extra
1   SIMPLE       modelos  index  NULL           idx_modelos_precio  6        NULL  10
```

[IMAGEN 4: salida de `SHOW INDEX FROM modelos;` o de los dos `EXPLAIN`]

### 3.7 Cambios respecto al Tema 3

| Cambio | Antes (Tema 3) | Después (Tema 4) |
|---|---|---|
| Inventario | Solo `disponible` booleano | `stock INT` con `CHECK (stock >= 0)` |
| Relaciones | Sin FK | `reservas` con FK a `modelos` y `users` |
| Reservas | No existían | Tabla `reservas` con estados y cantidades |
| Auditoría | No existía | `auditoria_modelos`, `auditoria_reservas` y 5 triggers |
| Consultas | SQL embebido en el router | 5 vistas reutilizables |
| Lógica | En Python | 4 procedimientos + 3 funciones |
| Índices | 4 índices en `modelos` (`PRIMARY`, 1 `UNIQUE` y 2 `KEY`) | 9 en `modelos` (4 base + 5 nuevos) y 2 nuevos en `reservas` |
| Transacciones | `START TRANSACTION`/`ROLLBACK` en pruebas | Demos de aislamiento y bloqueo pesimista |

### 3.8 Otros avances de la aplicación

Estos avances son contexto; el eje del Tema 4 es la base de datos.

- **Modelos 3D GLB:** subida, reemplazo, borrado y visor con `model-viewer`.
  `EXISTE` en `app/modelos/storage.py`, `app/modelos/router.py` y
  `app/templates/modelos.html`.
- **Filtros y paginación:** búsqueda por marca/nombre/descripción/color/
  transmisión, filtros por tipo, disponibilidad y rango de años, ordenamiento y
  estadísticas. `EXISTE` en `app/modelos/router.py`.
- **Administración:** creación de usuarios, cambio de rol y activación/
  desactivación. `EXISTE` en `app/auth/router.py`.
- **Mi perfil y UI por roles:** cambios **sin commitear** en
  `app/templates/profile.html`, `app/auth/router.py`,
  `app/templates/dashboard.html`, `app/templates/modelos.html`,
  `tests/test_profile.py` y `tests/test_permisos_ui.py`.
- **Pruebas:** 83 casos ejecutados. `EXISTE`.

---

## 4. Transacciones con niveles de aislamiento

Los guiones completos están en `database/transacciones/`. Se ejecutaron con dos
terminales y el cliente `mariadb`. El modelo temporal `__TX__` se crea en
`00_setup.sql` y se elimina en `12_cleanup.sql`.

> Cada archivo de sesión define al inicio `@modelo_id` y, cuando hace falta,
> `@usuario_id`; en algunos fragmentos del informe se omiten esas dos líneas
> para no repetirlas. Los scripts completos están en el repositorio.

### 4.1 Demo 1 — READ COMMITTED

**Nivel elegido:** `READ COMMITTED`. **Por qué:** es el nivel habitual de
aplicaciones web con muchas lecturas; permite ver cambios ya confirmados por
otras sesiones, pero no lecturas sucias. Es el escenario natural de un catálogo
donde un administrador cambia un precio mientras un cliente lo consulta.

**Escenario de negocio:** un administrador actualiza el precio de un modelo
mientras un vendedor lo está cotizando. El vendedor lee 10 000, el administrador
confirma 12 000 y el vendedor vuelve a leer dentro de la misma transacción. La
segunda lectura ve 12 000: **lectura no repetible**. Luego se demuestra que
`SELECT ... FOR UPDATE` evita la **actualización perdida** cuando dos sesiones
suman importes al mismo precio.

#### 4.1.1 Preparación

```sql
-- database/transacciones/00_setup.sql
INSERT INTO users (email, hashed_password, is_active, is_admin)
VALUES ('__tx__@example.invalid', 'x', 1, 0)
ON DUPLICATE KEY UPDATE is_active = 1;

INSERT INTO modelos (
    marca, nombre, anio, precio, color, tipo, transmision,
    disponible, descripcion, stock
) VALUES (
    '__TX__', 'Demo Transacciones', 2026, 10000.00, 'Gris',
    'sedan', 'manual', 1, 'Modelo temporal para demos de transacciones', 5
)
ON DUPLICATE KEY UPDATE precio = 10000.00, stock = 5, disponible = 1;
```

Salida real:

```text
modelo_id  usuario_id  precio     stock  disponible
24         9           10000.00   5      1
```

#### 4.1.2 Lectura no repetible — Sesión A

```sql
-- database/transacciones/02_read_committed_sesion_a.sql
SET @modelo_id := (
    SELECT id FROM modelos
    WHERE marca = '__TX__' AND nombre = 'Demo Transacciones' AND anio = 2026
);

SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
START TRANSACTION;

SELECT 'A1: lectura inicial' AS paso, precio, stock
FROM modelos WHERE id = @modelo_id;

SELECT SLEEP(5) AS espera_para_sesion_b;

SELECT 'A2: segunda lectura (misma transacción)' AS paso, precio, stock
FROM modelos WHERE id = @modelo_id;

COMMIT;

SELECT 'A3: después del COMMIT' AS paso, precio, stock
FROM modelos WHERE id = @modelo_id;
```

#### 4.1.3 Lectura no repetible — Sesión B

```sql
-- database/transacciones/03_read_committed_sesion_b.sql
SET @modelo_id := (
    SELECT id FROM modelos
    WHERE marca = '__TX__' AND nombre = 'Demo Transacciones' AND anio = 2026
);

SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
START TRANSACTION;

UPDATE modelos SET precio = 12000.00 WHERE id = @modelo_id;

COMMIT;

SELECT 'B: actualización confirmada' AS paso, precio, stock
FROM modelos WHERE id = @modelo_id;
```

**Orden exacto:** Terminal 1 ejecuta A; dentro de los 5 segundos, Terminal 2
ejecuta B.

**Salida real — Sesión A:**

```text
paso                                       precio     stock
A1: lectura inicial                        10000.00   5
espera_para_sesion_b
0
paso                                       precio     stock
A2: segunda lectura (misma transacción)    12000.00   5
paso                                       precio     stock
A3: después del COMMIT                     12000.00   5
```

**Salida real — Sesión B:**

```text
paso                       precio     stock
B: actualización confirmada 12000.00   5
```

**Anomalía demostrada:** lectura no repetible. A leyó 10 000 y, sin cerrar su
transacción, volvió a leer 12 000 porque B confirmó el cambio. `READ COMMITTED`
lo permite. **No hay lectura sucia**, porque B solo se ve después del `COMMIT`.

#### 4.1.4 Actualización perdida evitada con `FOR UPDATE`

**Sesión A:**

```sql
-- database/transacciones/04_read_committed_lost_update_a.sql
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
START TRANSACTION;

SELECT 'A1: fila bloqueada' AS paso, precio
FROM modelos WHERE id = @modelo_id FOR UPDATE;

SELECT SLEEP(5) AS espera_para_sesion_b;

UPDATE modelos SET precio = precio + 500 WHERE id = @modelo_id;

COMMIT;

SELECT 'A2: después del COMMIT' AS paso, precio
FROM modelos WHERE id = @modelo_id;
```

**Sesión B:**

```sql
-- database/transacciones/05_read_committed_lost_update_b.sql
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
START TRANSACTION;

SELECT 'B1: esperando el bloqueo de A' AS paso, precio
FROM modelos WHERE id = @modelo_id FOR UPDATE;

UPDATE modelos SET precio = precio + 1000 WHERE id = @modelo_id;

COMMIT;

SELECT 'B2: después del COMMIT' AS paso, precio
FROM modelos WHERE id = @modelo_id;
```

**Salida real — Sesión A:**

```text
paso                 precio
A1: fila bloqueada   10000.00
espera_para_sesion_b
0
paso                 precio
A2: después del COMMIT 10500.00
```

**Salida real — Sesión B:**

```text
paso                              precio
B1: esperando el bloqueo de A     10500.00
paso                              precio
B2: después del COMMIT            11500.00
```

**Anomalía evitada:** actualización perdida. B no leyó el valor viejo (10 000)
mientras A trabajaba; quedó bloqueada hasta el `COMMIT` de A y luego leyó
10 500. El resultado final 11 500 conserva ambas operaciones. Sin `FOR UPDATE`,
ambas sesiones podrían leer 10 000 y la última escribiría 11 000, perdiendo el
+500 de A.

#### 4.1.5 Verificación y limpieza

```sql
-- database/transacciones/11_verify.sql
SELECT id, marca, nombre, anio, precio, stock, disponible
FROM modelos WHERE id = @modelo_id;

SELECT id, modelo_id, usuario_id, cantidad, estado, created_at
FROM reservas WHERE modelo_id = @modelo_id ORDER BY id;
```

```sql
-- database/transacciones/12_cleanup.sql
DELETE ar FROM auditoria_reservas ar
JOIN reservas r ON r.id = ar.reserva_id
WHERE r.modelo_id = @modelo_id;
DELETE FROM reservas WHERE modelo_id = @modelo_id;
DELETE FROM modelos WHERE id = @modelo_id;
DELETE FROM auditoria_modelos WHERE modelo_id = @modelo_id;
DELETE FROM users WHERE email = '__tx__@example.invalid';
```

### 4.2 Demo 2 — SERIALIZABLE

**Nivel elegido:** `SERIALIZABLE`. **Por qué:** es el nivel más estricto de
MariaDB; convierte los `SELECT` normales en lecturas con bloqueo de rango
(next-key). Sirve para demostrar que una fila insertada por otra sesión no
aparece “por arte de magia” dentro de una transacción, y que dos reservas
concurrentes no pueden sobrevender la última unidad.

**Escenario de negocio:** dos clientes intentan reservar el último auto. Además,
un reporte cuenta reservas confirmadas mientras otro cliente inserta una nueva.
Con `SERIALIZABLE`, el conteo no cambia dentro de la transacción y la segunda
reserva no puede confirmarse si ya no hay stock.

#### 4.2.1 Preparación

```sql
-- database/transacciones/06_serializable_reset.sql
DELETE FROM reservas WHERE modelo_id = @modelo_id;
UPDATE modelos SET precio = 10000.00, stock = 1, disponible = 1
WHERE id = @modelo_id;
```

**Salida real:**

```text
paso                            precio     stock  disponible
SERIALIZABLE: estado inicial    10000.00   1      1
reservas_confirmadas
0
```

#### 4.2.2 Lectura fantasma — Sesión A

```sql
-- database/transacciones/07_serializable_phantom_a.sql
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
```

#### 4.2.3 Lectura fantasma — Sesión B

```sql
-- database/transacciones/08_serializable_phantom_b.sql
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
START TRANSACTION;

INSERT INTO reservas (modelo_id, usuario_id, cantidad, estado)
VALUES (@modelo_id, @usuario_id, 1, 'confirmada');

COMMIT;

SELECT 'B: inserción confirmada' AS paso, COUNT(*) AS reservas_confirmadas
FROM reservas
WHERE modelo_id = @modelo_id AND estado = 'confirmada';
```

**Salida real — Sesión A:**

```text
paso                                     reservas_confirmadas
A1: conteo inicial                       0
espera_para_sesion_b
0
paso                                     reservas_confirmadas
A2: conteo final (misma transacción)     0
paso                                     reservas_confirmadas
A3: después del COMMIT                   0
```

**Salida real — Sesión B:**

```text
paso                       reservas_confirmadas
B: inserción confirmada    1
```

B esperó **4 041 ms** (medido con `date +%s%3N`) antes de poder insertar. A no
vio la fila fantasma: su segundo conteo siguió en 0. `SERIALIZABLE` evita la
lectura fantasma a costa de bloquear la inserción.

#### 4.2.4 Sobreventa — Sesión A

```sql
-- database/transacciones/09_serializable_overselling_a.sql
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
START TRANSACTION;

CALL sp_reservar_modelo(@modelo_id, @usuario_id, 1, @reserva_id);

SELECT 'A1: reserva creada' AS paso, @reserva_id AS reserva_id, precio, stock
FROM modelos WHERE id = @modelo_id;

SELECT SLEEP(5) AS espera_para_sesion_b;

COMMIT;

SELECT 'A2: después del COMMIT' AS paso, @reserva_id AS reserva_id, precio, stock
FROM modelos WHERE id = @modelo_id;
```

#### 4.2.5 Sobreventa — Sesión B

```sql
-- database/transacciones/10_serializable_overselling_b.sql
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
START TRANSACTION;

CALL sp_reservar_modelo(@modelo_id, @usuario_id, 1, @reserva_id);

COMMIT;
```

**Salida real — Sesión A:**

```text
paso                  reserva_id  precio     stock
A1: reserva creada    4           10000.00   0
espera_para_sesion_b
0
paso                  reserva_id  precio     stock
A2: después del COMMIT 4          10000.00   0
```

**Salida real — Sesión B:**

```text
ERROR 1020 (HY000) at line 24: Record has changed since last read in table 'modelos'; try restarting transaction
```

B esperó **4 019 ms** y MariaDB abortó su transacción con un conflicto de
serialización. **No se creó una segunda reserva** y el stock quedó en 0. La
sobreventa se evita, aunque el error sea `1020` y no el `1644 Stock insuficiente`
del procedimiento: en `SERIALIZABLE`, MariaDB prefiere abortar antes de permitir
que B lea una fila que cambió desde su snapshot.

**Complemento real con READ COMMITTED:** el mismo par de sesiones, cambiando solo
el nivel a `READ COMMITTED`, produce el error de negocio limpio:

```text
ERROR 1644 (45000) at line 24: Stock insuficiente
```

Esto muestra la diferencia: en READ COMMITTED el procedimiento llega a leer el
stock actualizado (0) y lanza el `SIGNAL`; en SERIALIZABLE la transacción se
aborta antes por conflicto de serialización. Ambos resultados evitan la
sobreventa.

#### 4.2.6 Verificación real

```sql
SELECT id, marca, nombre, anio, precio, stock, disponible
FROM modelos WHERE id = @modelo_id;

SELECT id, modelo_id, usuario_id, cantidad, estado, created_at
FROM reservas WHERE modelo_id = @modelo_id ORDER BY id;
```

```text
id  marca    nombre              anio  precio     stock  disponible
24  __TX__   Demo Transacciones  2026  10000.00   0      1

id  modelo_id  usuario_id  cantidad  estado      created_at
4   24         9           1         confirmada  2026-11-04 21:03:48
```

### 4.3 Tabla comparativa

| Criterio | READ COMMITTED | SERIALIZABLE |
|---|---|---|
| Lectura sucia | No | No |
| Lectura no repetible | **Sí** (demostrada) | No |
| Lectura fantasma | **Sí** (permitida) | **No** (demostrada) |
| Actualización perdida | Evitable con `FOR UPDATE` | Evitada por bloqueo de rango |
| Bloqueos | Solo filas modificadas | Filas y rangos (next-key) |
| Concurrencia | Alta | Baja |
| Riesgo de deadlock | Bajo | Mayor |
| Error típico al competir | `1644 Stock insuficiente` | `1020 Record has changed` |
| Uso recomendado | Catálogo, consultas, CRUD | Reservas, cierres, reportes exactos |

### 4.4 Capturas de las dos sesiones

| Figura | Qué mostrar | Comando exacto | Terminal | Sección |
|---|---|---|---|---|
| 5 | Lectura no repetible, Sesión A | `mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/02_read_committed_sesion_a.sql` | Terminal 1 | 4.1.2 |
| 6 | Lectura no repetible, Sesión B | `mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/03_read_committed_sesion_b.sql` | Terminal 2 | 4.1.3 |
| 7 | Actualización perdida evitada, Sesión B | `mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/05_read_committed_lost_update_b.sql` | Terminal 2 | 4.1.4 |
| 8 | Lectura fantasma, Sesión A | `mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/07_serializable_phantom_a.sql` | Terminal 1 | 4.2.2 |
| 9 | Lectura fantasma, Sesión B | `mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/08_serializable_phantom_b.sql` | Terminal 2 | 4.2.3 |
| 10 | Sobreventa, Sesión B (error 1020) | `mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/10_serializable_overselling_b.sql` | Terminal 2 | 4.2.5 |
| 11 | Verificación final | `mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/11_verify.sql` | Terminal 1 | 4.2.6 |

[IMAGEN 5–6: dos terminales con la salida de la Sesión A y la Sesión B de READ COMMITTED]
[IMAGEN 8–11: dos terminales con la salida de SERIALIZABLE (fantasma y sobreventa)]

---

## 5. Dificultades y soluciones

### 5.1 Evidencia en el historial de commits

| Commit | Evidencia | Dificultad inferida | Solución |
|---|---|---|---|
| `c637eae` | “update from databases + fix bug on aplicacion de filtros + integracion de modelos 3d” | Los filtros tenían un bug y había que integrar 3D | Se corrigieron filtros y se agregó el visor; `EXISTE` en `app/modelos/router.py` y `tests/test_modelos_filtros.py` |
| `72432d2` | “update from categoría Modelos (autos) y conexión a MariaDB” | Había que conectar la app a MariaDB y crear la categoría Modelos | Se agregó `app/modelos/`, DDL y semilla; `EXISTE` |
| `992b1e5` | “Add admin panel with sidebar…” | Faltaba administración de usuarios y roles | Se agregó panel, creación de admins y toggles; `EXISTE` |
| `52c1336` | “Security: add headers, config loader, admin user, Docker…” | Faltaban headers, configuración y Docker | Se agregó middleware, `config_loader.py` y compose; `EXISTE` |
| `33652f6`, `915ade8` | “Remove cookies… from tracking” | Se estaban versionando cookies | Se eliminaron y se ajustó `.gitignore`; `EXISTE` |
| `bbaad70` | “pre-lasted 0.0.1” | Punto de control | Sin detalle técnico; `NO ENCONTRADO` |

### 5.2 Discrepancias corregidas en este informe

1. **Alembic no verificable:** `docs/INFORME_EVIDENCIA.md` citaba migraciones y
   `alembic/versions/057f...py`, pero `alembic/versions/` no existe y está
   ignorado por `.gitignore`. Este informe no afirma que las migraciones se
   hayan ejecutado.
2. **DDL desactualizado:** el informe previo mostraba `modelos` sin las cinco
   columnas 3D. Aquí se incluyen `modelo_3d_key`, `modelo_3d_url`,
   `modelo_3d_formato`, `modelo_3d_tamano` y `modelo_3d_subido_at`.
3. **Conteo de pruebas:** el informe previo decía “12 passed”. La ejecución real
   de esta entrega fue **83 passed in 8.47s**.
4. **Versión del motor:** el motor oficial es MariaDB 11 (`mariadb:11`). La
   instancia local usada para las salidas es **MariaDB 13.0.2**, porque
   `startdb.sh` usa el binario del sistema. El DDL y los objetos son compatibles
   con 11.
5. **Alcance de motores:** MariaDB es el oficial; MySQL 8.4 y PostgreSQL 16 son
   variantes documentadas, no equivalentes operativas.
6. **Fecha:** la portada usa 4 de noviembre de 2026.
7. **Nombre de carpeta:** el repositorio real es `tallerDB`, no
   `tallerdbProyect`.
8. **Creación del esquema:** se realiza con SQL y `Base.metadata.create_all`;
   Alembic no se ejecuta en runtime.
9. **Credenciales:** el informe no reproduce contraseñas, `SECRET_KEY` ni
   cadenas de conexión. Los comandos usan `-p` para que el cliente pida la
   contraseña.
10. **Duplicación de DDL:** `schema_mariadb.sql` y `init/01_schema.sql` son
    copias mantenidas a mano; se documenta el riesgo.
11. **Duplicación de semilla:** `seed_modelos.sql` e `init/02_seed_modelos.sql`
    contienen los mismos 18 modelos; se documenta el riesgo.
12. **`dev.db`:** no se usó; todas las salidas son de MariaDB.
13. **Ejemplo `id=23`:** el informe previo lo usaba como ejemplo; aquí no se
    reutiliza como dato histórico.
14. **`.env`:** no está versionado; solo `.env.example`. El informe no asume que
    `.env` exista en un clon.
15. **Diagramas/capturas:** se usan Mermaid y una tabla de comandos; no se
    generan imágenes.
16. **CI:** no hay `.github/`; las pruebas son locales.

### 5.3 Dificultades sugeridas `SUGERIDA, CONFIRMAR`

No hay issues ni un historial detallado que pruebe estas dificultades; se
proponen a partir de las pruebas y del código:

1. **Conexión asíncrona a MariaDB:** el proyecto usa `asyncmy` y
   `SQLAlchemy 2.0 async`; un fallo de conexión debe detener el arranque.
   Evidencia indirecta: `tests/test_database_failfast.py` y
   `tests/test_config.py`. `SUGERIDA, CONFIRMAR`.
2. **Filtros con `LIKE` y comodines:** se agregó `_escape_like` y escape de HTML
   para evitar inyección de comodines y XSS. Evidencia:
   `tests/test_modelos_filtros.py::test_busqueda_escapa_comodines_like` y
   `test_busqueda_escapa_html`. `SUGERIDA, CONFIRMAR`.
3. **Validación de GLB:** se valida extensión, `content-type`, cabecera `glTF`,
   versión, tamaño y chunk JSON; se rechazan archivos inválidos y demasiado
   grandes. Evidencia: `tests/test_modelos_3d.py`. `SUGERIDA, CONFIRMAR`.
4. **Cookies y sesiones:** los commits de limpieza y el uso de
   `HttpOnly`/`SameSite` sugieren problemas de exposición de cookies.
   Evidencia: commits `33652f6` y `915ade8`. `SUGERIDA, CONFIRMAR`.
5. **Concurrencia de reservas:** la primera implementación con
   `SELECT` simple permitía sobreventa; se corrigió con `SELECT ... FOR UPDATE`
   y `SERIALIZABLE`. `PROPUESTO`/verificado en esta entrega.

---

## 6. Estado del proyecto

### 6.1 Avance estimado por tema

| Tema | Avance | Justificación |
|---|---:|---|
| Tema 1 | 70 % | Requerimientos y ER reconstruidos en `docs/`; no son evidencia original del curso. |
| Tema 2 | 90 % | DDL MariaDB/PostgreSQL, ORM, normalización y diccionario; falta consolidar un único DDL canónico y migraciones. |
| Tema 3 | 85 % | Vistas, funciones, procedimientos, triggers e índices implementados y probados; roles granulares pendientes. |
| Tema 4 | 80 % | Stock, reservas, auditoría y dos demos de transacciones; falta integrar reservas en la UI y agregar pruebas automatizadas de concurrencia. |

### 6.2 Pruebas realizadas

| Prueba | Comando | Resultado real |
|---|---|---|
| Conexión y esquema | `python app/main.py testdb` | `[OK]` tablas, columnas 3D y rollback; `users=2`, `modelos=18` |
| Suite completa | `python -m pytest -p no:cacheprovider -q` | **83 passed in 8.47s** |
| CRUD | `mariadb ... < database/pruebas_crud.sql` | 18 modelos al inicio y al final; `UNIQUE` duplicado devuelve `1062` |
| CHECK stock | `UPDATE modelos SET stock=-1` | `ERROR 4025` |
| UNIQUE modelo | `INSERT` duplicado | `ERROR 1062` |
| Procedimiento duplicado | `CALL sp_crear_modelo(...)` | `ERROR 1644: Ya existe...` |
| Reserva y cancelación | `CALL sp_reservar_modelo` / `sp_cancelar_reserva` | stock 3 → 1 → 3 |
| Vistas | `SELECT` sobre las 5 vistas | 5 vistas creadas y consultadas |
| Funciones | `SELECT fn_...` | `11600.00`, stock 5, reservas 0 |
| Triggers | Consulta a auditoría | 4 filas de modelo y 2 de reserva |
| Índices | `EXPLAIN` | `idx_modelos_tipo` y `idx_modelos_precio` usados |
| Rollback/reapply | Scripts `*_rollback.sql` y reaplicación | 18 modelos, 5 vistas, 7 rutinas, 5 triggers |
| READ COMMITTED | Dos terminales | Lectura 10000 → 12000; pérdida evitada 10500 → 11500 |
| SERIALIZABLE | Dos terminales | Fantasma 0 → 0; sobreventa abortada con `1020` |

### 6.3 Pendientes y siguientes pasos

1. Integrar `reservas` en la UI y en la API (fuera del alcance autorizado).
2. Agregar pruebas automatizadas de concurrencia (dos conexiones) a `tests/`.
3. Implementar roles granulares (`tallerdb_read`, `tallerdb_app`,
   `tallerdb_admin`) y mínimo privilegio.
4. Unificar el DDL canónico y generar las copias de Docker para evitar deriva.
5. Versionar las migraciones Alembic o eliminar la referencia del informe
   anterior.
6. Documentar el procedimiento de respaldo/restauración con `mariadb-dump`.
7. Revisar credenciales en `config.json` y documentación; mover a variables de
   entorno y rotarlas.

---

## 7. Conclusiones

- El proyecto ya tenía una base sólida de autenticación, catálogo, filtros y
  modelos 3D; esta entrega le agrega la dimensión de **inventario y reservas**.
- La incorporación de `stock`, `reservas`, `CHECK`, FK y triggers convierte el
  catálogo en un sistema con integridad verificable, no solo una galería.
- Las vistas, funciones y procedimientos reducen la lógica duplicada y permiten
  probar las reglas de negocio directamente en SQL.
- Las demos de transacciones muestran una diferencia real: `READ COMMITTED`
  permite lecturas no repetibles y exige bloqueo explícito; `SERIALIZABLE`
  evita fantasmas y sobreventa, pero puede abortar con `1020`.
- La documentación existente tenía discrepancias importantes (Alembic,
  conteo de pruebas, DDL sin 3D). Este informe las corrige y deja la base para
  la entrega final.

---

## 8. Referencias técnicas

- MariaDB Foundation. *Transactions*.
  https://mariadb.com/kb/en/transactions/
- MariaDB Foundation. *SET TRANSACTION*.
  https://mariadb.com/kb/en/set-transaction/
- MariaDB Foundation. *InnoDB Locking and Transaction Model*.
  https://mariadb.com/kb/en/innodb-locking-and-transaction-model/
- MariaDB Foundation. *CREATE PROCEDURE*.
  https://mariadb.com/kb/en/create-procedure/
- MariaDB Foundation. *CREATE FUNCTION*.
  https://mariadb.com/kb/en/create-function/
- MariaDB Foundation. *CREATE TRIGGER*.
  https://mariadb.com/kb/en/create-trigger/
- MariaDB Foundation. *CREATE VIEW*.
  https://mariadb.com/kb/en/create-view/
- MariaDB Foundation. *CHECK Constraints*.
  https://mariadb.com/kb/en/check-constraints/
- MariaDB Foundation. *Foreign Keys*.
  https://mariadb.com/kb/en/foreign-keys/
- PostgreSQL Global Development Group. *Transaction Isolation*.
  https://www.postgresql.org/docs/16/transaction-iso.html
- Oracle. *MySQL 8.4 Reference Manual — Transaction Isolation Levels*.
  https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html
- SQLAlchemy. *Asynchronous SQLAlchemy*.
  https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- FastAPI. *FastAPI documentation*.
  https://fastapi.tiangolo.com/

---

## Anexo A — Tabla de figuras y capturas

| N.º | Qué mostrar | Comando o herramienta | Terminal / ventana | Sección |
|---|---|---|---|---|
| 1 | Diagrama ER | Renderizar el bloque Mermaid de `docs/MODELO_DATOS.md` en VS Code o GitHub | — | 2.1 |
| 2 | Estadísticas por marca | `mariadb -h 127.0.0.1 -u taller -p tallerdb -e "SELECT * FROM vw_estadisticas_marca ORDER BY stock_total DESC LIMIT 5;"` | Terminal 1 | 3.2 |
| 3 | Auditoría de modelo y reserva | `mariadb ... -e "SELECT * FROM auditoria_modelos ORDER BY id; SELECT * FROM auditoria_reservas ORDER BY id;"` | Terminal 1 | 3.5 |
| 4 | Índices y `EXPLAIN` | `mariadb ... -e "SHOW INDEX FROM modelos; EXPLAIN SELECT ...;"` | Terminal 1 | 3.6 |
| 5 | READ COMMITTED, Sesión A | `... < database/transacciones/02_read_committed_sesion_a.sql` | Terminal 1 | 4.1.2 |
| 6 | READ COMMITTED, Sesión B | `... < database/transacciones/03_read_committed_sesion_b.sql` | Terminal 2 | 4.1.3 |
| 7 | Actualización perdida, Sesión B | `... < database/transacciones/05_read_committed_lost_update_b.sql` | Terminal 2 | 4.1.4 |
| 8 | SERIALIZABLE, Sesión A | `... < database/transacciones/07_serializable_phantom_a.sql` | Terminal 1 | 4.2.2 |
| 9 | SERIALIZABLE, Sesión B | `... < database/transacciones/08_serializable_phantom_b.sql` | Terminal 2 | 4.2.3 |
| 10 | Sobreventa, Sesión B | `... < database/transacciones/10_serializable_overselling_b.sql` | Terminal 2 | 4.2.5 |
| 11 | Verificación final | `... < database/transacciones/11_verify.sql` | Terminal 1 | 4.2.6 |
| 12 | Suite de pruebas | `python -m pytest -p no:cacheprovider -q` | Terminal 1 | 6.2 |
| 13 | Diagnóstico de BD | `python app/main.py testdb` | Terminal 1 | 6.2 |
| 14 | Estado de git | `git status --short; git log --oneline -8` | Terminal 1 | 5.1 |

**Nota:** las capturas 1 y 5–11 requieren **dos terminales**. La Terminal 2 debe
ejecutarse dentro de los 5 segundos del `SELECT SLEEP(5)` de la Terminal 1.

---

## Anexo B — Corrección de discrepancias 1–16

| # | Discrepancia | Corrección aplicada |
|---|---|---|
| 1 | Migraciones Alembic citadas pero ausentes | Se declara “no verificable”; no se afirma su ejecución. |
| 2 | DDL del informe previo sin columnas 3D | El DDL de la sección 2.2 incluye las cinco columnas 3D. |
| 3 | “12 passed” desactualizado | Se reportan **83 passed in 8.47s**. |
| 4 | MariaDB 10.6+ vs 11 | Motor oficial MariaDB 11; ejecución local 13.0.2; compatibilidad 10.6+. |
| 5 | Cuatro motores como equivalentes | MariaDB oficial; MySQL 8.4 y PostgreSQL 16 como variantes. |
| 6 | Fecha 17 de octubre | Fecha 4 de noviembre de 2026. |
| 7 | Carpeta `tallerdbProyect` | Repositorio real `tallerDB`. |
| 8 | “Creada por Alembic” | Esquema creado por SQL y `Base.metadata.create_all`. |
| 9 | Credenciales en texto plano | Informe redactado; comandos con `-p`. |
| 10 | DDL duplicado | Se documenta el riesgo y se propone un DDL canónico. |
| 11 | Semilla duplicada | Se documenta el riesgo. |
| 12 | `dev.db` | No se usó; todas las salidas son MariaDB. |
| 13 | Ejemplo `id=23` | No se reutiliza como dato histórico. |
| 14 | `.env` “incluido” | Solo `.env.example` está versionado. |
| 15 | Sin imágenes | Mermaid + tabla de capturas. |
| 16 | Sin CI | Se reportan pruebas locales, no CI. |

---

## Anexo C — Archivos creados/modificados en esta entrega

**Nuevos scripts SQL:**

- `database/03_views.sql` y `database/03_views_rollback.sql`
- `database/04_procedures.sql` y `database/04_procedures_rollback.sql`
- `database/05_functions.sql` y `database/05_functions_rollback.sql`
- `database/06_triggers.sql` y `database/06_triggers_rollback.sql`
- `database/08_stock_reservas.sql` y `database/08_stock_reservas_rollback.sql`
- `database/09_indexes.sql` y `database/09_indexes_rollback.sql`
- `database/transacciones/00_setup.sql` a `12_cleanup.sql`
- `database/transacciones/README.md`

**Nuevos documentos:**

- `docs/REQUERIMIENTOS.md`
- `docs/MODELO_DATOS.md`
- `docs/INFORME_AVANCE_4.4.md`

**Modificado:**

- `docs/INFORME_EVIDENCIA.md` — nota al inicio que apunta al informe vigente y
  redacción de credenciales.
- `database/pruebas_crud.sql` y `database/seed_modelos.sql` — redacción de la
  contraseña en los comentarios de uso.

**No modificado por esta entrega:** `app/` y la UI. Los cambios sin commitear
que aparecen en `git status` para `app/`, `tests/` y `README.md` son trabajo
previo del proyecto (se documentan como avance en la sección 3.8), no cambios
introducidos aquí. **No se hicieron commits.**

---

## Anexo D — Datos que faltan o deben confirmarse

1. **Temario real de los Temas 1–3:** el informe usa la asignación tentativa
   `SUPUESTO`. Si el temario oficial difiere, hay que remapear secciones.
2. **Integrante, docente, institución y grupo:** la portada los deja como
   `(completar)`.
3. **Porcentaje de avance:** es una estimación; falta la rúbrica oficial.
4. **Roles/permisos:** P7 quedó fuera del alcance; si se requiere, hay que
   implementarlo.
5. **Integración de reservas en la UI:** no se hizo; solo existe en SQL.
6. **Pruebas de concurrencia automatizadas:** las demos son manuales con dos
   terminales; no están en `pytest`.
7. **Migraciones Alembic:** no existen; decidir si se versionan o se elimina la
   referencia.
8. **Credenciales en `config.json`:** hay secretos versionados; hay que rotarlos
   y moverlos a variables de entorno fuera de este informe.
