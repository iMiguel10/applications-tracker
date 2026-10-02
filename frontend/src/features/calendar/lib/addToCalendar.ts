import { format } from "date-fns";
import type { TFunction } from "i18next";

import type { Application } from "@/features/applications/types/Application";
import type { Interview } from "@/features/interviews/types/Interview";
import type { Reminder } from "@/features/reminders/types/Reminder";
import type { CalendarEvent, CalendarEventKind } from "../types/Calendar";

/** Una entrevista sin duración ocupa una hora en el calendario externo. */
export const DEFAULT_INTERVIEW_MINUTES = 60;
/** Un recordatorio es un aviso a una hora: un hueco corto para que se vea. */
export const REMINDER_MINUTES = 15;

/**
 * Un evento listo para llevarlo a otro calendario (RF-133): Google Calendar o un
 * `.ics`. Nunca lleva notas: son privadas y el calendario quizá se comparta.
 */
export interface CalendarEntry {
  /** Fijo por evento: importar dos veces el mismo `.ics` lo actualiza, no lo duplica. */
  uid: string;
  title: string;
  start: Date;
  end: Date;
  /** Líneas de la descripción, sin el enlace. */
  details: string[];
  /** La página de la app donde vive el evento. */
  url: string;
}

interface InterviewData {
  id: string;
  startsAt: string;
  durationMinutes: number | null;
  interviewType: string | null;
  format: string | null;
  interviewers: string | null;
  application: { id: string; position_title: string; company: { name: string } };
}

function entry(
  kind: CalendarEventKind,
  id: string,
  startsAt: string,
  minutes: number,
  fields: Pick<CalendarEntry, "title" | "details" | "url">,
): CalendarEntry {
  const start = new Date(startsAt);
  return {
    uid: `${kind}-${id}@applications-tracker`,
    start,
    end: new Date(start.getTime() + minutes * 60_000),
    ...fields,
  };
}

function interviewEntry(data: InterviewData, t: TFunction, origin: string): CalendarEntry {
  const { application } = data;
  return entry("interview", data.id, data.startsAt, data.durationMinutes ?? DEFAULT_INTERVIEW_MINUTES, {
    title: t("calendar.add.interviewTitle", {
      position: application.position_title,
      company: application.company.name,
    }),
    details: [
      data.interviewType ? `${t("interviews.fields.type")}: ${t(`interviews.type.${data.interviewType}`)}` : null,
      data.format ? `${t("interviews.fields.format")}: ${t(`interviews.format.${data.format}`)}` : null,
      data.interviewers ? `${t("interviews.fields.interviewers")}: ${data.interviewers}` : null,
    ].filter((line): line is string => !!line),
    url: `${origin}/applications/${application.id}`,
  });
}

function reminderEntry(
  id: string,
  title: string,
  dueAt: string,
  application: { id: string; position_title: string; company?: { name: string } } | null,
  t: TFunction,
  origin: string,
): CalendarEntry {
  const position = application
    ? [application.position_title, application.company?.name].filter(Boolean).join(" — ")
    : null;
  return entry("reminder", id, dueAt, REMINDER_MINUTES, {
    title,
    details: position ? [`${t("calendar.add.application")}: ${position}`] : [],
    url: application ? `${origin}/applications/${application.id}` : `${origin}/reminders`,
  });
}

/** Un evento de la vista del calendario. */
export function entryFromEvent(event: CalendarEvent, t: TFunction, origin: string): CalendarEntry {
  if (event.kind === "interview" && event.application) {
    return interviewEntry(
      {
        id: event.id,
        startsAt: event.starts_at,
        durationMinutes: event.duration_minutes,
        interviewType: event.interview_type,
        format: event.format,
        interviewers: event.interviewers,
        application: event.application,
      },
      t,
      origin,
    );
  }
  return reminderEntry(event.id, event.title ?? "", event.starts_at, event.application, t, origin);
}

/** Una entrevista del detalle de su solicitud. */
export function entryFromInterview(
  interview: Interview,
  application: Pick<Application, "id" | "position_title" | "company">,
  t: TFunction,
  origin: string,
): CalendarEntry {
  return interviewEntry(
    {
      id: interview.id,
      startsAt: interview.scheduled_at,
      durationMinutes: interview.duration_minutes,
      interviewType: interview.interview_type,
      format: interview.format,
      interviewers: interview.interviewers,
      application,
    },
    t,
    origin,
  );
}

/** Un recordatorio de su lista (la del detalle de la solicitud o la global). */
export function entryFromReminder(reminder: Reminder, t: TFunction, origin: string): CalendarEntry {
  return reminderEntry(reminder.id, reminder.title, reminder.due_at, reminder.application, t, origin);
}

/** "20261005T080000Z": la forma de un instante UTC en iCalendar y en Google. */
function utcStamp(date: Date): string {
  return date.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
}

function description(entry: CalendarEntry): string {
  return [...entry.details, entry.url].join("\n");
}

/** El enlace que abre Google Calendar con el evento ya rellenado. */
export function googleCalendarUrl(entry: CalendarEntry): string {
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: entry.title,
    dates: `${utcStamp(entry.start)}/${utcStamp(entry.end)}`,
    details: description(entry),
  });
  return `https://calendar.google.com/calendar/render?${params}`;
}

/**
 * Escape de un texto de iCalendar (RFC 5545 §3.3.11). Todo salto de línea, también
 * un retorno de carro suelto (la API lo admite en un título), pasa a `\n`: en crudo,
 * un lector lo tomaría como fin de línea y leería lo que sigue como otra propiedad.
 * El resto de caracteres de control, que TEXT no admite salvo el tabulador, se quita.
 */
function escapeText(value: string): string {
  return (
    value
      .replace(/\\/g, "\\\\")
      .replace(/;/g, "\\;")
      .replace(/,/g, "\\,")
      .replace(/\r\n|\r|\n/g, "\\n")
      // eslint-disable-next-line no-control-regex
      .replace(/[\u0000-\u0008\u000B-\u001F\u007F]/g, "")
  );
}

/**
 * Parte una línea en trozos de 75 octetos como máximo (RFC 5545 §3.1): se cuentan
 * bytes en UTF-8, no caracteres, y nunca se corta un carácter por la mitad.
 */
function fold(line: string): string {
  const encoder = new TextEncoder();
  const parts: string[] = [];
  let current = "";
  let size = 0;
  for (const char of line) {
    const bytes = encoder.encode(char).length;
    // La primera línea admite 75 octetos; las siguientes, 74 más el espacio inicial.
    const max = parts.length === 0 ? 75 : 74;
    if (size + bytes > max) {
      parts.push(current);
      current = "";
      size = 0;
    }
    current += char;
    size += bytes;
  }
  parts.push(current);
  return parts.join("\r\n ");
}

/** El fichero `.ics` de un evento, que importa cualquier calendario. */
export function buildIcs(entry: CalendarEntry, now: Date = new Date()): string {
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Applications Tracker//Calendar//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "BEGIN:VEVENT",
    `UID:${entry.uid}`,
    `DTSTAMP:${utcStamp(now)}`,
    `DTSTART:${utcStamp(entry.start)}`,
    `DTEND:${utcStamp(entry.end)}`,
    `SUMMARY:${escapeText(entry.title)}`,
    `DESCRIPTION:${escapeText(description(entry))}`,
    `URL:${entry.url}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ];
  return lines.map(fold).join("\r\n") + "\r\n";
}

/** "entrevista-backend-developer-acme-2026-10-05.ics": sin tildes ni símbolos. */
export function icsFilename(entry: CalendarEntry): string {
  const slug = entry.title
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60)
    .replace(/-+$/, "");
  // El día en la zona del navegador, que es donde se guarda el fichero.
  const day = format(entry.start, "yyyy-MM-dd");
  return `${slug || "evento"}-${day}.ics`;
}
