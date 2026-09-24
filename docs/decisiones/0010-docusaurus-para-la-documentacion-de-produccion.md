# 0010 — Docusaurus para la documentación de producción

- **Fecha:** 2026-09-24
- **Estado:** propuesta (se acepta al construir F10)

## Contexto

La decisión fundacional [A17](../arquitectura/index.md#1-decisiones) eligió MkDocs Material y descartó Docusaurus porque "metería un segundo ecosistema Node solo para documentar". Ese sitio está pensado para quien trabaja en el código: arquitectura, decisiones, trampas.

La v2 añade un público distinto: quien **usa** la herramienta y quien la **despliega**. El usuario pidió explícitamente Docusaurus para ese público, con tres partes: despliegue en producción, manual de uso y referencia de la API de todo el sistema, en español e inglés (RNF-33).

## Decisión

Se añade un segundo sitio con Docusaurus en `manual/`, con i18n (es, en) y la referencia de la API generada desde el mismo `docs/referencia/openapi.json` que ya exporta el backend. MkDocs **se queda** como documentación de desarrollo: A17 no se sustituye, se acota a ese público.

## Alternativas descartadas

- **Un solo sitio MkDocs para todo**, con un plugin de i18n (`mkdocs-static-i18n`): técnicamente viable, pero mezcla en la misma navegación la guía de uso y las trampas de implementación, y la traducción de las páginas de desarrollo no aporta nada.
- **Mantener el argumento de A17**: era más débil de lo que parecía. El frontend ya es React con npm, así que Docusaurus no introduce un ecosistema nuevo en el repositorio, solo un proyecto más dentro del mismo.

## Consecuencias

- Dos sitios que mantener, uno en dos idiomas (R14). El agente documentador los mantiene en el mismo commit que el código.
- La referencia de la API sigue sin escribirse a mano: los dos sitios la generan del mismo contrato.
- El CI construye también el manual; su tiempo de build se vigila.
