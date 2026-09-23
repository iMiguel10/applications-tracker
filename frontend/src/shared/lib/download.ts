/** Dispara la descarga de un blob ya obtenido (RF-70): sin navegar a la API, así
 * las cookies de sesión no dependen de la política SameSite de una navegación
 * cruzada de origen. */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
