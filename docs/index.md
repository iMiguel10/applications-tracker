# Applications Tracker

Aplicación para registrar y seguir las solicitudes a puestos de trabajo: cada candidatura, su historial de estados, sus entrevistas y el próximo paso. Es un proyecto de portfolio que además se usa de verdad.

!!! success "Estado"
    Todas las fases del plan están construidas: el MVP (F0–F6 y F8), la v2 (F9–F17: infraestructura de segundo plano, manual de producción, cuenta y protección, avisos por email, documentos, perfil y CVs generados, IA, tablero Kanban y calendario) y la puesta en producción (F7, cerrada el 2026-10-19 sobre un Coolify propio con un solo dominio, copias de seguridad programadas y despliegue continuo desde la CI; [0023](decisiones/0023-produccion-en-coolify-con-un-solo-dominio.md)). El orden de construcción no siguió la numeración: F6 antes que F5 ([0006](decisiones/0006-ci-antes-que-f5.md)), F8 antes que F7 ([0009](decisiones/0009-f8-antes-que-f7.md)) y F16 y F17 antes que F15 ([0014](decisiones/0014-f16-y-f17-antes-que-f15.md)). La suscripción ICS de F17 se descartó ([0016](decisiones/0016-sin-suscripcion-ics.md)).

## En una página

| | |
|---|---|
| **Qué resuelve** | Que ninguna candidatura se olvide y que se vea de un vistazo cómo va la búsqueda |
| **Para quién** | Una persona en búsqueda activa, con sus datos privados |
| **Stack** | FastAPI · SQLAlchemy async · PostgreSQL 17 · SuperTokens · React 19 · TypeScript · Vite · Docker |
| **Técnica** | Monolito en capas, máquina de estados con historial append-only, aislamiento entre usuarios en dos capas |
| **Naturaleza** | Portfolio + uso propio: rigor en el núcleo técnico, lo comercial pospuesto `[C]` |

## Por dónde empezar

- [Especificación](producto/especificacion.md): qué hace el producto, sus requisitos numerados, el ciclo de vida de una solicitud y lo que **no** sabe responder.
- [Arquitectura](arquitectura/index.md): las decisiones con sus alternativas descartadas, el modelo de datos, los flujos y las invariantes.
- [Servicios y estructura](arquitectura/servicios-y-estructura.md): qué corre en Docker, cómo se organiza el código y qué puede hacer cada capa.
- [Autenticación](arquitectura/autenticacion.md): la integración con SuperTokens y sus trampas.
- [Arquitectura de la v2](arquitectura/v2.md): el diseño de la siguiente versión, con un documento por tema (segundo plano y emails, ficheros, IA, límites y abuso). Construidas de F9 a F17; F7 (producción en Coolify), cerrada.
- [Decisiones](decisiones/index.md): la bitácora de cambios de rumbo durante el desarrollo.

## Las tres ideas que sostienen el diseño

1. **El historial manda.** El estado de una solicitud es una copia del último cambio de su historial append-only. Las transiciones solo las valida el backend, y se puede deshacer porque nada se sobrescribe.
2. **Nada es de nadie más.** Cada consulta filtra por el usuario de la sesión y la base de datos impide, con claves foráneas compuestas, enlazar datos de dos usuarios. Un recurso ajeno responde igual que uno inexistente.
3. **El sistema solo sabe lo que le cuentan.** Las métricas dicen sobre cuántas solicitudes se calculan, y una candidatura sin respuesta aparece como "sin actividad", nunca como descartada.

## Cómo se mantiene esta documentación

- La fuente vive en `docs/` junto al código y **cambia en el mismo commit** que el código que describe.
- Los diagramas son texto (Mermaid), no imágenes.
- La referencia de la API no se escribe a mano: se genera del contrato OpenAPI de FastAPI.
- Si el código y un documento no coinciden, no se corrige el documento sin más: primero se averigua si el diseño evolucionó o si la implementación se lo saltó.
