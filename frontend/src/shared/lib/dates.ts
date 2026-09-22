import { format, isValid, parse } from "date-fns";

const DATE_ONLY_FORMAT = "yyyy-MM-dd";

/**
 * Convierte "yyyy-MM-dd" (campo `date` de la API) en un Date a medianoche LOCAL.
 *
 * No usar new Date("2026-09-01"): lo interpreta como medianoche UTC y, en una zona
 * al oeste de UTC, eso es el día anterior (el error de "un día menos", riesgo R6).
 */
export function parseDateOnly(value: string | null | undefined): Date | undefined {
  if (!value) return undefined;
  const date = parse(value, DATE_ONLY_FORMAT, new Date());
  return isValid(date) ? date : undefined;
}

/** Date → "yyyy-MM-dd" con la fecha LOCAL (no la de UTC, que puede ser otro día). */
export function toDateOnly(date: Date): string {
  return format(date, DATE_ONLY_FORMAT);
}
