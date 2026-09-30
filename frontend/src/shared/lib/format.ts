import { parseDateOnly } from "@/shared/lib/dates";

/** Fecha sin hora ("yyyy-MM-dd") en el formato del idioma. Nunca new Date(value): ver parseDateOnly. */
export function formatDateOnly(value: string | null, locale: string): string {
  const date = parseDateOnly(value);
  return date ? new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(date) : "—";
}

/** Instante ISO (UTC) en la hora local del navegador. */
export function formatDateTime(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value),
  );
}

export function formatSalaryRange(
  min: number | null,
  max: number | null,
  currency: string,
  locale: string,
): string | null {
  if (min === null && max === null) return null;
  // narrowSymbol: el símbolo por defecto solo existe para el euro en locale es; sin
  // esto, la libra se mostraba como el código "GBP" en vez de "£" (el franco suizo
  // sigue mostrándose como "CHF": no tiene símbolo propio, ni en Suiza).
  const money = new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    currencyDisplay: "narrowSymbol",
    maximumFractionDigits: 0,
  });
  if (min !== null && max !== null) return `${money.format(min)} – ${money.format(max)}`;
  return min !== null ? `≥ ${money.format(min)}` : `≤ ${money.format(max!)}`;
}

const BYTE_UNITS = ["kilobyte", "megabyte", "gigabyte"] as const;

/** Tamaño de un fichero o del almacenamiento ("1,5 MB"). Múltiplos de 1024, como
 * el límite del backend (100 MB = 100 × 1024 × 1024 bytes). */
export function formatBytes(bytes: number, locale: string): string {
  // Los bytes sueltos, a mano: Intl escribe "0 byte" en inglés o "0B" pegado.
  if (bytes < 1024) return `${new Intl.NumberFormat(locale).format(bytes)} B`;
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < BYTE_UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return new Intl.NumberFormat(locale, {
    style: "unit",
    unit: BYTE_UNITS[unit],
    unitDisplay: "short",
    maximumFractionDigits: 1,
  }).format(value);
}
