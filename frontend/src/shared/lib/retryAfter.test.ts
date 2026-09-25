import { describe, expect, it } from "vitest";

import { formatRetryAfter } from "./retryAfter";

describe("formatRetryAfter", () => {
  it.each([
    [42, "es", "dentro de 42 segundos"],
    [60, "es", "dentro de 1 minuto"],
    // Redondea hacia arriba: nunca promete menos espera de la real.
    [61, "es", "dentro de 2 minutos"],
    [3600, "en", "in 60 minutes"],
    [0, "en", "in 1 second"],
  ])("%i s in %s is %s", (seconds, locale, expected) => {
    expect(formatRetryAfter(seconds, locale)).toBe(expected);
  });
});
