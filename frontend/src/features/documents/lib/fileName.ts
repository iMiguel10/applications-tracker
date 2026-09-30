/** Nombre al descargar: el visible, siempre acabado en `.pdf`, como la API. */
export function downloadName(name: string): string {
  return name.toLowerCase().endsWith(".pdf") ? name : `${name}.pdf`;
}
