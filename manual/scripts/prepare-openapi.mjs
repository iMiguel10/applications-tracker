// Prepara el contrato que consume la referencia de la API del manual.
//
// La fuente es la de siempre, docs/referencia/openapi.json (la exporta el
// backend). Ese contrato no declara `servers` a propósito: así Swagger, servido
// por la propia API, llama a su mismo origen. Pero sin `servers`, el plugin de
// OpenAPI escribe los ejemplos contra el origen del MANUAL (localhost:3001), que
// no es la API. Aquí se añade un servidor con la URL de la API como variable
// editable, en una copia derivada que no se versiona.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const SOURCE = "../docs/referencia/openapi.json";
const TARGET = ".openapi/openapi.json";

const spec = JSON.parse(readFileSync(SOURCE, "utf8"));
spec.servers = [
  {
    url: "{apiUrl}",
    description: "API de tu instalación (API_DOMAIN)",
    variables: {
      apiUrl: {
        default: "http://localhost:8000",
        description: "URL pública de la API, sin barra final",
      },
    },
  },
];

mkdirSync(".openapi", { recursive: true });
writeFileSync(TARGET, JSON.stringify(spec, null, 2));
console.log(`${TARGET} preparado a partir de ${SOURCE}`);
