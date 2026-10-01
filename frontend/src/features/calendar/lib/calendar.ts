import { TZDate } from "@date-fns/tz";
import {
  addDays,
  addMonths,
  addWeeks,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isValid,
  parse,
  startOfMonth,
  startOfWeek,
} from "date-fns";

import type { CalendarEvent, CalendarParams } from "../types/Calendar";

// Semanas de lunes a domingo en los dos idiomas: es la semana ISO que usan el
// resumen semanal y el dashboard (RF-61, RF-82).
const WEEK = { weekStartsOn: 1 } as const;
const DAY_FORMAT = "yyyy-MM-dd";

/** La zona de la cuenta (RF-130) o, si no tiene, la del navegador. */
export function calendarZone(accountZone: string | null | undefined): string {
  return accountZone || Intl.DateTimeFormat().resolvedOptions().timeZone;
}

/** El día de hoy ("yyyy-MM-dd") en la zona dada. */
export function todayIn(zone: string, now: Date = new Date()): string {
  return format(new TZDate(now, zone), DAY_FORMAT);
}

/** El día ("yyyy-MM-dd") en que cae un instante ISO, en la zona dada. */
export function dayOf(instant: string, zone: string): string {
  return format(new TZDate(new Date(instant), zone), DAY_FORMAT);
}

/** Medianoche de un día "yyyy-MM-dd" en la zona dada. */
function midnight(day: string, zone: string): TZDate {
  const [year, month, date] = day.split("-").map(Number);
  return new TZDate(year, month - 1, date, zone);
}

function isDay(value: string | null): value is string {
  return !!value && isValid(parse(value, DAY_FORMAT, new Date()));
}

export function parseCalendarParams(search: URLSearchParams, today: string): CalendarParams {
  const view = search.get("view") === "week" ? "week" : "month";
  const date = search.get("date");
  return { view, date: isDay(date) ? date : today };
}

/** Solo lo que no es lo de por defecto: `/calendar` es el mes de hoy. */
export function serializeCalendarParams(params: CalendarParams, today: string): URLSearchParams {
  const search = new URLSearchParams();
  if (params.view === "week") search.set("view", "week");
  if (params.date !== today) search.set("date", params.date);
  return search;
}

export interface VisibleRange {
  /** Inicio (incluido) y fin (excluido), los que se piden a la API. */
  start: Date;
  end: Date;
  /** Los días que se pintan, "yyyy-MM-dd", de lunes a domingo. */
  days: string[];
}

/**
 * Lo que se ve de una vista: el mes completo con las semanas que lo tocan (de 4 a
 * 6 filas), o la semana de lunes a domingo del día de referencia.
 */
export function visibleRange(params: CalendarParams, zone: string): VisibleRange {
  const anchor = midnight(params.date, zone);
  const start =
    params.view === "month"
      ? startOfWeek(startOfMonth(anchor), WEEK)
      : startOfWeek(anchor, WEEK);
  const last =
    params.view === "month" ? endOfWeek(endOfMonth(anchor), WEEK) : endOfWeek(anchor, WEEK);
  const days = eachDayOfInterval({ start, end: last }).map((day) => format(day, DAY_FORMAT));
  return { start, end: midnight(format(addDays(last, 1), DAY_FORMAT), zone), days };
}

/** El mismo día de referencia, un mes o una semana antes (-1) o después (+1). */
export function shiftParams(params: CalendarParams, step: -1 | 1, zone: string): CalendarParams {
  const anchor = midnight(params.date, zone);
  const moved = params.view === "month" ? addMonths(anchor, step) : addWeeks(anchor, step);
  return { ...params, date: format(moved, DAY_FORMAT) };
}

export function isSameMonth(day: string, reference: string): boolean {
  return day.slice(0, 7) === reference.slice(0, 7);
}

/** Los eventos agrupados por el día en que caen en la zona dada, en su orden. */
export function eventsByDay(events: CalendarEvent[], zone: string): Map<string, CalendarEvent[]> {
  const byDay = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const day = dayOf(event.starts_at, zone);
    byDay.set(day, [...(byDay.get(day) ?? []), event]);
  }
  return byDay;
}

/** Un recordatorio pendiente cuya hora ya pasó. Una entrevista nunca "vence". */
export function isOverdue(event: CalendarEvent, now: Date = new Date()): boolean {
  return event.kind === "reminder" && new Date(event.starts_at) < now;
}

/** Adónde lleva un evento (RF-131): su solicitud o, sin ella, los recordatorios. */
export function eventHref(event: CalendarEvent): string {
  return event.application ? `/applications/${event.application.id}` : "/reminders";
}


/** Mediodía en UTC de un día "yyyy-MM-dd". Un día del calendario no depende de la
 * zona: formatearlo desde ahí con `timeZone: "UTC"` nunca lo mueve al de al lado. */
function noonUtc(day: string): number {
  const [year, month, date] = day.split("-").map(Number);
  return Date.UTC(year, month - 1, date, 12);
}

/** Un día "yyyy-MM-dd" escrito en el idioma de la interfaz. */
export function formatDay(day: string, locale: string, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat(locale, { ...options, timeZone: "UTC" }).format(noonUtc(day));
}

/** El periodo que se ve, como título: "Octubre de 2026" o "28 sept – 4 oct 2026". */
export function periodTitle(params: CalendarParams, days: string[], locale: string): string {
  const title =
    params.view === "month"
      ? formatDay(params.date, locale, { month: "long", year: "numeric" })
      : new Intl.DateTimeFormat(locale, {
          day: "numeric",
          month: "short",
          year: "numeric",
          timeZone: "UTC",
        }).formatRange(noonUtc(days[0]), noonUtc(days[days.length - 1]));
  return title.charAt(0).toLocaleUpperCase(locale) + title.slice(1);
}

/** La hora de un evento en la zona dada ("09:30"). */
export function formatTime(instant: string, zone: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: zone,
  }).format(new Date(instant));
}
