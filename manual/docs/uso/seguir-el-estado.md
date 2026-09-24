---
title: Seguir el estado de una solicitud
sidebar_label: Cambiar el estado
---

Cada solicitud tiene un estado, y cada cambio queda guardado en su **Historial de estados**.

## Los estados

| Estado | Significa |
|---|---|
| Guardada | Te interesa, pero aún no has enviado la candidatura |
| Enviada | Candidatura enviada, sin respuesta todavía |
| En revisión | La empresa ha respondido: primer contacto o prueba inicial |
| Entrevistas | Proceso de entrevistas en curso |
| Oferta | Tienes una oferta |
| Aceptada | Has aceptado la oferta. **Final** |
| Descartada | La empresa te descarta, o rechazas la oferta. **Final** |
| Retirada | Abandonas el proceso. **Final** |

## Cambiar el estado

1. Abre la solicitud y pulsa **Cambiar estado**.
2. Elige el **Nuevo estado**. Solo aparecen los que tienen sentido desde el actual (ver la tabla de abajo).
3. En **Cuándo ocurrió**, deja **Ahora** o elige la fecha real si estás registrando algo que pasó antes.
4. Si quieres, añade una nota (por ejemplo, "rechacé la oferta por el salario").
5. Pulsa **Cambiar estado** para confirmarlo.

Si pasas a **Enviada** una solicitud que no tenía fecha de envío, se rellena con la fecha del cambio.

La fecha de un cambio no puede ser futura ni anterior al último cambio registrado: el historial siempre va hacia delante.

### Desde cada estado se puede pasar a

| Desde | A |
|---|---|
| Guardada | Enviada, Retirada |
| Enviada | En revisión, Entrevistas, Descartada, Retirada |
| En revisión | Entrevistas, Descartada, Retirada |
| Entrevistas | Oferta, Descartada, Retirada |
| Oferta | Aceptada, Descartada, Retirada |
| Aceptada, Descartada, Retirada | Ninguno: son estados finales |

- Se puede **saltar** estados hacia delante: de Enviada a Entrevistas, si la empresa no hizo una primera revisión.
- **No se retrocede**. Si te equivocaste, deshaz el último cambio (abajo).
- Si una empresa reabre un proceso que estaba cerrado, registra una solicitud nueva o deshaz el cierre.

## Deshacer el último cambio

Para corregir un error, pulsa **Deshacer último cambio** en el historial y confírmalo. Ese cambio desaparece del historial y la solicitud vuelve al estado anterior.

Solo se puede deshacer el cambio más reciente, y nunca el estado inicial con el que se creó la solicitud.
