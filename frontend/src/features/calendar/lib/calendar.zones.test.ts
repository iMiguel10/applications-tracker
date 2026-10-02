import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import type { CalendarEvent } from "../types/Calendar";
import { dayOf, eventsByDay, shiftParams, todayIn, visibleRange } from "./calendar";

/**
 * Pruebas adversas de zona horaria (QA de F17): cambios de hora en Europa y en
 * América (también los que ocurren a medianoche), semanas que cruzan de año y
 * días al oeste de UTC. Cada bloque se repite con el navegador en varias zonas:
 * el calendario se calcula en la zona de la cuenta y la del navegador no debe
 * colarse en ningún resultado.
 */

const utc = (date: Date) => new Date(date.getTime()).toISOString();

const BROWSER_ZONES = ["UTC", "America/Los_Angeles", "Pacific/Kiritimati", "Asia/Kolkata"];

const reminderAt = (id: string, starts_at: string): CalendarEvent => ({
  kind: "reminder",
  id,
  starts_at,
  duration_minutes: null,
  title: id,
  interview_type: null,
  format: null,
  interviewers: null,
  outcome: null,
  application: null,
});

/** Los días esperados de lunes a domingo a partir de un lunes (aritmética en UTC puro). */
function weekFrom(monday: string): string[] {
  const start = Date.parse(`${monday}T12:00:00Z`);
  return Array.from({ length: 7 }, (_, i) =>
    new Date(start + i * 86_400_000).toISOString().slice(0, 10),
  );
}

describe.each(BROWSER_ZONES)("con el navegador en %s", (browserZone) => {
  beforeAll(() => {
    vi.stubEnv("TZ", browserZone);
  });
  afterAll(() => {
    vi.unstubAllEnvs();
  });

  it("el navegador simulado está de verdad en esa zona", () => {
    // Comparado con el nombre que da ICU a esa zona (Asia/Kolkata sale Asia/Calcutta).
    const canonical = new Intl.DateTimeFormat("en", { timeZone: browserZone }).resolvedOptions()
      .timeZone;
    expect(Intl.DateTimeFormat().resolvedOptions().timeZone).toBe(canonical);
  });

  describe("semanas con cambio de hora", () => {
    it.each([
      // [zona de la cuenta, día de referencia, lunes, inicio UTC, fin UTC]
      // Europa, primavera: el domingo 29 de marzo dura 23 h.
      ["Europe/Madrid", "2026-03-29", "2026-03-23", "2026-03-22T23:00:00.000Z", "2026-03-29T22:00:00.000Z"],
      // Europa, otoño: el domingo 25 de octubre dura 25 h.
      ["Europe/London", "2026-10-25", "2026-10-19", "2026-10-18T23:00:00.000Z", "2026-10-26T00:00:00.000Z"],
      // EE. UU., primavera (8 de marzo) y otoño (1 de noviembre), en domingo.
      ["America/New_York", "2026-03-08", "2026-03-02", "2026-03-02T05:00:00.000Z", "2026-03-09T04:00:00.000Z"],
      ["America/Los_Angeles", "2026-11-01", "2026-10-26", "2026-10-26T07:00:00.000Z", "2026-11-02T08:00:00.000Z"],
      // El lunes siguiente al cambio de EE. UU. empieza ya con la hora nueva.
      ["America/Chicago", "2026-03-09", "2026-03-09", "2026-03-09T05:00:00.000Z", "2026-03-16T05:00:00.000Z"],
    ])("%s, semana del %s", (zone, date, monday, start, end) => {
      const range = visibleRange({ view: "week", date }, zone);

      expect(range.days).toEqual(weekFrom(monday));
      expect(utc(range.start)).toBe(start);
      expect(utc(range.end)).toBe(end);
    });

    it.each([
      // Chile y Cuba cambian la hora A MEDIANOCHE: ese día las 00:00 no existen
      // (primavera) o se repiten (otoño). El día no debe saltar al de al lado.
      ["America/Santiago", "2026-09-06"], // domingo, 00:00 → 01:00
      ["America/Santiago", "2026-04-05"], // domingo, 00:00 → 23:00 del sábado
      ["America/Havana", "2026-03-08"], // domingo, 00:00 → 01:00
      ["America/Havana", "2026-11-01"], // domingo, 01:00 → 00:00
      ["America/Asuncion", "2026-10-04"], // domingo, 00:00 → 01:00
    ])("%s, semana del %s (cambio a medianoche)", (zone, date) => {
      const range = visibleRange({ view: "week", date }, zone);

      expect(range.days).toHaveLength(7);
      expect(range.days).toContain(date);
      expect(range.days).toEqual(weekFrom(range.days[0]));
      // El inicio cae en el lunes de la semana en la zona de la cuenta…
      expect(dayOf(utc(range.start), zone)).toBe(range.days[0]);
      // …y el fin, en el lunes siguiente, sin dejar fuera ni repetir un trozo de día.
      const nextMonday = new Date(Date.parse(`${range.days[0]}T12:00:00Z`) + 7 * 86_400_000)
        .toISOString()
        .slice(0, 10);
      expect(dayOf(utc(range.end), zone)).toBe(nextMonday);
      expect(dayOf(new Date(range.end.getTime() - 1).toISOString(), zone)).toBe(range.days[6]);
      expect(dayOf(new Date(range.start.getTime() - 1).toISOString(), zone)).not.toBe(
        range.days[0],
      );
    });

    it.each([
      ["America/Santiago", "2026-09-07"], // lunes tras el cambio de medianoche
      ["America/Havana", "2026-03-09"],
    ])("%s, la semana del %s empieza en lunes", (zone, date) => {
      const range = visibleRange({ view: "week", date }, zone);

      expect(range.days[0]).toBe(date);
      expect(dayOf(utc(range.start), zone)).toBe(date);
    });

    it("un evento justo antes y justo después del cambio cae en su día", () => {
      // Madrid, 29 de marzo de 2026: a las 02:00 locales pasan a ser las 03:00.
      const before = reminderAt("before", "2026-03-29T00:59:00Z"); // 01:59 CET
      const after = reminderAt("after", "2026-03-29T01:00:00Z"); // 03:00 CEST
      const nextDay = reminderAt("next", "2026-03-29T22:00:00Z"); // 00:00 del lunes

      const byDay = eventsByDay([before, after, nextDay], "Europe/Madrid");

      expect(byDay.get("2026-03-29")).toEqual([before, after]);
      expect(byDay.get("2026-03-30")).toEqual([nextDay]);
    });
  });

  describe("semanas y meses que cruzan de año", () => {
    it("la semana del 31 de diciembre va del lunes 28 al domingo 3 de enero", () => {
      const range = visibleRange({ view: "week", date: "2026-12-31" }, "Europe/Madrid");

      expect(range.days).toEqual(weekFrom("2026-12-28"));
      expect(utc(range.start)).toBe("2026-12-27T23:00:00.000Z");
      expect(utc(range.end)).toBe("2027-01-03T23:00:00.000Z");
    });

    it("enero de 2027 empieza a pintarse el lunes 28 de diciembre", () => {
      const range = visibleRange({ view: "month", date: "2027-01-01" }, "America/New_York");

      expect(range.days[0]).toBe("2026-12-28");
      expect(range.days.at(-1)).toBe("2027-01-31");
      expect(range.days).toHaveLength(35);
      expect(utc(range.start)).toBe("2026-12-28T05:00:00.000Z");
      expect(utc(range.end)).toBe("2027-02-01T05:00:00.000Z");
    });

    it("avanzar y retroceder cruza de año en las dos vistas", () => {
      expect(shiftParams({ view: "week", date: "2026-12-31" }, 1, "Asia/Tokyo")).toEqual({
        view: "week",
        date: "2027-01-07",
      });
      expect(shiftParams({ view: "month", date: "2027-01-15" }, -1, "America/Los_Angeles")).toEqual(
        { view: "month", date: "2026-12-15" },
      );
      expect(shiftParams({ view: "week", date: "2027-01-02" }, -1, "Pacific/Kiritimati")).toEqual({
        view: "week",
        date: "2026-12-26",
      });
    });

    it("avanzar una semana sobre un cambio de hora a medianoche no se salta un día", () => {
      expect(shiftParams({ view: "week", date: "2026-09-01" }, 1, "America/Santiago")).toEqual({
        view: "week",
        date: "2026-09-08",
      });
      expect(shiftParams({ view: "week", date: "2026-04-01" }, 1, "America/Santiago")).toEqual({
        view: "week",
        date: "2026-04-08",
      });
    });
  });

  describe("días al oeste de UTC", () => {
    it("un evento de madrugada en UTC cae el día anterior en América", () => {
      const event = reminderAt("late", "2026-10-06T03:30:00Z");

      expect(dayOf(event.starts_at, "America/Los_Angeles")).toBe("2026-10-05");
      expect(dayOf(event.starts_at, "Pacific/Honolulu")).toBe("2026-10-05");
      expect(dayOf(event.starts_at, "Europe/Madrid")).toBe("2026-10-06");
      expect(eventsByDay([event], "America/Los_Angeles").get("2026-10-05")).toEqual([event]);
    });

    it("el mes de una cuenta en Honolulu pide desde su medianoche (10:00 UTC)", () => {
      const range = visibleRange({ view: "month", date: "2026-10-01" }, "Pacific/Honolulu");

      expect(range.days[0]).toBe("2026-09-28");
      expect(utc(range.start)).toBe("2026-09-28T10:00:00.000Z");
      expect(utc(range.end)).toBe("2026-11-02T10:00:00.000Z");
    });

    it("hoy en la cuenta no es hoy en el navegador", () => {
      // 05:00 UTC del día 2: en Los Ángeles aún es el día 1; en Kiritimati, ya el 2.
      const now = new Date("2026-10-02T05:00:00Z");

      expect(todayIn("America/Los_Angeles", now)).toBe("2026-10-01");
      expect(todayIn("Pacific/Kiritimati", now)).toBe("2026-10-02");
      expect(todayIn("Pacific/Pago_Pago", now)).toBe("2026-10-01");
    });
  });
});
