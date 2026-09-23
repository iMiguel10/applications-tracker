# 0005 — Los recordatorios no tienen página global en F4

- **Fecha:** 2026-09-23
- **Estado:** aceptada · afecta a F4 (frontend) y a F5

## Contexto

RF-50 permite crear un recordatorio "opcionalmente" ligado a una solicitud, y el modelo de datos (arquitectura §5) ya trata `reminders` como una tabla **raíz** de propiedad `user_id`, con `application_id` opcional: nada en el backend le impide existir sin solicitud ni aparecer en un listado que cruce varias.

RF-52, en cambio, solo pide ver los recordatorios "en el dashboard y en el detalle de la solicitud". El dashboard es F5. Ninguna RF de recordatorios (RF-50…53) pide editarlos ni borrarlos, a diferencia de RF-40 ("añadir, editar y borrar entrevistas"), así que el propio backend de F4 solo tiene crear, listar, completar y descartar.

Con esa lectura, dos interpretaciones eran defendibles para el frontend de F4:

1. Construir ya una página `/reminders` que liste y cree recordatorios sueltos, aprovechando que la API ya lo soporta.
2. Limitar el frontend de F4 a lo que RF-52 pide explícitamente: recordatorios embebidos en el detalle de la solicitud, filtrados por ella.

## Decisión

Se elige la opción 2. En F4, `features/reminders/` solo se usa desde `ApplicationDetailPage`, filtrado por `application_id`; no hay ruta `/reminders` ni entrada en `shared/config/navigation.ts`. El endpoint `GET /reminders` ya admite un listado global (sin `application_id`) y `POST /reminders` ya admite un recordatorio suelto (`application_id: null`) porque el modelo de datos los soporta sin coste adicional, pero hoy ninguna pantalla los usa.

## Alternativas descartadas

- **Página `/reminders` ya en F4**: es una lectura válida de RF-50, pero se sale de lo que pide RF-52 para esta fase (dashboard y detalle) y adelanta trabajo de agregación cruzada entre solicitudes que es, en esencia, el problema que resuelve F5. Construirla dos veces (una vista simple ahora, la vista real del dashboard después) es el coste que se evita.

## Consecuencias

- Un recordatorio sin solicitud asociada solo se puede crear hoy con la API directamente (Swagger o un cliente propio), no desde la interfaz. Es una limitación real del alcance de F4, documentada aquí para que no se lea como un olvido.
- F5 tiene que añadir, para cerrar el círculo: la ruta `/reminders` (o la vista equivalente dentro del dashboard), su entrada de navegación, y decidir si la interacción con recordatorios sueltos necesita algo más que crear/completar/descartar (F4 no incluyó PATCH ni DELETE porque ninguna RF los pedía; si la página global lo necesita, es una ampliación de alcance de F5, no de F4).
- El backend no cambia: ya está preparado para esa vista.
