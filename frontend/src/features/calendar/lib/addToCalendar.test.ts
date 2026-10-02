import { beforeAll, describe, expect, it } from "vitest";

import i18n from "@/shared/i18n/i18n";
import type { Interview } from "@/features/interviews/types/Interview";
import type { Reminder } from "@/features/reminders/types/Reminder";
import type { CalendarEvent } from "../types/Calendar";
import {
  buildIcs,
  entryFromEvent,
  entryFromInterview,
  entryFromReminder,
  googleCalendarUrl,
  icsFilename,
  type CalendarEntry,
} from "./addToCalendar";

const ORIGIN = "https://tracker.example";
const t = i18n.t.bind(i18n);

const application = {
  id: "app-1",
  position_title: "Backend Developer",
  company: { id: "c-1", name: "Acme" },
};

const interviewEvent: CalendarEvent = {
  kind: "interview",
  id: "int-1",
  starts_at: "2026-10-05T08:00:00Z",
  duration_minutes: 45,
  title: null,
  interview_type: "technical",
  format: "online",
  interviewers: "Ana López",
  outcome: "pending",
  application,
};

const interview: Interview = {
  id: "int-1",
  scheduled_at: "2026-10-05T08:00:00Z",
  duration_minutes: null,
  interviewers: null,
  interview_type: null,
  format: null,
  outcome: "pending",
  notes: "Preguntar por el salario",
  created_at: "2026-10-01T08:00:00Z",
  updated_at: "2026-10-01T08:00:00Z",
};

const reminder: Reminder = {
  id: "rem-1",
  title: "Enviar el test",
  due_at: "2026-10-06T16:30:00Z",
  application: { id: "app-1", position_title: "Backend Developer" },
  sent_at: null,
  completed_at: null,
  channel: "in_app",
  status: "pending",
  created_at: "2026-10-01T08:00:00Z",
  updated_at: "2026-10-01T08:00:00Z",
};

/** Las líneas lógicas de un `.ics`: deshace el plegado de 75 octetos. */
const unfold = (ics: string) => ics.replace(/\r\n /g, "").split("\r\n");

beforeAll(async () => {
  await i18n.changeLanguage("es");
});

describe("entradas de calendario", () => {
  it("una entrevista lleva puesto, empresa, duración y detalles, pero no notas", () => {
    const entry = entryFromEvent(interviewEvent, t, ORIGIN);

    expect(entry.uid).toBe("interview-int-1@applications-tracker");
    expect(entry.title).toBe("Entrevista: Backend Developer — Acme");
    expect(entry.end.getTime() - entry.start.getTime()).toBe(45 * 60_000);
    expect(entry.details).toEqual([
      "Tipo: Técnica",
      "Formato: Online",
      "Con quién: Ana López",
    ]);
    expect(entry.url).toBe(`${ORIGIN}/applications/app-1`);
  });

  it("una entrevista sin duración ocupa una hora y nunca lleva sus notas", () => {
    const entry = entryFromInterview(interview, application, t, ORIGIN);

    expect(entry.end.getTime() - entry.start.getTime()).toBe(60 * 60_000);
    expect(entry.details).toEqual([]);
    expect(buildIcs(entry)).not.toContain("salario");
    expect(googleCalendarUrl(entry)).not.toContain("salario");
  });

  it("un recordatorio dura 15 minutos y nombra su solicitud", () => {
    const entry = entryFromReminder(reminder, t, ORIGIN);

    expect(entry.uid).toBe("reminder-rem-1@applications-tracker");
    expect(entry.title).toBe("Enviar el test");
    expect(entry.end.getTime() - entry.start.getTime()).toBe(15 * 60_000);
    expect(entry.details).toEqual(["Solicitud: Backend Developer"]);
  });

  it("un recordatorio suelto enlaza a los recordatorios", () => {
    const entry = entryFromReminder({ ...reminder, application: null }, t, ORIGIN);

    expect(entry.details).toEqual([]);
    expect(entry.url).toBe(`${ORIGIN}/reminders`);
  });

  it("el mismo evento da siempre el mismo identificador", () => {
    const first = entryFromEvent(interviewEvent, t, ORIGIN);
    const moved = entryFromEvent({ ...interviewEvent, starts_at: "2026-10-07T10:00:00Z" }, t, ORIGIN);

    expect(moved.uid).toBe(first.uid);
  });
});

const entry: CalendarEntry = {
  uid: "interview-int-1@applications-tracker",
  title: "Entrevista: Ingeniería, datos; y más\\ todo",
  start: new Date("2026-10-05T08:00:00Z"),
  end: new Date("2026-10-05T08:45:00Z"),
  details: ["Tipo: Técnica", "Con quién: Ana"],
  url: `${ORIGIN}/applications/app-1`,
};

describe("googleCalendarUrl", () => {
  it("abre Google con el título, las horas en UTC y la descripción", () => {
    const url = new URL(googleCalendarUrl(entry));

    expect(url.origin + url.pathname).toBe("https://calendar.google.com/calendar/render");
    expect(url.searchParams.get("action")).toBe("TEMPLATE");
    expect(url.searchParams.get("text")).toBe(entry.title);
    expect(url.searchParams.get("dates")).toBe("20261005T080000Z/20261005T084500Z");
    expect(url.searchParams.get("details")).toBe(
      `Tipo: Técnica\nCon quién: Ana\n${ORIGIN}/applications/app-1`,
    );
  });
});

describe("buildIcs", () => {
  const now = new Date("2026-10-01T12:00:00Z");

  it("escribe un VEVENT con horas en UTC y líneas terminadas en CRLF", () => {
    const ics = buildIcs(entry, now);
    const lines = unfold(ics);

    expect(ics.endsWith("\r\n")).toBe(true);
    expect(ics.replace(/\r\n/g, "")).not.toContain("\n");
    expect(lines).toContain("BEGIN:VCALENDAR");
    expect(lines).toContain("VERSION:2.0");
    expect(lines).toContain("UID:interview-int-1@applications-tracker");
    expect(lines).toContain("DTSTAMP:20261001T120000Z");
    expect(lines).toContain("DTSTART:20261005T080000Z");
    expect(lines).toContain("DTEND:20261005T084500Z");
    expect(lines).toContain(`URL:${ORIGIN}/applications/app-1`);
  });

  it("escapa comas, puntos y coma, barras y saltos de línea", () => {
    const lines = unfold(buildIcs(entry, now));

    expect(lines).toContain("SUMMARY:Entrevista: Ingeniería\\, datos\\; y más\\\\ todo");
    expect(lines).toContain(
      `DESCRIPTION:Tipo: Técnica\\nCon quién: Ana\\n${ORIGIN}/applications/app-1`,
    );
  });

  it("pliega las líneas largas sin pasar de 75 octetos ni partir un carácter", () => {
    const long = { ...entry, title: "Entrevista técnica ñandú ".repeat(10) };
    const ics = buildIcs(long, now);
    const encoder = new TextEncoder();

    for (const line of ics.split("\r\n")) {
      expect(encoder.encode(line).length).toBeLessThanOrEqual(75);
    }
    expect(ics).not.toContain("�");
    expect(unfold(ics)).toContain(`SUMMARY:${long.title}`);
  });
});

describe("icsFilename", () => {
  it("quita tildes y símbolos y añade el día", () => {
    expect(icsFilename({ ...entry, title: "Entrevista: Ingeniería — Acme, S.L." })).toMatch(
      /^entrevista-ingenieria-acme-s-l-2026-10-0[45]\.ics$/,
    );
  });

  it("sin nada aprovechable en el título, se llama evento", () => {
    expect(icsFilename({ ...entry, title: "¿¡…!?" })).toMatch(/^evento-2026-10-0[45]\.ics$/);
  });
});
