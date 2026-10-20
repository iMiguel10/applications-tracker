import type { SidebarsConfig } from "@docusaurus/plugin-content-docs";

// Generado por docusaurus-plugin-openapi-docs a partir de docs/referencia/openapi.json
// (npm run gen-api, que corre antes de start y build). No se versiona. Exporta
// directamente la lista de elementos de la barra lateral.
import apiReference from "./docs/api/referencia/sidebar";

const sidebars: SidebarsConfig = {
  // Tareas del usuario, no pantallas (manual de uso, RNF-33).
  uso: [
    "index",
    "uso/primeros-pasos",
    "uso/registrar-una-solicitud",
    "uso/seguir-el-estado",
    "uso/tablero",
    "uso/entrevistas",
    "uso/recordatorios",
    "uso/calendario",
    "uso/encontrar-solicitudes",
    "uso/archivar-y-borrar",
    "uso/dashboard",
    "uso/documentos",
    "uso/perfil",
    "uso/generar-un-cv",
    "uso/adaptar-el-cv-con-ia",
    "uso/escribir-una-carta-con-ia",
    "uso/usar-tu-propia-clave-de-ia",
    "uso/exportar",
    "uso/preferencias",
    "uso/borrar-la-cuenta",
  ],
  despliegue: [
    "despliegue/index",
    "despliegue/requisitos",
    "despliegue/coolify",
    "despliegue/sin-coolify",
    "despliegue/variables",
    "despliegue/cuentas",
    "despliegue/correo",
    "despliegue/ia-de-la-plataforma",
    "despliegue/copias-de-seguridad",
    "despliegue/despliegue-continuo",
    "despliegue/actualizar",
    "despliegue/obligaciones",
  ],
  api: [
    "api/guia",
    {
      type: "category",
      label: "Referencia",
      collapsed: false,
      items: apiReference,
    },
  ],
};

export default sidebars;
