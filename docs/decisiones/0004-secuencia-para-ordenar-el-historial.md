# 0004 — El historial de estados se ordena por una columna de secuencia

- **Fecha:** 2026-09-22
- **Estado:** aceptada · afecta a F3 (aún no implementado)

## Contexto

El historial de estados (`application_status_changes`) es la fuente de verdad del estado de una solicitud: `applications.status` es una copia del `to_status` del **último** cambio, y *deshacer* borra precisamente ese último cambio (arquitectura §4).

Hasta ahora, "el último" se definía como el de `created_at` mayor. La [decisión 0001](0001-clock-timestamp-en-created-at.md) ya corrigió un problema previo (`now()` daba la misma hora a todas las filas de una transacción) pasando a `clock_timestamp()`, pero dejó abierto un riesgo: `clock_timestamp()` lee el **reloj del sistema**, que puede retroceder (un ajuste de NTP, un cambio manual de hora, una máquina virtual que se reanuda). Si el reloj retrocede entre dos cambios de estado, el registrado después tendría una hora anterior y *deshacer* borraría el cambio equivocado, dejando `status` desincronizado del historial.

## Decisión

`application_status_changes` tendrá una columna **`seq bigint GENERATED ALWAYS AS IDENTITY`**, y el orden del historial y la elección del "último" cambio se harán por `seq`, no por `created_at`.

- `seq` lo genera una secuencia de Postgres: siempre crece y no depende del reloj.
- El índice pasa a ser `(application_id, seq DESC)`.
- `created_at` se conserva como dato informativo ("cuándo se registró"), y `changed_at` sigue siendo la fecha real declarada por el usuario, que alimenta las métricas.
- El cambio de estado seguirá bloqueando la solicitud con `SELECT … FOR UPDATE`: eso es lo que serializa dos cambios simultáneos sobre la misma solicitud, y garantiza que el orden de `seq` coincide con el orden real de los cambios de esa solicitud.

Cambia la **invariante 3**: `applications.status` es igual al `to_status` del cambio con el `seq` más alto de esa solicitud.

## Alternativas descartadas

- **Seguir con `created_at`** (`clock_timestamp()`): correcto el 99,9 % del tiempo, pero su fallo es silencioso y justo en la operación más delicada (*deshacer*). Una columna de secuencia cuesta una línea en el modelo.
- **Ordenar por `created_at` y desempatar por `id`**: los UUID v4 son aleatorios y no reflejan el orden de inserción, así que el desempate sería arbitrario.
- **UUID v7 como clave primaria** (ordenables por tiempo): también dependen del reloj, y cambiaría el tipo de clave de una sola tabla respecto al resto del modelo.

## Consecuencias

- El orden del historial deja de depender del reloj del sistema.
- `seq` es único por tabla, no por solicitud: los números de una solicitud no son consecutivos (1, 5, 9…). Es irrelevante para ordenar, pero **no debe mostrarse** como "cambio número N" en la interfaz.
- La secuencia avanza aunque una transacción se revierta, así que puede haber huecos. También es irrelevante para el orden.
- Afecta solo a F3: la tabla no existe todavía, así que no hace falta migrar nada.
