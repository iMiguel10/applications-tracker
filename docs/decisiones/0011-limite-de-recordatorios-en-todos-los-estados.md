# 0011 — El límite de recordatorios cuenta todos los estados, y los recordatorios se pueden borrar

- **Fecha:** 2026-09-25
- **Estado:** aceptada

## Contexto

Desde el MVP (F4), el límite de recordatorios era de 500 **pendientes**: los hechos y los descartados no contaban. Además, los recordatorios no se podían borrar, porque ninguna RF lo pedía.

Al hacer visibles los límites en F11, el usuario detectó el hueco. Con registro abierto, cualquiera puede crear 500 recordatorios, marcarlos como hechos y repetir sin fin: la tabla crece sin tope y el límite no lo impide. Es justo el abuso que los límites deben frenar (límites y abuso §1).

## Decisión

El límite pasa a contar **los recordatorios en cualquier estado**, con un valor por defecto de **5000**, el mismo que las solicitudes. Se renombra de `pending_reminders` a `reminders` (`LimitKey.REMINDERS`, `LIMIT_REMINDERS`) y conserva el código de error de siempre, `reminders_limit_reached`. Para poder liberar espacio, los recordatorios **se pueden borrar** en cualquier estado: `DELETE /reminders/{id}`, con confirmación en la interfaz.

## Alternativas descartadas

- **Dos límites, pendientes y total.** Mantenía el de 500 pendientes y añadía otro de total. Daba más control, pero el usuario vería dos barras para lo mismo, y el de pendientes ya no protegía de nada que no protegiera el total.
- **Contar todos y purgar automáticamente** los hechos y descartados antiguos (por ejemplo, de más de un año). Evitaba el botón de borrar, pero añadía una tarea programada en el `worker` y borraba historial sin que el usuario lo pidiera.
- **Dejarlo como estaba.** El hueco es real y barato de explotar.

## Consecuencias

- Una cuenta con mucho historial podría llegar al tope sin abusar de nada. Con 5000 es improbable (una búsqueda larga ronda los cientos), y borrar los antiguos, o una excepción con `set_user_limit`, lo resuelve.
- Completar o descartar un recordatorio **ya no libera espacio**; borrarlo, sí. La interfaz y el manual lo dicen.
- Se retira el "sin editar ni borrar" de F4: ahora se pueden borrar, pero editar sigue sin existir.
- `ReminderRepository.count_pending` se sustituye por `count` (todos los estados), que es lo que usa `LimitService`.
