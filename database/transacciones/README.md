# Demos de transacciones — TallerDB

Estos guiones usan **dos terminales** con el cliente `mariadb` y las tablas
reales `modelos`, `users` y `reservas`. No usan `dev.db`.

## Requisitos

```bash
./startdb.sh
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/08_stock_reservas.sql
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/04_procedures.sql
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/06_triggers.sql
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/00_setup.sql
```

El cliente pedirá la contraseña; no la escribas en el comando ni en el historial.

## Demo 1 — READ COMMITTED: lectura no repetible y actualización perdida

### 1.1 Lectura no repetible

**Terminal 1**

```bash
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/01_read_committed_reset.sql
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/02_read_committed_sesion_a.sql
```

**Terminal 2** (ejecutar dentro de los 5 segundos del `SELECT SLEEP(5)`)

```bash
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/03_read_committed_sesion_b.sql
```

Resultado esperado:

- A1 lee `10000.00`.
- B actualiza a `12000.00` y confirma.
- A2, en la misma transacción, lee `12000.00`.
- Es una **lectura no repetible** permitida por READ COMMITTED.

### 1.2 Actualización perdida evitada con `SELECT ... FOR UPDATE`

**Terminal 1**

```bash
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/01_read_committed_reset.sql
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/04_read_committed_lost_update_a.sql
```

**Terminal 2** (dentro de los 5 segundos)

```bash
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/05_read_committed_lost_update_b.sql
```

Resultado esperado:

- A bloquea la fila y suma 500 → `10500.00`.
- B queda esperando en `SELECT ... FOR UPDATE`.
- Cuando A confirma, B lee `10500.00` y suma 1000 → `11500.00`.
- No se pierde la actualización de A.

## Demo 2 — SERIALIZABLE: lectura fantasma y sobreventa

### 2.1 Lectura fantasma

**Terminal 1**

```bash
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/06_serializable_reset.sql
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/07_serializable_phantom_a.sql
```

**Terminal 2** (dentro de los 5 segundos)

```bash
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/08_serializable_phantom_b.sql
```

Resultado esperado:

- A1 cuenta `0` reservas confirmadas.
- B intenta insertar y queda bloqueada por los bloqueos de rango de SERIALIZABLE.
- A2 vuelve a contar `0`: no ve la fila fantasma.
- A confirma; B inserta. La verificación final muestra `1`.

### 2.2 Sobreventa evitada con `sp_reservar_modelo`

**Terminal 1**

```bash
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/06_serializable_reset.sql
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/09_serializable_overselling_a.sql
```

**Terminal 2** (dentro de los 5 segundos)

```bash
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/10_serializable_overselling_b.sql
```

Resultado esperado:

- A reserva la única unidad y deja el stock en `0`.
- B espera el bloqueo; cuando A confirma, el procedimiento lanza:

```text
ERROR 1644 (45000): Stock insuficiente
```

- Solo existe una reserva confirmada. No hay sobreventa.

## Verificación y limpieza

```bash
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/11_verify.sql
mariadb -h 127.0.0.1 -u taller -p tallerdb < database/transacciones/12_cleanup.sql
```

`11_verify.sql` muestra precio, stock, reservas y auditoría.
`12_cleanup.sql` elimina el modelo `__TX__`, el usuario temporal y sus registros.

## Notas

- `SET TRANSACTION ISOLATION LEVEL ...` se ejecuta **antes** de `START TRANSACTION`.
- `SELECT SLEEP(5)` solo existe para que puedas ejecutar la otra terminal a tiempo.
- Si ejecutas la sesión B después del `SLEEP`, ya no habrá bloqueo; repite el reset.
- En MariaDB, SERIALIZABLE convierte los `SELECT` normales en lecturas con
  bloqueo de rango. Es más estricto, pero reduce la concurrencia.
- Los procedimientos no hacen `COMMIT`: la transacción la controla el llamador.
