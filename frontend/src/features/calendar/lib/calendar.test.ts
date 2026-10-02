import { describe, expect, it } from "vitest";

import type { CalendarEvent } from "../types/Calendar";
import {
  dayOf,
  eventHref,
  eventsByDay,
  formatDay,
  formatTime,
  isOverdue,
  parseCalendarParams,
  periodTitle,
  serializeCalendarParams,
  shiftParams,
  todayIn,
  visibleRange,
} from "./calendar";

/** El instante en UTC: TZDate escribe toISOString con el desfase de su zona. */
const utc = (date: Date) => new Date(date.getTime()).toISOString();

const event = (fields: Partial<CalendarEvent>): CalendarEvent => ({
  kind: "reminder",
  id: "r1",
  starts_at: "2026-10-05T10:00:00Z",
  duration_minutes: null,
  title: "Llamar",
  interview_type: null,
  format: null,
  interviewers: null,
  outcome: null,
  application: null,
  ...fields,
});

describe("today and days in the account zone", () => {
  // 23:30 UTC del 1 de octubre: en Madrid ya es día 2; en Nueva York, aún día 1.
  const now = new Date("2026-10-01T23:30:00Z");

  it("takes the day in the given zone, not the browser's", () => {
    expect(todayIn("Europe/Madrid", now)).toBe("2026-10-02");
    expect(todayIn("America/New_York", now)).toBe("2026-10-01");
    expect(dayOf("2026-10-01T23:30:00Z", "Asia/Tokyo")).toBe("2026-10-02");
  });
});

describe("parseCalendarParams / serializeCalendarParams", () => {
  it("defaults to this month and drops what is the default", () => {
    const params = parseCalendarParams(new URLSearchParams(), "2026-10-01");

    expect(params).toEqual({ view: "month", date: "2026-10-01" });
    expect(serializeCalendarParams(params, "2026-10-01").toString()).toBe("");
  });

  it("reads a week view on a given day", () => {
    const params = parseCalendarParams(
      new URLSearchParams("view=week&date=2026-12-24"),
      "2026-10-01",
    );

    expect(params).toEqual({ view: "week", date: "2026-12-24" });
    expect(serializeCalendarParams(params, "2026-10-01").toString()).toBe(
      "view=week&date=2026-12-24",
    );
  });

  it.each(["2026-13-01", "2026-02-30", "mañana", ""])("ignores an invalid date (%s)", (date) => {
    expect(parseCalendarParams(new URLSearchParams({ date }), "2026-10-01").date).toBe(
      "2026-10-01",
    );
  });
});

describe("visibleRange", () => {
  it("covers whole weeks from Monday around the month", () => {
    // Octubre de 2026 empieza en jueves y acaba en sábado.
    const range = visibleRange({ view: "month", date: "2026-10-15" }, "Europe/Madrid");

    expect(range.days[0]).toBe("2026-09-28");
    expect(range.days.at(-1)).toBe("2026-11-01");
    expect(range.days).toHaveLength(35);
    // Medianoche de Madrid (UTC+2 en verano).
    expect(utc(range.start)).toBe("2026-09-27T22:00:00.000Z");
    // El 25 de octubre cambia la hora: el 2 de noviembre ya es UTC+1.
    expect(utc(range.end)).toBe("2026-11-01T23:00:00.000Z");
  });

  it("covers a week from Monday to Sunday", () => {
    const range = visibleRange({ view: "week", date: "2026-10-01" }, "UTC");

    expect(range.days).toEqual([
      "2026-09-28",
      "2026-09-29",
      "2026-09-30",
      "2026-10-01",
      "2026-10-02",
      "2026-10-03",
      "2026-10-04",
    ]);
    expect(utc(range.start)).toBe("2026-09-28T00:00:00.000Z");
    expect(utc(range.end)).toBe("2026-10-05T00:00:00.000Z");
  });

  it("keeps 7 days in a week that changes the clock", () => {
    // Semana del 25 de octubre en Madrid: ese domingo dura 25 horas.
    const range = visibleRange({ view: "week", date: "2026-10-25" }, "Europe/Madrid");

    expect(range.days).toHaveLength(7);
    expect(range.days.at(-1)).toBe("2026-10-25");
    expect(utc(range.end)).toBe("2026-10-25T23:00:00.000Z");
  });

  it("never asks the API for more than 62 days", () => {
    for (const date of ["2026-02-15", "2026-08-01", "2027-05-31"]) {
      const range = visibleRange({ view: "month", date }, "Pacific/Kiritimati");
      const days = (range.end.getTime() - range.start.getTime()) / 86_400_000;
      expect(days).toBeLessThanOrEqual(62);
    }
  });
});

describe("shiftParams", () => {
  it("moves a month or a week keeping the view", () => {
    expect(shiftParams({ view: "month", date: "2026-01-31" }, 1, "UTC")).toEqual({
      view: "month",
      date: "2026-02-28",
    });
    expect(shiftParams({ view: "week", date: "2026-10-01" }, -1, "UTC")).toEqual({
      view: "week",
      date: "2026-09-24",
    });
  });
});

describe("events", () => {
  it("groups by the day in the account zone", () => {
    const late = event({ id: "late", starts_at: "2026-10-05T22:30:00Z" });
    const early = event({ id: "early", starts_at: "2026-10-05T08:00:00Z" });

    const byDay = eventsByDay([early, late], "Europe/Madrid");

    expect(byDay.get("2026-10-05")).toEqual([early]);
    expect(byDay.get("2026-10-06")).toEqual([late]);
  });

  it("marks only past reminders as overdue", () => {
    const now = new Date("2026-10-05T12:00:00Z");

    expect(isOverdue(event({}), now)).toBe(true);
    expect(isOverdue(event({ starts_at: "2026-10-06T00:00:00Z" }), now)).toBe(false);
    expect(isOverdue(event({ kind: "interview" }), now)).toBe(false);
  });

  it("links to the application or, without one, to the reminders", () => {
    expect(eventHref(event({}))).toBe("/reminders");
    expect(
      eventHref(
        event({
          application: { id: "a1", position_title: "Dev", company: { id: "c", name: "Acme" } },
        }),
      ),
    ).toBe("/applications/a1");
  });
});

describe("labels", () => {
  it("writes the period in the interface language", () => {
    const month = visibleRange({ view: "month", date: "2026-10-15" }, "UTC");
    const week = visibleRange({ view: "week", date: "2026-10-01" }, "UTC");

    expect(periodTitle({ view: "month", date: "2026-10-15" }, month.days, "es")).toBe(
      "Octubre de 2026",
    );
    expect(periodTitle({ view: "month", date: "2026-10-15" }, month.days, "en")).toBe(
      "October 2026",
    );
    expect(periodTitle({ view: "week", date: "2026-10-01" }, week.days, "en")).toMatch(
      /Sep 28\s*–\s*Oct 4, 2026/,
    );
  });

  it("keeps a day on its date whatever the zone", () => {
    expect(formatDay("2026-10-01", "en", { day: "numeric", month: "long" })).toBe("October 1");
  });

  it("writes the time in the account zone", () => {
    expect(formatTime("2026-10-05T07:30:00Z", "Europe/Madrid", "es")).toBe("09:30");
    expect(formatTime("2026-10-05T07:30:00Z", "America/New_York", "es")).toBe("03:30");
  });
});
