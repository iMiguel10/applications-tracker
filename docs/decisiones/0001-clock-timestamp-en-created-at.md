# 0001 — `clock_timestamp()` en lugar de `now()` para `created_at`

- **Fecha:** 2026-09-22
- **Estado:** aceptada

## Contexto

La arquitectura (§5) definía `created_at timestamptz NOT NULL DEFAULT now()` en todas las tablas y usaba `created_at` para ordenar: el listado de solicitudes y, sobre todo, el historial de estados. Deshacer toma "el último cambio por `created_at`" (invariante 3).

En F0, un test de API que creaba dos solicitudes y esperaba la más reciente primero falló de forma no determinista. El motivo: en Postgres, `now()` es `transaction_timestamp()`, la hora de **inicio de la transacción**, no la del `INSERT`. Todas las filas escritas en una misma transacción reciben exactamente el mismo `created_at`, y el orden entre ellas queda en manos del desempate (un UUID aleatorio).

Esto afecta a más casos que el test:

- Los tests corren dentro de una transacción externa que se revierte (ver `tests/conftest.py`). Con `now()`, todos los cambios de estado de un test de F3 tendrían la misma hora y "deshacer el último" borraría uno al azar.
- En producción, cualquier service que escriba dos filas ordenables en la misma petición produce el mismo empate.

## Decisión

Todas las columnas `created_at` usan `server_default=func.clock_timestamp()`, que devuelve la hora real en el momento de cada inserción. El desempate por `id` en las consultas ordenadas se mantiene para los empates reales (mismo microsegundo).

## Alternativas descartadas

- **Mantener `now()` y usar la hora de Python (`default=datetime.now`)**: saca de la BD la fuente de la hora. Además, la hora del proceso Python y la de Postgres pueden diferir, y las filas insertadas con SQL directo o desde migraciones no la tendrían.
- **Mantener `now()` y ajustar solo los tests** (commits reales, sin transacción externa): tapa el síntoma en los tests y deja el empate en producción. Además, obliga a limpiar la BD entre tests.
- **Ordenar por `id`**: los UUID v4 son aleatorios y no reflejan el orden de inserción.

## Consecuencias

- `created_at` refleja el instante real de cada fila, incluso dentro de una transacción larga.
- `clock_timestamp()` depende del reloj del sistema, que puede retroceder (ajustes de NTP). Para listados es irrelevante. Para el historial de estados, donde el orden es la fuente de verdad de deshacer, **resuelto en la [decisión 0004](0004-secuencia-para-ordenar-el-historial.md)**: el historial se ordena por una columna de secuencia (`seq`), no por `created_at`.
