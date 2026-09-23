import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { toChangedAt } from "./applicationStatusChange.service";

describe("toChangedAt", () => {
  beforeEach(() => {
    // Hora local fija: 2026-09-23T14:30:00 en la zona del test (ver vitest.config).
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 23, 14, 30, 0));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("keeps today's actual clock time instead of midnight", () => {
    // Si el usuario "elige" hoy sin pensarlo, el resultado debe seguir siendo
    // prácticamente ahora, no medianoche (que caería antes del último cambio).
    const result = new Date(toChangedAt("2026-09-23"));

    expect(result.getHours()).toBe(14);
    expect(result.getMinutes()).toBe(30);
  });

  it("uses the current clock time on a past date, not midnight", () => {
    const result = new Date(toChangedAt("2026-09-01"));

    expect(result.getFullYear()).toBe(2026);
    expect(result.getMonth()).toBe(8);
    expect(result.getDate()).toBe(1);
    expect(result.getHours()).toBe(14);
    expect(result.getMinutes()).toBe(30);
  });

  it("returns a value Date can parse back (ISO with an explicit offset)", () => {
    expect(Number.isNaN(new Date(toChangedAt("2026-09-01")).getTime())).toBe(false);
  });
});
