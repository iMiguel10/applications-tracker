# Applications Tracker

Aplicación para registrar y seguir las solicitudes a puestos de trabajo: cada candidatura, su historial de estados, sus entrevistas y el próximo paso. Es un proyecto de portfolio que además se usa de verdad.

!!! warning "Estado"
    En desarrollo. Terminadas F0 (esqueleto vertical), F1 (autenticación), F2 (empresas y solicitudes) y F3 (ciclo de vida: historial de estados, transiciones y deshacer); la siguiente es F4, entrevistas y recordatorios.

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
