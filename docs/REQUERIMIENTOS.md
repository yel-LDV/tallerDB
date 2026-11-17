# TallerDB — Requerimientos (reconstrucción)

**Proyecto:** TallerDB — Catálogo de Autos  
**Fecha:** 4 de noviembre de 2026  
**Alcance:** Actividad 4.4 — Informe de Avance de Proyecto  
**Naturaleza del documento:** reconstrucción a partir del código, el README y el
informe de evidencia. Los objetivos y requisitos marcados como **(nuevo)** se
incorporan en esta entrega para cubrir el Tema 4.

> **Etiquetas de evidencia:** `EXISTE` = verificable en el repositorio;
> `INFERIDO` = deducido del código/README; `PROPUESTO` = definido en esta
> entrega; `NO ENCONTRADO` = no hay evidencia.

---

## 1. Problema

Un taller o concesionario necesita publicar su catálogo de autos, permitir que
los clientes consulten disponibilidad y precio, y que solo el personal
autorizado pueda administrar el inventario. El proyecto parte de una aplicación
web con autenticación y administración de usuarios, a la que se le incorporó la
categoría **Modelos** y, en esta entrega, el control de **stock** y
**reservas**. `INFERIDO` de `README.md` y `docs/INFORME_EVIDENCIA.md`.

El problema central es que un catálogo sin inventario no puede responder con
fiabilidad a la pregunta “¿cuántas unidades quedan?”. La incorporación de
`modelos.stock` y `reservas` convierte el catálogo en un sistema con una regla
de negocio verificable: no se puede reservar más de lo disponible. `PROPUESTO`.

---

## 2. Objetivo general

Diseñar e implementar una base de datos relacional en MariaDB para un catálogo
de autos, con autenticación de usuarios, administración del catálogo, control de
inventario y reservas, aplicando diseño relacional, SQL avanzado y transacciones
con niveles de aislamiento. `PROPUESTO`.

## 3. Objetivos específicos

1. Modelar las entidades `users`, `modelos` y `reservas` con claves primarias,
   claves foráneas y restricciones de integridad. `PROPUESTO` para `reservas`;
   `EXISTE` para `users` y `modelos`.
2. Documentar el modelo conceptual, el modelo relacional y la normalización.
   `PROPUESTO`.
3. Implementar el DDL en MariaDB 11 y su variante PostgreSQL 16. `EXISTE`
   parcialmente; `stock` y `reservas` se agregan en `database/08_stock_reservas.sql`.
4. Implementar consultas, vistas, funciones, procedimientos y triggers.
   `EXISTE` para consultas e índices; `PROPUESTO` para vistas, funciones,
   procedimientos y triggers.
5. Demostrar dos transacciones con niveles de aislamiento distintos
   (`READ COMMITTED` y `SERIALIZABLE`) sobre datos reales. `PROPUESTO`.
6. Verificar el sistema con pruebas automatizadas y scripts SQL reproducibles.
   `EXISTE` para pytest y CRUD; `PROPUESTO` para las demos de transacciones.

---

## 4. Alcance

### 4.1 Incluido

- Registro, inicio y cierre de sesión; perfil y cambio de contraseña.
- Administración de usuarios y roles (`is_admin`, `is_active`).
- Catálogo de modelos con búsqueda, filtros, ordenamiento, paginación y
  estadísticas.
- API REST de modelos y visor de modelos 3D en formato GLB.
- Inventario por modelo (`stock`) y reservas con estados.
- Vistas, funciones, procedimientos, triggers, índices y auditoría.
- Transacciones `READ COMMITTED` y `SERIALIZABLE`.

### 4.2 Excluido

- Pasarela de pagos y facturación.
- Notificaciones por correo o mensajería.
- Aplicación móvil nativa.
- Reglas fiscales específicas por país.
- Autenticación multifactor.

---

## 5. Actores

| Actor | Descripción | Evidencia |
|---|---|---|
| Visitante | Consulta la landing y puede registrarse. | `EXISTE` (`app/templates/landing.html`, `/register`). |
| Usuario registrado | Inicia sesión, consulta el catálogo y su perfil. | `EXISTE` (`app/auth/router.py`). |
| Administrador | Crea, edita y elimina modelos; gestiona usuarios y archivos 3D. | `EXISTE` (`app/auth/router.py`, `app/modelos/router.py`). |
| Cliente | Reserva unidades de un modelo. | `PROPUESTO` (`reservas`, `sp_reservar_modelo`). |
| DBA | Ejecuta scripts, migraciones, respaldos y consultas de auditoría. | `INFERIDO` (`startdb.sh`, `database/`). |

---

## 6. Requisitos funcionales

| ID | Requisito | Evidencia |
|---|---|---|
| RF-01 | Registrar usuarios con email único y contraseña validada. | `EXISTE` |
| RF-02 | Iniciar y cerrar sesión con cookie HttpOnly. | `EXISTE` |
| RF-03 | Distinguir usuarios normales de administradores. | `EXISTE` |
| RF-04 | Listar, buscar, filtrar, ordenar y paginar modelos. | `EXISTE` |
| RF-05 | Crear, editar y eliminar modelos solo como administrador. | `EXISTE` |
| RF-06 | Subir, reemplazar, visualizar y eliminar un GLB por modelo. | `EXISTE` |
| RF-07 | Consultar y cambiar la propia contraseña. | `EXISTE` (sin commit) |
| RF-08 | Mostrar solo las acciones permitidas según el rol. | `EXISTE` (sin commit) |
| RF-09 | Controlar el stock por modelo y evitar stock negativo. | `PROPUESTO` |
| RF-10 | Registrar reservas con cantidad, usuario, modelo y estado. | `PROPUESTO` |
| RF-11 | Evitar la sobreventa cuando dos usuarios reservan a la vez. | `PROPUESTO` |
| RF-12 | Auditar cambios de precio, stock, disponibilidad y reservas. | `PROPUESTO` |
| RF-13 | Exportar estadísticas por marca y por tipo mediante vistas. | `PROPUESTO` |

---

## 7. Requisitos no funcionales

| ID | Requisito | Evidencia |
|---|---|---|
| RNF-01 | Motor oficial MariaDB 11; PostgreSQL 16 y MySQL 8.4 como variantes. | `EXISTE` en Docker; decisión de esta entrega. |
| RNF-02 | Integridad referencial con InnoDB y claves foráneas. | `PROPUESTO` para `reservas`. |
| RNF-03 | Contraseñas con bcrypt y sesiones HttpOnly/SameSite. | `EXISTE` |
| RNF-04 | No exponer secretos en el repositorio ni en el informe. | `PARCIAL`: hay credenciales en `config.json` y documentación; el informe las redacta. |
| RNF-05 | Arranque fail-fast si la base de datos no responde. | `EXISTE` |
| RNF-06 | Pruebas automatizadas reproducibles. | `EXISTE`: 83 casos ejecutados. |
| RNF-07 | Scripts SQL idempotentes y con rollback. | `PROPUESTO` para los objetos nuevos. |
| RNF-08 | Compatibilidad con el CRUD actual sin modificar `app/`. | `EXISTE`: las columnas nuevas son nullable o tienen default. |

---

## 8. Casos de uso principales

### UC-01 — Consultar catálogo

1. El usuario abre `/modelos`.
2. Aplica búsqueda, marca, tipo, disponibilidad y rango de años.
3. El sistema devuelve la página filtrada y las estadísticas.
4. Puede abrir el visor 3D si el modelo tiene GLB.

**Evidencia:** `EXISTE` en `app/modelos/router.py` y `tests/test_modelos_filtros.py`.

### UC-02 — Reservar un modelo

1. El cliente elige un modelo con stock.
2. El sistema bloquea la fila con `SELECT ... FOR UPDATE`.
3. Verifica que `stock >= cantidad`.
4. Descuenta stock e inserta la reserva.
5. Si no hay stock, devuelve “Stock insuficiente” y no crea la reserva.

**Evidencia:** `PROPUESTO` en `sp_reservar_modelo`.

### UC-03 — Cancelar una reserva

1. El cliente indica la reserva.
2. El sistema verifica que no esté cancelada.
3. Cambia el estado a `cancelada` y devuelve el stock.
4. El trigger de auditoría registra el cambio.

**Evidencia:** `PROPUESTO` en `sp_cancelar_reserva` y triggers.

### UC-04 — Administrar usuarios

1. El admin abre el panel.
2. Crea usuarios, otorga/quita admin o activa/desactiva cuentas.
3. No puede modificarse a sí mismo.

**Evidencia:** `EXISTE` en `app/auth/router.py`.

### UC-05 — Auditar cambios

1. El DBA consulta `auditoria_modelos` o `auditoria_reservas`.
2. Ve acción, valores anteriores/nuevos, usuario de BD y fecha.

**Evidencia:** `PROPUESTO` en `database/06_triggers.sql`.

---

## 9. Supuestos y restricciones

- El catálogo se administra desde la aplicación; las reservas se incorporan en
  esta entrega mediante SQL y procedimientos, sin modificar la UI. `PROPUESTO`.
- `modelos.disponible` es una bandera de exhibición; `modelos.stock` es la
  cantidad real. La regla de negocio es: si `stock = 0`, el modelo no debería
  ofrecerse, aunque `disponible` siga en 1. `PROPUESTO`.
- El stock inicial de los 18 modelos de ejemplo se fija en 5 unidades para los
  disponibles y 0 para los no disponibles. `PROPUESTO`.
- Las reservas canceladas no se borran: cambian de estado y devuelven stock.
- La aplicación no se modifica en esta entrega; las tablas nuevas son ignoradas
  por el ORM actual y no rompen el CRUD. `EXISTE` (verificado con `testdb` y
  `pytest`).

---

## 10. Trazabilidad

| Requisito | Implementación |
|---|---|
| RF-01 a RF-03 | `app/auth/router.py`, `app/models/user.py` |
| RF-04 a RF-05 | `app/modelos/router.py`, `app/models/modelo.py` |
| RF-06 | `app/modelos/storage.py`, `app/static/vendor/model-viewer.min.js` |
| RF-07 a RF-08 | `app/templates/profile.html`, cambios sin commit en `app/auth/router.py` |
| RF-09 a RF-13 | `database/08_stock_reservas.sql`, `03_views.sql`, `04_procedures.sql`, `05_functions.sql`, `06_triggers.sql`, `09_indexes.sql` |
| RNF-06 | `tests/` (83 casos) |
| RNF-07 | Scripts `*_rollback.sql` |
