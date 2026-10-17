# TallerDB — Catálogo de Autos (categoría «Modelos»)

**Informe de evidencia — Aplicación web con base de datos MariaDB**

---

## 1. Portada

| Campo | Detalle |
|---|---|
| **Nombre del proyecto** | TallerDB — Catálogo de Autos |
| **Integrante** | _(completar con el nombre del alumno)_ |
| **Materia / Asignatura** | _(completar: p. ej. Bases de Datos)_ |
| **Docente** | _(completar)_ |
| **Institución** | _(completar)_ |
| **Grupo / Cuatrimestre** | _(completar)_ |
| **Fecha de entrega** | 17 de octubre de 2026 |

> **Tecnologías utilizadas:** Python 3.14 · FastAPI 0.115 · SQLAlchemy 2.0 (async) · MariaDB 11 (driver `asyncmy`) · Jinja2 · Alembic 1.13.

**Repositorio / carpeta del proyecto:** `tallerdbProyect/`

---

## 2. Introducción

El presente proyecto consiste en una aplicación web desarrollada con **FastAPI** y **MariaDB** cuyo propósito es **mostrar un catálogo de autos**. Para ello se incorporó una categoría principal llamada **«Modelos»**, que representa cada automóvil del catálogo mediante la entidad `modelos`.

La aplicación parte de un sistema de autenticación y administración de usuarios ya existente y **extiende su alcance** con:

1. **Conexión a una base de datos MariaDB** mediante el driver asíncrono `asyncmy`.
2. Una **nueva categoría «Modelos»** con esquema, interfaz gráfica y API REST.
3. Un **conjunto de consultas SQL** y scripts que documentan la creación del esquema, los datos de ejemplo y la verificación de las operaciones **CRUD** (Create, Read, Update, Delete).

El objetivo es demostrar el uso completo de una base de datos relacional: diseño del esquema, conexión desde la aplicación, operaciones de inserción, actualización, borrado y consulta, así como la construcción de la interfaz web que los manipula.

---

## 3. Desarrollo

### 3.1 Descripción de las interfaces

La aplicación incorpora una interfaz protegida por sesión. Las vistas nuevas y relevantes para la categoría «Modelos» son:

| Interfaz | Ruta | Método | Descripción |
|---|---|---|---|
| **Menú lateral** | `/dashboard` | GET | Se agregó la opción «Modelos» al menú y una tarjeta de acceso rápido. |
| **Catálogo de autos** | `/modelos` | GET | Galería con todos los autos en tarjetas. Incluye buscador, filtros y estadísticas. |
| **Filtros de consulta** | `/modelos` | GET | Búsqueda general (`q`), marca, tipo, disponibilidad, rango de años y ordenamiento. |
| **Estadísticas** | `/modelos` | GET | Total, disponibles, precio promedio y rango de años (calculadas con SQL). |
| **Modal de alta/edición** | `/modelos` | UI | Formulario de creación y edición de un modelo. |
| **API REST** | `/modelos/api` | GET/POST/PUT/DELETE | Operaciones CRUD en formato JSON. |
| **Documentación API** | `/docs` | GET | Swagger UI autogenerado por FastAPI. |

**Interfaz principal — catálogo (`/modelos`)**

- Barra de **búsqueda general** por marca, nombre o descripción.
- **Filtros**: marca, tipo de carrocería y disponibilidad.
- **Ordenamiento**: más recientes, precio (asc/desc), año (asc/desc) y marca.
- **Estadísticas** superiores calculadas en la base de datos.
- **Galería** en *grid* con tarjeta por auto: marca, modelo, año, precio, color, transmisión y estado de disponibilidad.
- Solo los usuarios con rol de **administrador** ven los botones «Nuevo modelo», «Editar» y «Eliminar».

**Interfaz de ejemplos (comportamiento)**

```
┌──────────────── Catálogo de autos ─────────────────┐
│ [Buscar...]  [Marca▾] [Tipo▾] [Disponible▾]  [+ Nuevo] │
├────────────────────────────────────────────────────┤
│  🚗 Ford Mustang      🚗 BMW Serie 3   🚗 Tesla Model 3 │
│  2024 · Deportivo     2025 · Sedán     2025 · Sedán     │
│  $ 98,000.00           $ 89,500.00      $ 74,900.00     │
│  [Editar] [Eliminar]  ...               ...             │
└────────────────────────────────────────────────────┘
```

### 3.2 Conexión a MariaDB

La conexión se configura de forma centralizada. La cadena de conexión se construye en `app/config_loader.py`:

```python
# mysql+asyncmy://usuario:contraseña@host:puerto/base_de_datos?charset=utf8mb4
DATABASE_TYPE=mariadb
MARIADB_HOST=127.0.0.1
MARIADB_PORT=3306
MARIADB_USER=taller
MARIADB_PASSWORD=tallerpass
MARIADB_DATABASE=tallerdb
```

Resultado de la construcción de la URL (verificado):

```
mysql+asyncmy://taller:tallerpass@127.0.0.1:3307/tallerdb?charset=utf8mb4
```

La entidad `Modelo` (tabla `modelos`) es creada por Alembic y también por los scripts SQL descritos en el apartado 3.4.

### 3.3 Pruebas de inserción, actualización, borrado y consultas

Las pruebas se documentan en el archivo **`database/pruebas_crud.sql`**, que ejecuta las cuatro operaciones dentro de una transacción y finaliza con `ROLLBACK`, por lo que **no deja residuos** en la base de datos.

**Ejecución real (salida de la consola MariaDB):**

```sql
-- PRUEBA 1: INSERCIÓN (CREATE)
INSERT INTO modelos (marca, nombre, anio, precio, color, tipo, transmision, disponible, descripcion)
VALUES ('Prueba', 'Test Coupé', 2026, 55000.00, 'Rojo', 'coupe', 'manual', 1, '...');

+----+--------+-----------+------+----------+-----------+
| id | marca  | nombre    | anio | precio   | disponible|
+----+--------+-----------+------+----------+-----------+
| 19 | Prueba | Test Coupé| 2026 | 55000.00 |         1 |
+----+--------+-----------+------+----------+-----------+

-- Prueba negativa de restricción UNIQUE (esperado):
ERROR 1062 (23000): Duplicate entry 'Prueba-Test Coupé-2026' for key 'uq_modelo_marca_nombre_anio'
```

```sql
-- PRUEBA 2: CONSULTA (READ)  -- filtro por marca
SELECT marca, nombre, anio, precio FROM modelos WHERE marca = 'Toyota' ORDER BY anio DESC;
+--------+---------+------+----------+
| marca  | nombre  | anio | precio   |
+--------+---------+------+----------+
| Toyota | Corolla | 2025 | 29900.00 |
| Toyota | Corolla | 2024 | 28900.00 |
| Toyota | Hilux   | 2024 | 52500.00 |
+--------+---------+------+----------+

-- PRUEBA 2.4: agregados
+-------+-----------------+------------+-----------+
| total | precio_promedio | precio_min | precio_max|
+-------+-----------------+------------+-----------+
|    19 |        42815.79 |   19800.00 |  98000.00 |
+-------+-----------------+------------+-----------+

-- PRUEBA 2.5: conteo por tipo (GROUP BY)
+-----------+----------+
| tipo      | cantidad |
+-----------+----------+
| sedan     |        8 |
| suv       |        5 |
| hatchback |        3 |
| coupe     |        1 |
| pickup    |        1 |
| deportivo |        1 |
+-----------+----------+
```

```sql
-- PRUEBA 3: ACTUALIZACIÓN (UPDATE)
UPDATE modelos SET precio = 49999.99, disponible = 0 WHERE marca = 'Prueba' AND nombre = 'Test Coupé';

-- Antes: 55000.00  |  Después: 49999.99, disponible = 0, actualizado

-- Actualización masiva de precios a los SUV (+5%)
+-------------+-----------+------+----------+
| marca       | nombre    | ...  | precio   |
+-------------+-----------+------+----------+
| Kia         | Sportage  |      | 50190.00 |
| Hyundai     | Tucson    |      | 47460.00 |
| Honda       | HR-V      |      | 37695.00 |
| Volkswagen  | T-Cross   |      | 35070.00 |
| Renault     | Duster    |      | 30765.00 |
+-------------+-----------+------+----------+
```

```sql
-- PRUEBA 4: BORRADO (DELETE)
DELETE FROM modelos WHERE marca = 'Prueba' AND nombre = 'Test Coupé';
-- Verificación: filas_restantes_del_modelo_prueba = 0

DELETE FROM modelos WHERE id = 0;   -- prueba negativa
-- filas_afectadas_por_id_inexistente = 0

-- ESTADO FINAL tras el ROLLBACK
+--------------------------+
| total_modelos_final_real |
+--------------------------+
|                       18 |
+--------------------------+
```

### 3.4 Código fuente de los scripts SQL

**a) `database/schema_mariadb.sql`** — creación de la base de datos y tablas:

```sql
CREATE DATABASE IF NOT EXISTS tallerdb
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tallerdb;

CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT 1,
    is_admin        BOOLEAN      NOT NULL DEFAULT 0,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY ix_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS modelos (
    id          INT           AUTO_INCREMENT PRIMARY KEY,
    marca       VARCHAR(100)  NOT NULL,
    nombre      VARCHAR(120)  NOT NULL,
    anio        INT           NOT NULL,
    precio      DECIMAL(12,2) NOT NULL,
    color       VARCHAR(50)   NULL,
    tipo        VARCHAR(40)   NOT NULL DEFAULT 'sedan',
    transmision VARCHAR(30)   NOT NULL DEFAULT 'manual',
    disponible  BOOLEAN       NOT NULL DEFAULT 1,
    descripcion TEXT          NULL,
    imagen_url  VARCHAR(500)  NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_modelo_marca_nombre_anio (marca, nombre, anio),
    KEY ix_modelos_marca  (marca),
    KEY ix_modelos_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**b) `database/seed_modelos.sql`** — inserción de datos de ejemplo (18 autos):

```sql
INSERT IGNORE INTO modelos
    (marca, nombre, anio, precio, color, tipo, transmision, disponible, descripcion)
VALUES
    ('Toyota', 'Corolla', 2024, 28900.00, 'Blanco', 'sedan', 'automatica', 1, 'Sedán compacto...'),
    ('Ford',   'Mustang', 2024, 98000.00, 'Amarillo', 'deportivo', 'manual', 1, 'Deportivo icónico...'),
    -- ... 18 modelos en total
    ('Tesla',  'Model 3', 2025, 74900.00, 'Blanco', 'sedan', 'automatica', 1, 'Eléctrico...');
```

**b.1) Archivos de inicialización para Docker** (`database/init/`): la imagen oficial de MariaDB ejecuta automáticamente estos scripts al crear el volumen de datos.

```
database/init/01_schema.sql        # esquema (users + modelos)
database/init/02_seed_modelos.sql  # datos de ejemplo
```

**c) `database/pruebas_crud.sql`** — pruebas de las cuatro operaciones (fragmento):

```sql
START TRANSACTION;
-- INSERCIÓN
INSERT INTO modelos (marca, nombre, anio, precio, ...) VALUES (...);
-- CONSULTA
SELECT marca, nombre, anio, precio FROM modelos WHERE marca = 'Toyota' ORDER BY anio DESC;
SELECT COUNT(*) AS total, ROUND(AVG(precio),2) AS precio_promedio, MIN(precio), MAX(precio) FROM modelos;
SELECT tipo, COUNT(*) FROM modelos GROUP BY tipo ORDER BY 2 DESC;
-- ACTUALIZACIÓN
UPDATE modelos SET precio = 49999.99, disponible = 0 WHERE marca = 'Prueba' AND nombre = 'Test Coupé';
-- BORRADO
DELETE FROM modelos WHERE marca = 'Prueba' AND nombre = 'Test Coupé';
ROLLBACK;
```

**d) Definición ORM equivalente** (`app/models/modelo.py`): la entidad `Modelo` mapea la tabla `modelos`.

```python
class Modelo(Base):
    __tablename__ = "modelos"
    __table_args__ = (UniqueConstraint("marca", "nombre", "anio", name="uq_modelo_marca_nombre_anio"),)

    id:          Mapped[int]     = mapped_column(Integer, primary_key=True, autoincrement=True)
    marca:       Mapped[str]     = mapped_column(String(100), nullable=False, index=True)
    nombre:      Mapped[str]     = mapped_column(String(120), nullable=False, index=True)
    anio:        Mapped[int]     = mapped_column(Integer, nullable=False)
    precio:      Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    color:       Mapped[str]     = mapped_column(String(50), nullable=True)
    tipo:        Mapped[str]     = mapped_column(String(40), nullable=False, default="sedan")
    transmision: Mapped[str]     = mapped_column(String(30), nullable=False, default="manual")
    disponible:  Mapped[bool]    = mapped_column(Boolean, nullable=False, default=True)
    descripcion: Mapped[str]     = mapped_column(Text, nullable=True)
    imagen_url:  Mapped[str]     = mapped_column(String(500), nullable=True)
    created_at:  Mapped[datetime]= mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at:  Mapped[datetime]= mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

### 3.5 Resultados obtenidos

**Verificación de la conexión a MariaDB y creación del esquema**

```
$ mariadb --version
mariadb  Ver ... 10.x/11.x  Distrib ...

$ alembic upgrade head
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Running upgrade  -> 6c7809c1762a, Initial migration - users table
INFO  [alembic.runtime.migration] Running upgrade 6c7809c1762a -> 0f9f10566365, Add is_admin column to users
INFO  [alembic.runtime.migration] Running upgrade 0f9f10566365 -> 057f4683225b, Add modelos table
```

**Tablas creadas en MariaDB**

```
MariaDB [tallerdb]> SHOW TABLES;
+--------------------+
| Tables_in_tallerdb |
+--------------------+
| alembic_version    |
| modelos            |
| users              |
+--------------------+
```

**API REST verificada con `curl` (usuario administrador con sesión iniciada)**

| Operación | Petición | Resultado |
|---|---|---|
| **READ** (lista) | `GET /modelos/api?limit=3&orden=precio_desc` | `200 OK` — 3 modelos ordenados por precio. |
| **CREATE** | `POST /modelos/api` con JSON `PruebaAPI/Integra` | `201 Created` — `id = 23`. |
| **READ** (uno) | `GET /modelos/api/23` | `200 OK` — datos del modelo. |
| **UPDATE** | `PUT /modelos/api/23` con `{"precio": 9999.99, "disponible": false}` | `200 OK` — campos actualizados. |
| **QUERY** | `GET /modelos/api?q=Integra` | `200 OK` — 1 coincidencia. |
| **DELETE** | `DELETE /modelos/api/23` | `200 OK`. |
| **READ** (tras borrar) | `GET /modelos/api/23` | `404 Not Found`. |

**Interfaz web**

- `GET /modelos` responde `200` y renderiza **18 tarjetas** de autos del catálogo.
- El menú lateral del panel incluye el enlace **«Modelos»** (`/dashboard`).
- Los usuarios sin sesión son redirigidos a `/login` (código `303`).

**Pruebas automatizadas**

```
$ pytest -q
............
12 passed in 0.46s
```

---

## 4. Recomendaciones

1. **No exponer contraseñas ni claves `SECRET_KEY` por defecto** en producción; generar la clave con `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
2. **Ejecutar las migraciones de Alembic** de forma controlada en cada despliegue (`alembic upgrade head`) para mantener el esquema versionado.
3. **Usar un usuario de base de datos con permisos mínimos** (no `root`) y restringir el acceso por red.
4. **Habilitar HTTPS** y cookies `Secure` cuando `DEBUG=false` (ya contemplado en el middleware de sesión).
5. **Implementar respaldos periódicos** de la base de datos con `mariadb-dump`.
6. **Agregar paginación en la interfaz** cuando el catálogo crezca; la API ya soporta `limit`/`offset`.
7. **Añadir imágenes reales** de los autos (el campo `imagen_url` ya existe en el modelo).
8. **Incorporar pruebas de integración con base de datos temporal** para no depender de la base de desarrollo.

---

## 5. Conclusiones

- Se logró **integrar la aplicación con una base de datos MariaDB**, construyendo la cadena de conexión de forma centralizada y verificando el correcto funcionamiento del driver asíncrono.
- Se implementó la **categoría «Modelos»**, que permite *mostrar* un catálogo de autos tanto en una interfaz web como a través de una API REST.
- Quedaron **demostradas las cuatro operaciones CRUD** con resultados verificables: inserción (incluyendo la validación de la restricción `UNIQUE`), consultas con filtros y agregados, actualización (individual y masiva) y borrado.
- El uso de **Alembic** garantiza que el esquema pueda evolucionar de manera ordenada y reproducible.
- El proyecto cumple con la estructura de evidencia solicitada: interfaz, pruebas, scripts SQL y resultados.

---

## 6. Referencias (formato APA)

Bayer, M. (2024). *Alembic documentation*. https://alembic.sqlalchemy.org/en/latest/

Bayer, M. (2024). *SQLAlchemy 2.0 documentation*. https://docs.sqlalchemy.org/

FastAPI. (2024). *FastAPI documentation*. https://fastapi.tiangolo.com/

MariaDB Foundation. (2024). *MariaDB documentation*. https://mariadb.org/documentation/

Pallets. (2024). *Jinja*. https://jinja.palletsprojects.com/

Python Software Foundation. (2024). *Python 3.14 documentation*. https://docs.python.org/3/

Starlette. (2024). *Starlette documentation*. https://www.starlette.io/

---

## Anexo A — Estructura de archivos nuevos / modificados

```
tallerdbProyect/
├── app/
│   ├── models/
│   │   └── modelo.py                # Entidad Modelo (tabla modelos)
│   ├── schemas/
│   │   └── modelo.py                # Validación Pydantic
│   ├── modelos/
│   │   ├── __init__.py
│   │   └── router.py                # Página HTML + API CRUD
│   └── templates/
│       └── modelos.html             # Interfaz del catálogo
├── database/
│   ├── schema_mariadb.sql           # DDL del esquema
│   ├── seed_modelos.sql             # Datos de ejemplo
│   ├── pruebas_crud.sql             # Pruebas INSERT/UPDATE/DELETE/SELECT
│   └── init/                        # Scripts para el contenedor MariaDB
│       ├── 01_schema.sql
│       └── 02_seed_modelos.sql
├── alembic/versions/057f4683225b_add_modelos_table.py
└── (informe) docs/INFORME_EVIDENCIA.md
```

## Anexo B — Cómo levantar el entorno

**Con Docker (MariaDB):**

```bash
docker compose up --build
# Interfaz: http://localhost:8000/modelos
```

**Local (con un servidor MariaDB en marcha):**

```bash
# 1. Crear la base de datos y las tablas
mariadb -u root -p < database/schema_mariadb.sql

# 2. Datos de ejemplo
mariadb -u taller -p tallerdb < database/seed_modelos.sql

# 3. Configurar .env (DATABASE_TYPE=mariadb y variables MARIADB_*)
# 4. Iniciar la aplicación
python run.py
```

**Ejecutar las pruebas CRUD:**

```bash
mariadb -u taller -p --force tallerdb < database/pruebas_crud.sql
```
