// Comprueba que cada página del manual existe en los dos idiomas (RNF-33).
// Una página en un solo idioma es un fallo, no un pendiente: Docusaurus no lo
// detecta, porque muestra la versión española cuando falta la traducción.
import { readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const SOURCE = "docs";
const TRANSLATION = "i18n/en/docusaurus-plugin-content-docs/current";
// Generada del OpenAPI y en español a propósito en los dos idiomas.
const GENERATED = "api/referencia";

function pages(root) {
  const found = [];
  (function walk(dir) {
    for (const name of readdirSync(dir)) {
      const path = join(dir, name);
      if (statSync(path).isDirectory()) walk(path);
      else if (/\.mdx?$/.test(name)) found.push(relative(root, path).replaceAll("\\", "/"));
    }
  })(root);
  return new Set(found.filter((page) => !page.startsWith(GENERATED)));
}

const spanish = pages(SOURCE);
const english = pages(TRANSLATION);
const missingInEnglish = [...spanish].filter((page) => !english.has(page));
const missingInSpanish = [...english].filter((page) => !spanish.has(page));

if (missingInEnglish.length || missingInSpanish.length) {
  for (const page of missingInEnglish) console.error(`Falta en inglés: ${TRANSLATION}/${page}`);
  for (const page of missingInSpanish) console.error(`Sobra en inglés (no existe en ${SOURCE}/): ${page}`);
  process.exit(1);
}
console.log(`${spanish.size} páginas, todas en español y en inglés.`);
