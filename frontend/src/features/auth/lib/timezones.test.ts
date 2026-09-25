import { describe, expect, it } from "vitest";

import { timezoneOptions } from "./timezones";

describe("timezoneOptions", () => {
  it("stores the IANA name and shows it readable, with today's offset", () => {
    const options = timezoneOptions("es", null);
    const puertoRico = options.find((o) => o.value === "America/Puerto_Rico");

    // Sin horario de verano: su desfase es fijo y la prueba no depende de la fecha
    // en que se ejecute.
    expect(puertoRico?.label).toBe("America/Puerto Rico (GMT-4)");
  });

  it("always offers UTC and keeps a saved zone the browser does not list", () => {
    const values = timezoneOptions("es", "Asia/Kathmandu").map((o) => o.value);

    expect(values).toContain("UTC");
    expect(values).toContain("Asia/Kathmandu");
  });
});
