# Applications Tracker

Aplicación para registrar y seguir las solicitudes a puestos de trabajo: cada candidatura, su historial de estados, sus entrevistas y el próximo paso. Es un proyecto de portfolio que además se usa de verdad.

!!! warning "Estado"
    En desarrollo. Terminadas F0 (esqueleto vertical), F1 (autenticación), F2 (empresas y solicitudes), F3 (ciclo de vida: historial de estados, transiciones y deshacer), F4 (entrevistas y recordatorios), F5 (dashboard, exportación CSV y listado global de recordatorios), F6 (integración continua) y F8 (revisión final); sigue pendiente F7, ahora la puesta en producción real, en espera de servidor. La **v2** (F9–F17: CVs, IA, emails, calendario…) está especificada y diseñada; de ella están construidas F9, la infraestructura (correo, cola de trabajos con su worker, almacén de ficheros y generación de PDF), que todavía no usa ninguna funcionalidad, y F10, el manual de producción en Docusaurus (`manual/`, en español y en inglés). F6 se construyó antes que F5 por decisión explícita ([0006](decisiones/0006-ci-antes-que-f5.md)), no porque F5 ya no hiciera falta, y F8 se construyó antes que F7 por otra decisión explícita ([0009](decisiones/0009-f8-antes-que-f7.md)).

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
- [Arquitectura de la v2](arquitectura/v2.md): el diseño de la siguiente versión, con un documento por tema (segundo plano y emails, ficheros, IA, límites y abuso). Construida la infraestructura (F9); las funcionalidades, todavía no.
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
