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

const DATE_TIME_LOCAL_FORMAT = "yyyy-MM-dd'T'HH:mm";

/**
 * Instante ISO (con zona) de la API → valor para `<input type="datetime-local">`,
 * en la hora LOCAL del navegador (F4: entrevistas y recordatorios tienen hora,
 * a diferencia de `applied_at`, que es solo un día).
 */
export function toDateTimeLocal(value: string): string {
  return format(new Date(value), DATE_TIME_LOCAL_FORMAT);
}

/**
 * Valor de `<input type="datetime-local">` (sin zona, "yyyy-MM-ddTHH:mm") → ISO
 * en UTC. Sin zona explícita, `new Date(...)` lo interpreta como hora LOCAL, que es
 * justo lo que muestra el input: no hace falta convertir a mano.
 */
export function datetimeLocalToIso(value: string): string {
  return new Date(value).toISOString();
}
