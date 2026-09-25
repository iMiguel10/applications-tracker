/** Cuánto esperar tras un 429, en palabras del idioma: "dentro de 42 segundos",
 * "in 5 minutes". Con segundos por debajo del minuto y minutos redondeados hacia
 * arriba a partir de ahí, para no prometer menos espera de la real. */
export function formatRetryAfter(seconds: number, locale: string): string {
  const format = new Intl.RelativeTimeFormat(locale, { numeric: "always" });
  if (seconds < 60) return format.format(Math.max(1, Math.ceil(seconds)), "second");
  return format.format(Math.ceil(seconds / 60), "minute");
}
