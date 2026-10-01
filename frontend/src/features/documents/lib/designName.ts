import type { CvDesign } from "../types/Document";

/** Nombre de un diseño de CV en el idioma de la interfaz; su clave si el catálogo
 * aún no ha llegado o ya no lo tiene (un CV generado con un diseño retirado). */
export function designName(design: CvDesign | undefined, key: string, language: string): string {
  if (!design) return key;
  return design.names[language] ?? design.names.en ?? key;
}

/** El idioma de la interfaz reducido a los de los diseños. */
export const uiCvLanguage = (language: string) => (language.startsWith("en") ? "en" : "es");
