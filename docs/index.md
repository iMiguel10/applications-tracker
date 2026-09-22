# Applications Tracker

Aplicación para registrar y seguir las solicitudes a puestos de trabajo.

!!! warning "Estado"
    Fase de diseño. Solo existe el entorno Docker de desarrollo y un endpoint de salud; la especificación de producto y la arquitectura se están redactando.

## Cómo se mantiene esta documentación

- La fuente vive en `docs/` junto al código y **cambia en el mismo commit** que el código que describe.
- Los diagramas son texto (Mermaid), no imágenes.
- La referencia de la API no se escribe a mano: se genera del contrato OpenAPI de FastAPI.
- Si el código y un documento no coinciden, no se corrige el documento sin más: primero se averigua si evolucionó el diseño o si la implementación se lo saltó.
