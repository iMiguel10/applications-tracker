// Comprueba que cada página del manual que enlaza la ayuda de la aplicación existe en
// los dos idiomas (issue #6). La lista vive en el frontend
// (frontend/src/shared/config/manualPages.ts): si se renombra o se borra una página
// del manual sin tocarla, la aplicación enlazaría a un 404 y nada más lo detectaría.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

// Desde manual/ en el host y en la CI; en el contenedor, `compose.yml` monta esa
// carpeta en /frontend/…, que desde /app es la misma ruta relativa.
const PAGES_FILE =
  process.env.MANUAL_PAGES_FILE ?? "../frontend/src/shared/config/manualPages.ts";
const ROOTS = {
  es: "docs",
  en: "i18n/en/docusaurus-plugin-content-docs/current",
};

/** Las rutas de `MANUAL_PAGES`: `clave: "ruta",` dentro del objeto. */
function linkedPages() {
  const source = readFileSync(PAGES_FILE, "utf8");
  const block = source.match(/MANUAL_PAGES = \{([\s\S]*?)\}/);
  if (!block) throw new Error(`No encuentro MANUAL_PAGES en ${PAGES_FILE}`);
  const pages = [...block[1].matchAll(/^\s*(\w+):\s*"([^"]*)",?\s*$/gm)].map(
    ([, key, path]) => ({ key, path }),
  );
  if (pages.length === 0) throw new Error(`MANUAL_PAGES está vacío en ${PAGES_FILE}`);
  return pages;
}

/** La URL de cada página como la publica Docusaurus (routeBasePath "/"): su `slug`
 * si lo tiene; si no, su ruta sin extensión, e `index` es la carpeta. */
function urls(root) {
  const found = new Set();
  (function walk(dir) {
    for (const name of readdirSync(dir)) {
      const path = join(dir, name);
      if (statSync(path).isDirectory()) {
        walk(path);
        continue;
      }
      if (!/\.mdx?$/.test(name)) continue;
      const slug = readFileSync(path, "utf8").match(/^---[\s\S]*?^slug:\s*(\S+)[\s\S]*?^---/m);
      if (slug) {
        found.add(slug[1].replace(/^\/|\/$/g, ""));
      } else {
        const page = relative(root, path).replaceAll("\\", "/").replace(/\.mdx?$/, "");
        found.add(page.replace(/(^|\/)index$/, ""));
      }
    }
  })(root);
  return found;
}

const pages = linkedPages();
const missing = [];
for (const [language, root] of Object.entries(ROOTS)) {
  const published = urls(root);
  for (const { key, path } of pages) {
    if (!published.has(path)) missing.push(`${key}: "${path}" no existe en ${language} (${root})`);
  }
}

if (missing.length) {
  for (const line of missing) console.error(line);
  console.error(`Corrige la página del manual o ${PAGES_FILE}.`);
  process.exit(1);
}
console.log(`${pages.length} páginas enlazadas desde la aplicación, todas en español y en inglés.`);
