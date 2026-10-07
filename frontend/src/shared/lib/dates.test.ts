import { describe, expect, it } from "vitest";
import {
  accountZone,
  datetimeLocalToIso,
  parseDateOnly,
  toDateOnly,
  toDateTimeLocal,
  todayIn,
} from "./dates";

describe("parseDateOnly", () => {
  it("keeps the calendar day in local time (no 'one day less')", () => {
    const date = parseDateOnly("2026-09-01");

    expect(date?.getFullYear()).toBe(2026);
    expect(date?.getMonth()).toBe(8);
    expect(date?.getDate()).toBe(1);
  });

  it("returns undefined for empty or malformed values", () => {
    expect(parseDateOnly(null)).toBeUndefined();
    expect(parseDateOnly("")).toBeUndefined();
    expect(parseDateOnly("01/09/2026")).toBeUndefined();
  });

  it("round-trips with toDateOnly", () => {
    expect(toDateOnly(parseDateOnly("2026-12-31")!)).toBe("2026-12-31");
  });
});

describe("datetimeLocalToIso / toDateTimeLocal", () => {
  it("reads the clock time in the given zone, not the browser's", () => {
    expect(datetimeLocalToIso("2026-09-01T15:30", "Europe/Madrid")).toBe(
      "2026-09-01T13:30:00.000Z",
    );
    expect(datetimeLocalToIso("2026-09-01T15:30", "America/New_York")).toBe(
      "2026-09-01T19:30:00.000Z",
    );
  });

  it("writes an instant as the clock time of the given zone", () => {
    expect(toDateTimeLocal("2026-09-01T19:30:00Z", "America/New_York")).toBe("2026-09-01T15:30");
    expect(toDateTimeLocal("2026-09-01T19:30:00Z", "Asia/Tokyo")).toBe("2026-09-02T04:30");
  });

  it("round-trips in any zone, also on daylight saving days", () => {
    for (const zone of ["Europe/Madrid", "America/New_York", "Australia/Sydney", "UTC"]) {
      for (const local of ["2026-01-15T09:00", "2026-07-15T23:45", "2026-10-25T03:30"]) {
        expect(toDateTimeLocal(datetimeLocalToIso(local, zone), zone)).toBe(local);
      }
    }
  });

  it("moves a clock time that does not exist to the next one that does", () => {
    // Madrid salta de 2:00 a 3:00 el 29 de marzo de 2026: las 2:30 no existen.
    const iso = datetimeLocalToIso("2026-03-29T02:30", "Europe/Madrid");

    expect(toDateTimeLocal(iso, "Europe/Madrid")).toBe("2026-03-29T03:30");
  });
});

describe("todayIn / accountZone", () => {
  it("gives the day in the zone, which may not be the UTC one", () => {
    const now = new Date("2026-10-02T02:00:00Z");

    expect(todayIn("Europe/Madrid", now)).toBe("2026-10-02");
    expect(todayIn("America/Los_Angeles", now)).toBe("2026-10-01");
  });

  it("falls back to the browser zone when the account has none", () => {
    const browser = Intl.DateTimeFormat().resolvedOptions().timeZone;

    expect(accountZone("Asia/Tokyo")).toBe("Asia/Tokyo");
    expect(accountZone(null)).toBe(browser);
    expect(accountZone("")).toBe(browser);
  });
});
