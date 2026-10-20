import { MANUAL_PAGES, type ManualPage } from "@/shared/config/manualPages";

// En producción el manual va en el mismo dominio (0023); en desarrollo, en su propio
// servidor (`VITE_MANUAL_URL=http://localhost:3001/`), que solo sirve el español.
const DEFAULT_BASE = "/manual/";

/** Base del manual, siempre con barra final. */
export function manualBase(configured: string | undefined): string {
  const base = configured?.trim() || DEFAULT_BASE;
  return base.endsWith("/") ? base : `${base}/`;
}

/**
 * URL de una página del manual en el idioma de la interfaz: el español es el idioma
 * por defecto del manual (en la raíz) y el inglés va bajo `en/`. Cualquier otro
 * idioma cae en el español, como la interfaz.
 */
export function manualUrl(
  page: ManualPage,
  language: string | undefined,
  base = manualBase(import.meta.env.VITE_MANUAL_URL),
): string {
  const prefix = language?.startsWith("en") ? "en/" : "";
  return `${base}${prefix}${MANUAL_PAGES[page]}`;
}
