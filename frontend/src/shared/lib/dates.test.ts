import { describe, expect, it } from "vitest";
import { datetimeLocalToIso, parseDateOnly, toDateOnly, toDateTimeLocal } from "./dates";

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
  it("round-trips a datetime-local value through an ISO instant", () => {
    const local = "2026-09-01T15:30";

    const iso = datetimeLocalToIso(local);

    expect(toDateTimeLocal(iso)).toBe(local);
  });

  it("produces a value Date can parse back", () => {
    expect(Number.isNaN(new Date(datetimeLocalToIso("2026-09-01T15:30")).getTime())).toBe(
      false,
    );
  });
});
