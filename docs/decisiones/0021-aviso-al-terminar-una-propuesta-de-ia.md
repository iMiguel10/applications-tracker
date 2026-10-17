# 0021 — Aviso al terminar una propuesta de IA, en la aplicación y por email

- **Fecha:** 2026-10-17
- **Estado:** aceptada

## Contexto

Con Ollama como IA de la plataforma por defecto ([0020](0020-ollama-por-defecto-y-usos-gratuitos-sin-tope.md)), una propuesta de CV tarda 2 o 3 minutos. Hasta ahora la aplicación solo la vigilaba desde el detalle de su solicitud o desde su página de revisión. Si el usuario se iba a otra página, no se enteraba de que había terminado.

El usuario propuso avisar al terminar «por correo si está habilitado o de alguna manera». La API no tiene una forma de pedir las propuestas en curso de todas las solicitudes a la vez.

## Decisión

- **Aviso dentro de la aplicación, siempre** (RF-157). Al pedir una propuesta, la pestaña la apunta (en `sessionStorage`, con el puesto, la empresa y el usuario), y un vigilante montado en `AppLayout` la consulta desde cualquier página mientras siga en curso. Al terminar sale un aviso: lista para revisar (**Revisar**) o el motivo del fallo (**Ver la solicitud**).
  - **También en el detalle de la misma solicitud**, aunque su tarjeta ya se actualice sola: decisión del usuario, porque confirma que ha terminado.
  - No sale en la página de revisión de esa propuesta, que ya lo muestra.
  - Sin propuestas vigiladas no hace ninguna petición.
- **Aviso por email, desactivado por defecto**: un tipo más de los avisos de F12 (`ai_proposal_finished`), con su interruptor en **Avisos por email** (`users.notify_ai_proposal`). Casi siempre se espera en la página y el aviso en la aplicación ya basta; el email es para quien se va. El interruptor solo aparece si la instalación tiene IA.
  - Sigue el patrón de F12: un barrido cada minuto reclama un aviso por propuesta terminada en la última hora, de cuentas verificadas con el aviso activado, y un compositor escribe el email al enviarlo. Nunca sale dos veces.
  - `ai_proposals.finished_at` marca cuándo terminó. Las propuestas anteriores no la tienen, así que activar el aviso nunca envía emails de propuestas antiguas.
  - El email **no lleva el contenido** de la propuesta, solo el puesto, la empresa, el resultado y el enlace: lo propuesto sale del perfil, y así no circula por correo.
  - Avisa también de las propuestas que no salieron (no válidas, rechazadas o fallidas), con el motivo.

## Alternativas descartadas

- **Un endpoint de «propuestas en curso»** que cada página consultara siempre: cubriría otras pestañas y dispositivos, pero haría peticiones aunque no hubiera nada en curso. Para eso ya está el email.
- **Notificaciones del navegador** (las del sistema operativo): piden permiso y no funcionan igual en todos los navegadores. Se pueden añadir más adelante sobre el mismo vigilante.
- **El email activado por defecto:** un email por cada propuesta pedida sería ruido para quien espera en la página.
- **Enviar el email desde el `worker` al terminar la propuesta**, sin barrido: llegaría unos segundos antes, pero saltaría el reclamo de F12, que es lo que impide que salga dos veces si el trabajo se repite.

## Consecuencias

- El aviso en la aplicación no llega a otra pestaña ni a otro dispositivo, ni si se cierra la pestaña mientras se genera.
- El email tarda como mucho un minuto más que el aviso en la aplicación, y necesita SMTP y el email verificado, como todos los avisos.
- Un tipo nuevo de aviso obliga a rehacer el CHECK de `notification_deliveries.kind` en la migración, y al deshacerla se borran antes sus entregas.
