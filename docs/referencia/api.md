# Referencia de la API

Generada del esquema OpenAPI de la aplicación ([`openapi.json`](openapi.json)); **no se edita a mano**. Cómo se documenta un endpoint, cómo se regenera este fichero y cómo autenticarse está en la guía [Documentar y usar la API](../guias/documentar-la-api.md).

!!! tip "Para probar las rutas"
    Esta página es de solo lectura. Para ejecutar peticiones reales, usa Swagger en la API en marcha: <http://localhost:8000/docs>.

<div id="swagger-ui"></div>

<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
  window.addEventListener("load", function () {
    SwaggerUIBundle({
      url: "../openapi.json",
      dom_id: "#swagger-ui",
      // Solo lectura: el sitio de documentación no lanza peticiones.
      supportedSubmitMethods: [],
      defaultModelsExpandDepth: 0,
      docExpansion: "list",
    });
  });
</script>
