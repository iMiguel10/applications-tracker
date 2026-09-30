# 0012 — El canal de un aviso va en la entrega, no en el recordatorio

- **Fecha:** 2026-09-30
- **Estado:** aceptada

## Contexto

En el MVP (F4), los recordatorios dejaron puesta una costura para avisar algún día por otros medios (RF-53): una columna `channel` en cada recordatorio (siempre `in_app`), un campo `sent_at` y una interfaz `NotificationChannel` con una sola implementación, `InAppChannel`, que no hacía nada. `ReminderService` la llamaba **al crear** el recordatorio. El diseño de la v2 preveía que el email fuera su segunda implementación, un `EmailChannel`.

Al construir el aviso de recordatorio vencido (RF-80, F12 paso 2) el aviso resultó ser otra cosa:

- Salta **al vencer** el recordatorio, a veces semanas después de crearlo, y lo dispara un barrido del `worker`, no la petición que lo crea.
- Lo decide **la cuenta** (`notify_reminder_due`, RF-84), no cada recordatorio.
- Es uno de cuatro avisos. Los otros tres (entrevista, resumen semanal, sin actividad) no tienen nada que ver con un recordatorio.
- La pieza que hace el trabajo ya existía desde el paso 1: las entregas ("nunca dos veces") y un `NotificationComposer` por tipo de aviso.

Al preguntar qué supondría añadir más adelante Telegram, Slack o WhatsApp, quedó claro dónde importa el canal: **al entregar**. Un mismo motivo avisado por email y por Telegram son dos entregas. Con la clave única del paso 1, `(usuario, tipo, motivo)`, la segunda chocaría con la primera y no saldría nunca.

## Decisión

- Se **quita** la costura de F4: `services/notifications/` (`NotificationChannel`, `InAppChannel`) y su llamada en `ReminderService.create`. No hacía nada y un canal futuro tampoco la usaría.
- Se pone la costura donde se usa: `notification_deliveries.channel` (`DeliveryChannel`, hoy solo `email`), dentro de la clave única, que pasa a ser `(user_id, kind, channel, dedupe_key)`. Se añadió en la migración del paso 1 (`f58741a45d81`), que aún no se había publicado.
- Los cuatro avisos pasan por el mismo camino: barrido → reclamo → `send_notification` → compositor del tipo → `EmailSender`.
- `reminders.channel` y `reminders.sent_at` se quedan como están, sin uso: quitarlos es una migración que hoy no aporta nada. Cuándo salió un aviso lo guarda su entrega.

## Qué supondría un canal nuevo (Telegram, Slack, WhatsApp)

1. **Conectar la cuenta del canal**: un flujo propio y una tabla con la dirección (`chat_id` de Telegram, usuario de Slack, teléfono de WhatsApp) y si está confirmada. El email no lo necesita porque viene de SuperTokens.
2. **Preferencias por canal**: de un interruptor por aviso a una tabla de avisos por canales.
3. **Un emisor en `infra/`** detrás de una interfaz, como `EmailSender`, que clasifique los fallos en "no salió" y "no se sabe". Y, entonces sí, una interfaz de canal de entrega con dos implementaciones.
4. **Textos por canal**: un mensaje de Telegram no es un email con asunto y HTML.
5. **Baja desde el propio canal.**
6. **Un valor más en `DeliveryChannel`** con su migración (el CHECK de la columna lo exige). Los barridos, el reclamo, los estados y los reintentos no cambian.

WhatsApp Business además **cobra por mensaje** y exige plantillas aprobadas: necesitaría un límite con coste, como la IA (límites y abuso §1).

## Alternativas descartadas

- **Adaptar `NotificationChannel` y crear un `EmailChannel`.** Cumplía el diseño original, pero había que cambiar cuándo se llama la interfaz. Además, añadía una capa que por dentro llamaría a lo mismo que los compositores, servía para uno solo de los cuatro avisos y hacía chocar el `channel` de cada recordatorio con la preferencia de la cuenta.
- **Dejar la costura sin usar.** No tocaba el MVP, pero dejaba dos cosas llamadas "canal" con significados distintos, una de ellas muerta.
- **Construir ya la interfaz de canal de entrega.** Con una sola implementación sería adivinar cómo será la segunda. La columna y `EmailSender` detrás de su interfaz bastan para que añadirla sea un cambio localizado.

## Consecuencias

- `ReminderService` ya no recibe un canal. Su prueba de la costura desaparece con ella.
- La especificación (RF-53 y los puntos de extensión) y la arquitectura dejan de hablar de `EmailChannel`: el email es el primer valor de `DeliveryChannel`.
