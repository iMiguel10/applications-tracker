# 0015 — El cambio inicial de una solicitud enviada lleva su fecha de envío

- **Fecha:** 2026-10-01
- **Estado:** aceptada

## Contexto

Al crear una solicitud, su cambio inicial del historial (`from_status = NULL`) se fechaba siempre "ahora", también cuando se registraba como **Enviada** con una fecha de envío anterior. Pero `changed_at` es **cuándo ocurrió**, no cuándo se registró ([arquitectura](../arquitectura/index.md#estado-actual-historial-de-estados), "Una secuencia y dos fechas"). Lo destapó el `qa-verifier` de F16: una candidatura enviada el día 20 y apuntada el 1 salía en el tablero como "Desde hoy en este estado" (RF-120), y el historial decía "Enviada · 1 oct".

Tenía otro efecto: como un cambio no puede ser anterior al último registrado, tampoco se podía apuntar una respuesta de la semana pasada a una candidatura registrada hoy (422 `changed_at_before_last_change`).

## Decisión

- **Al crear** una solicitud como `applied` con una fecha de envío pasada, el cambio inicial lleva ese día **a la hora actual en la zona del usuario** (UTC si no tiene), el mismo criterio que "Cuándo ocurrió" al cambiar de estado: medianoche pintaría "0:00" en el historial. Si el día es hoy o futuro, es ahora: un cambio nunca está en el futuro. `saved` siempre es ahora. La regla vive en `domain/application_status.py` (`initial_change_at`).
- **Al editar `applied_at`**, el cambio inicial la sigue solo mientras sea el **único** del historial y esté en `applied`. Con cambios posteriores no se toca: el historial no puede quedar desordenado, y lo que pasó después ya tiene sus fechas. La edición bloquea la solicitud (`SELECT … FOR UPDATE`, como un cambio de estado) para que un cambio simultáneo no quede antes que el inicial.
- **Sin migración** de los datos existentes, por decisión del usuario: solo cambia lo que se crea o edita desde ahora.
- `last_activity_at` **no cambia**: sigue siendo el momento del registro.

## Alternativas descartadas

- **Usar la fecha de envío solo para pintar los días del tablero**: más barato, pero el historial seguiría mostrando una fecha falsa y seguiría sin poder apuntarse una respuesta anterior al registro.
- **Medianoche del día de envío**: el historial muestra fecha y hora, y "0:00" parece un dato inventado.
- **Que la inactividad (RF-64, RF-83) cuente desde la fecha de envío**: al pasar al sistema varias candidaturas antiguas, llegaría de golpe un aviso de inactividad por casi todas. Registrar una solicitud ya es actividad.

## Consecuencias

- El tablero, el historial y las métricas de tiempos cuentan desde el día real de envío.
- Se puede registrar una respuesta con una fecha entre el envío y el registro.
- Ningún aviso cambia: ninguno lee la fecha de los cambios de estado. Una solicitud registrada tarde no avisa de inactividad hasta que pasa el umbral desde su registro.
- Las solicitudes creadas antes de esta decisión conservan su cambio inicial con la fecha de registro. Editar su fecha de envío lo corrige si aún no tienen otros cambios.
