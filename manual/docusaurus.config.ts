import type * as Preset from "@docusaurus/preset-classic";
import type { Config } from "@docusaurus/types";
import type * as OpenApiPlugin from "docusaurus-plugin-openapi-docs";
import { themes as prismThemes } from "prism-react-renderer";

// Documentación de PRODUCCIÓN (decisión 0010): uso, despliegue y API, en español
// e inglés. La de desarrollo sigue en MkDocs (docs/). En producción (F7) se sirve
// bajo /manual/ con el mismo Nginx que el frontend: MANUAL_BASE_URL lo ajusta.
const config: Config = {
  title: "Applications Tracker",
  tagline: "Manual de uso, despliegue y API",
  favicon: "img/logo.png",

  url: process.env.MANUAL_URL ?? "http://localhost:3001",
  baseUrl: process.env.MANUAL_BASE_URL ?? "/",

  // Un enlace roto rompe el build, igual que `mkdocs build --strict`.
  onBrokenLinks: "throw",
  onBrokenAnchors: "throw",
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: "throw",
    },
  },

  i18n: {
    defaultLocale: "es",
    locales: ["es", "en"],
    localeConfigs: {
      es: { label: "Español", htmlLang: "es" },
      en: { label: "English", htmlLang: "en" },
    },
  },

  presets: [
    [
      "classic",
      {
        docs: {
          routeBasePath: "/",
          sidebarPath: "./sidebars.ts",
          // Componente del tema de OpenAPI: pinta las páginas generadas de la
          // referencia y deja las demás como un documento normal.
          docItemComponent: "@theme/ApiItem",
        },
        blog: false,
        theme: {
          customCss: "./src/css/custom.css",
        },
      } satisfies Preset.Options,
    ],
  ],

  plugins: [
    [
      "docusaurus-plugin-openapi-docs",
      {
        id: "api",
        docsPluginId: "classic",
        config: {
          app: {
            // Copia derivada del MISMO contrato que versiona el backend y publica
            // MkDocs (docs/referencia/openapi.json), con la URL de la API como
            // servidor: ver scripts/prepare-openapi.mjs. Ni la copia ni la salida
            // se versionan.
            specPath: ".openapi/openapi.json",
            outputDir: "docs/api/referencia",
            // El panel "Send API Request" llamaría a la API desde el origen del
            // manual: CORS no lo permite y mezclaría sesiones. Para probar la
            // API está Swagger (/docs) en la propia API.
            hideSendButton: true,
            sidebarOptions: {
              groupPathsBy: "tag",
              categoryLinkSource: "tag",
            },
          } satisfies OpenApiPlugin.Options,
        },
      },
    ],
  ],

  themes: ["docusaurus-theme-openapi-docs"],

  themeConfig: {
    image: "img/logo.png",
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: "Applications Tracker",
      logo: {
        alt: "Applications Tracker",
        src: "img/logo.png",
      },
      items: [
        { type: "docSidebar", sidebarId: "uso", position: "left", label: "Uso" },
        {
          type: "docSidebar",
          sidebarId: "despliegue",
          position: "left",
          label: "Despliegue",
        },
        { type: "docSidebar", sidebarId: "api", position: "left", label: "API" },
        { type: "localeDropdown", position: "right" },
        {
          href: "https://github.com/iMiguel10/applications-tracker",
          label: "GitHub",
          position: "right",
        },
      ],
    },
    footer: {
      style: "dark",
      copyright: "Applications Tracker",
    },
    // Ejemplos de código de la referencia: curl primero (el mismo formato que la
    // guía de integración); por defecto el tema empieza por C#.
    languageTabs: [
      { highlight: "bash", language: "curl", logoClass: "curl" },
      { highlight: "python", language: "python", logoClass: "python", variant: "requests" },
      { highlight: "javascript", language: "javascript", logoClass: "javascript", variant: "fetch" },
    ],
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ["bash", "json"],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
