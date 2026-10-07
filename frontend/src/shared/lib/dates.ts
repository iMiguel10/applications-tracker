import { TZDate } from "@date-fns/tz";
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

/** La zona horaria del navegador (nombre IANA). */
export function browserZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

/**
 * La zona en la que la interfaz muestra y pide las horas: la de la cuenta (RF-07),
 * la misma que usan los emails y el calendario, o la del navegador si no tiene.
 */
export function accountZone(zone: string | null | undefined): string {
  return zone || browserZone();
}

/** El día de hoy ("yyyy-MM-dd") en la zona dada. */
export function todayIn(zone: string, now: Date = new Date()): string {
  return format(new TZDate(now, zone), DATE_ONLY_FORMAT);
}

/**
 * Instante ISO (con zona) de la API → hora de reloj "yyyy-MM-ddTHH:mm" en la zona
 * dada, el valor de `FormDateTimePicker` (F4: entrevistas y recordatorios tienen
 * hora, a diferencia de `applied_at`, que es solo un día).
 */
export function toDateTimeLocal(value: string, zone: string): string {
  return format(new TZDate(new Date(value), zone), DATE_TIME_LOCAL_FORMAT);
}

/**
 * Hora de reloj "yyyy-MM-ddTHH:mm" leída en la zona dada → ISO en UTC. No sirve
 * `new Date(value)`: lo leería en la zona del navegador, que puede no ser la de la
 * cuenta. Una hora que no existe (la que se salta al adelantar el reloj) cae en la
 * siguiente que sí existe.
 */
export function datetimeLocalToIso(value: string, zone: string): string {
  const [day, time] = value.split("T");
  const [year, month, date] = day.split("-").map(Number);
  const [hours, minutes] = time.split(":").map(Number);
  // TZDate escribe toISOString con el desfase de su zona: se pasa por un Date.
  return new Date(new TZDate(year, month - 1, date, hours, minutes, zone).getTime()).toISOString();
}
