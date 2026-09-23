# 0006 — F6 (CI) se construye antes que F5

- **Fecha:** 2026-09-23
- **Estado:** aceptada

## Contexto

El orden de fases de la [especificación](../producto/especificacion.md#11-alcance-por-fases) sitúa F5 (dashboard y exportación CSV) antes que F6 (integración continua). El usuario pidió explícitamente construir F6 antes que F5.

## Decisión

Se construye F6 (`.github/workflows/ci.yml`, con los jobs `backend-lint`, `backend-tests`, `frontend` y `docs`) sin haber empezado F5. F5 sigue pendiente y conserva su alcance íntegro: dashboard, exportación CSV y la página global de recordatorios que anticipaba la decisión [0005](0005-recordatorios-sin-pagina-global-en-f4.md).

## Alternativas descartadas

No aplica: el orden lo fijó el usuario directamente, sin plantear alternativas que evaluar.

## Consecuencias

- F6 no dependía de nada de F5, así que no hubo bloqueo técnico al invertir el orden.
- El CI corre ya contra el código de F0–F4; cuando se construya F5, sus pruebas y su build entran en los mismos jobs existentes sin cambios de estructura.
- La tabla de fases de `docs/producto/especificacion.md` §11 no se reordena: describe alcance, no el orden real de construcción. El orden real queda constatado en el estado de `CLAUDE.md`, el `README.md` y esta entrada.
