# 0009 — F8 se construye antes que F7

- **Fecha:** 2026-09-24
- **Estado:** aceptada

## Contexto

El orden de fases de la [especificación](../producto/especificacion.md#11-alcance-por-fases) sitúa F7 (entonces "preparación para despliegue") antes que F8 (revisión final). Ya existe un precedente de invertir el orden de construcción sin tocar esa tabla de alcance: la decisión [0006](0006-ci-antes-que-f5.md), cuando F6 se construyó antes que F5. El usuario pidió aquí, de la misma forma, construir F8 antes que F7, con el MVP funcional completo (F0–F6) ya cerrado.

## Decisión

Se construye F8 (auditoría de funcionalidades, preferencias de usuario, moneda cerrada, script de rendimiento, borrado de cuenta y diseño de la interfaz) sin haber empezado F7. Al mismo tiempo, F7 cambia de contenido: deja de ser "preparación para despliegue" (`compose.prod.yml`, Nginx, variables de producción, sin desplegar de verdad) y pasa a ser la **puesta en producción real**, con el sistema accesible fuera de local. F7 sigue sin empezar.

## Alternativas descartadas

No aplica: el orden y la redefinición de F7 los fijó el usuario directamente, sin plantear alternativas que evaluar.

## Consecuencias

- F8 no dependía de nada de F7 (una imagen de producción o un despliegue real), así que no hubo bloqueo técnico al invertir el orden.
- Al revisar el diseño de la interfaz y cerrar huecos de funcionalidad (F8) antes de desplegar (F7), lo que llegue a producción ya pasó por esa pasada deliberada, en vez de desplegarse primero y revisarse después.
- La tabla de fases de `docs/producto/especificacion.md` §11 no se reordena: describe alcance, no el orden real de construcción, igual que ya establecía la decisión 0006. El orden real queda constatado en el estado de `CLAUDE.md`, el `README.md` y esta entrada.
- F7, al pasar de "preparación" a "despliegue real", incorpora ahora la variable de si el sistema queda accesible en un dominio público: eso puede traer requisitos nuevos (TLS, backups programados más allá del `pg_dump` manual documentado) que no estaban en su alcance original.
