import { describe, expect, it } from "vitest";
import { toChangedAt } from "./applicationStatusChange.service";

// 14:30 en Madrid (12:30 UTC) y 08:30 en Nueva York.
const NOW = new Date("2026-09-23T12:30:00Z");

describe("toChangedAt", () => {
  it("keeps today's actual clock time in the account zone instead of midnight", () => {
    // Si el usuario "elige" hoy sin pensarlo, el resultado debe seguir siendo
    // ahora mismo, no medianoche (que caería antes del último cambio).
    expect(toChangedAt("2026-09-23", "Europe/Madrid", NOW)).toBe(NOW.toISOString());
    expect(toChangedAt("2026-09-23", "America/New_York", NOW)).toBe(NOW.toISOString());
  });

  it("uses the current clock time of the account zone on a past date", () => {
    expect(toChangedAt("2026-09-01", "Europe/Madrid", NOW)).toBe("2026-09-01T12:30:00.000Z");
    expect(toChangedAt("2026-09-01", "America/New_York", NOW)).toBe("2026-09-01T12:30:00.000Z");
  });

  it("reads the day in the account zone, not in the browser's", () => {
    // 23:30 en Nueva York es ya el día siguiente en UTC y en Madrid: el día elegido
    // sigue siendo el de la cuenta.
    const lateEvening = new Date("2026-09-24T03:30:00Z");

    expect(toChangedAt("2026-09-01", "America/New_York", lateEvening)).toBe(
      "2026-09-02T03:30:00.000Z",
    );
  });

  it("keeps the clock time across a daylight saving change", () => {
    // El 1 de marzo Madrid está en UTC+1; el 23 de septiembre, en UTC+2.
    expect(toChangedAt("2026-03-01", "Europe/Madrid", NOW)).toBe("2026-03-01T13:30:00.000Z");
  });
});
