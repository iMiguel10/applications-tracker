# 0014 — F16 y F17 se construyen antes que F15

- **Fecha:** 2026-10-01
- **Estado:** aceptada

## Contexto

Con F14 cerrada, la siguiente fase en el orden de la [especificación](../producto/especificacion.md#11-alcance-por-fases) era F15 (IA: CV y carta adaptados a una oferta, cuota gratuita y claves propias). F15 es la fase con más decisiones abiertas: qué proveedores se habilitan, qué modelo usa la clave de la plataforma, cuántos usos gratuitos tiene cada cuenta y qué tope de gasto global se fija, valores que el diseño ([IA](../arquitectura/ia.md)) deja para cuando se conozcan los precios reales. La especificación ya preveía que F16 (tablero Kanban) y F17 (calendario y suscripción ICS) no dependen de F12–F15 y pueden adelantarse. El usuario pidió dejar F15 para el final, como ya se hizo al adelantar F6 ([0006](0006-ci-antes-que-f5.md)) y F8 ([0009](0009-f8-antes-que-f7.md)).

## Decisión

Se construyen F16 y después F17 antes que F15. F15 queda como la última fase de la v2 y conserva su diseño y sus decisiones pendientes.

Decisiones del usuario para F16, al empezarla:

- El tablero es **otra vista de Solicitudes**, con un selector Lista/Tablero, no una página nueva en el menú: comparte filtros y URL con el listado (RF-122) y el menú no crece.
- **Soltar una tarjeta cambia el estado al momento**, con fecha "ahora" y **Deshacer** en el aviso, sin diálogo. Quien quiera nota o fecha usa "Mover a…", que abre el diálogo de cambio de estado de siempre.

## Alternativas descartadas

No aplica: el orden lo fijó el usuario directamente.

## Consecuencias

- F16 y F17 no usan nada de F15: el tablero reutiliza las transiciones y el cambio de estado del MVP, y el calendario, la zona horaria de F11 y los recordatorios y entrevistas.
- Las decisiones de F15 (proveedores, modelo, cuota, tope) se toman más tarde, con precios y versiones de los SDK de IA más recientes. Antes de construirla hay que volver a comprobar que esos SDK siguen mantenidos.
- La tabla de fases de la especificación no se reordena: describe alcance, no el orden de construcción (como en 0006 y 0009). El orden real queda en el estado de `CLAUDE.md` y en esta entrada.
