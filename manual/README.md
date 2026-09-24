# Manual (documentación de producción)

Sitio Docusaurus para quien **usa**, **despliega** o **se integra** con Applications Tracker, en español (idioma por defecto) e inglés. La documentación de desarrollo es otro sitio: MkDocs, en `docs/` ([decisión 0010](../docs/decisiones/0010-docusaurus-para-la-documentacion-de-produccion.md)).

| Carpeta | Contenido |
|---|---|
| `docs/uso/` | Manual de uso, una página por tarea |
| `docs/despliegue/` | Servicios, variables, correo, copias de seguridad |
| `docs/api/guia.md` | Guía de integración con la API |
| `docs/api/referencia/` | **Generada** de `../docs/referencia/openapi.json` en cada `start` y `build`. No se versiona ni se edita |
| `i18n/en/docusaurus-plugin-content-docs/current/` | Traducción al inglés, con la misma estructura que `docs/` |
| `i18n/en/*.json`, `i18n/es/code.json` | Textos de la navegación en inglés y del tema de OpenAPI en español |

## Trabajar con el manual

```bash
docker compose up manual                                     # http://localhost:3001, en español
docker compose run --rm --service-ports manual npm run start -- --host 0.0.0.0 --port 3000 --poll 1000 --locale en   # en inglés
docker compose run --rm --no-deps manual npm run check-i18n  # cada página en los dos idiomas
docker compose run --rm --no-deps manual npm run build       # build completo, los dos idiomas; falla ante enlaces rotos
```

**El servidor de desarrollo sirve un solo idioma cada vez**: en `http://localhost:3001` el selector de idioma lleva a `/en/`, que da 404 mientras no se arranque con `--locale en`. El build sí genera los dos.

## Reglas

- **Solo lo que existe.** Una función entra en el manual cuando está construida.
- **Tareas, no pantallas.** "Registrar una solicitud", no "La pantalla de solicitudes".
- **Los dos idiomas en el mismo commit.** `npm run check-i18n` falla si una página existe en un solo idioma.
- **La referencia de la API no se escribe a mano.** Si le falta algo, se añade al endpoint o al schema del backend y se regenera `docs/referencia/openapi.json`.
- **Despliegue verificable.** Cada paso es un comando concreto con lo que debe verse si ha ido bien.
- Los nombres de botones y campos se copian de `frontend/src/shared/i18n/locales/{es,en}.json`, para que coincidan con la pantalla.
