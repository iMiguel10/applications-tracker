# 0016 — Sin suscripción ICS: eventos sueltos generados en el navegador

- **Fecha:** 2026-10-02
- **Estado:** aceptada

## Contexto

F17 incluía dos formas de llevar las entrevistas y los recordatorios a otro calendario: la **suscripción ICS** (RF-132, RF-134), un enlace privado por usuario que Google, Outlook o Apple vuelven a pedir cada cierto tiempo, y **añadir un evento suelto** (RF-133), con un enlace a Google Calendar o un `.ics`. El diseño de la suscripción ya estaba hecho (A40, la tabla `calendar_feeds`, el endpoint público `GET /calendar/{token}.ics` y su rate limit por token, en `v2.md` y `limites-y-abuso.md`).

Al detallarla antes de construirla, el usuario la descartó: **no aporta tanto valor** como para mantener lo que cuesta. Es solo de lectura, Google tarda horas en refrescarla y exige un endpoint público autenticado solo por un token secreto (con su lista blanca en T1, su rate limit y el riesgo de que el token acabe en un log), una tabla nueva y una URL que, guardando solo su hash, únicamente se puede ver al crearla.

## Decisión

- **No se construye la suscripción ICS.** RF-132 y RF-134 pasan a descartados; A40, `calendar_feeds`, el feed público y la prueba L8 quedan en los documentos como diseño no construido, con un enlace a esta decisión.
- **RF-133 se hace entero en el navegador**, sin endpoint: el frontend ya tiene todos los datos del evento. `features/calendar/lib/addToCalendar.ts` genera el enlace de Google Calendar y el `.ics` (RFC 5545: identificador fijo por evento, horas en UTC, escape de texto y líneas plegadas a 75 octetos). Sin la suscripción, compartir el generador con el backend ya no justificaba un endpoint ni la librería `icalendar`.
- **Solo Google Calendar como atajo**, además del `.ics`, que importa cualquier calendario (Outlook, Apple, Thunderbird…). Decisión del usuario.
- El evento lleva título, horas, tipo, formato, entrevistadores y un enlace a la solicitud, **nunca las notas**: son privadas y el calendario externo quizá se comparta. Para llevar los entrevistadores, `GET /calendar/events` los devuelve desde ahora.
- El menú **Añadir al calendario** está en los eventos de la vista semana (y de la agenda del móvil), en las entrevistas del detalle de la solicitud (salvo las canceladas) y en los recordatorios pendientes, tanto del detalle como de la página Recordatorios.

## Alternativas descartadas

- **Construir la suscripción como estaba diseñada**: es lo que se descarta, por el coste frente al valor.
- **Generar el `.ics` de un evento suelto en el backend** (`GET /calendar/events/{kind}/{id}.ics` con `icalendar`): solo tenía sentido para compartir el generador con la suscripción. Sin ella, es un endpoint, una dependencia y una petición más para lo que el navegador ya sabe.
- **Atajos para Outlook.com, Microsoft 365 y Yahoo**: existen enlaces equivalentes al de Google, pero Microsoft no documenta los suyos y alguna vez los ha cambiado, y el `.ics` ya cubre esos calendarios. Se pueden añadir más adelante sin tocar nada más: son otra función como `googleCalendarUrl`.

## Consecuencias

- Un evento añadido a otro calendario es una **copia**: si la entrevista se mueve en la app, en el otro calendario sigue a la hora antigua. Importar de nuevo su `.ics` la actualiza (mismo `UID`); el enlace de Google crea otro evento.
- No hay ningún endpoint público nuevo: la lista blanca de T1 sigue igual (`health`, `meta` y la baja de avisos).
- El riesgo R12 (fuga del enlace del calendario) desaparece.
- La suscripción queda en la "evolución documentada que no se construye" de la especificación; si algún día se retoma, su diseño sigue en `v2.md` y `limites-y-abuso.md`.
