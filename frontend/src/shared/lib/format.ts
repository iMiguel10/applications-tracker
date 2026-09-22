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
  const money = new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  });
  if (min !== null && max !== null) return `${money.format(min)} – ${money.format(max)}`;
  return min !== null ? `≥ ${money.format(min)}` : `≤ ${money.format(max!)}`;
}
