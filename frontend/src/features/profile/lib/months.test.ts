import { describe, expect, it } from "vitest";

import { formatMonth, fromMonthYear, monthOptions, toMonthYear, yearOptions } from "./months";

describe("months", () => {
  it("separa y vuelve a unir mes y año", () => {
    expect(toMonthYear("2021-03-01")).toEqual({ month: "03", year: "2021" });
    expect(fromMonthYear({ month: "03", year: "2021" })).toBe("2021-03-01");
    expect(fromMonthYear({ month: "03", year: null })).toBeNull();
    expect(toMonthYear(null)).toEqual({ month: null, year: null });
  });

  it("nombra los meses en el idioma pedido, con mayúscula", () => {
    expect(monthOptions("es")[0]).toEqual({ value: "01", label: "Enero" });
    expect(monthOptions("en")[11]).toEqual({ value: "12", label: "December" });
  });

  it("ofrece años de 5 por delante hasta 1950", () => {
    const years = yearOptions(new Date(2026, 8, 30));
    expect(years[0].value).toBe("2031");
    expect(years.at(-1)?.value).toBe("1950");
  });

  it("formatea el mes sin desplazarse por la zona horaria", () => {
    // Medianoche UTC del día 1 sería el mes anterior al oeste de UTC.
    expect(formatMonth("2021-03-01", "en")).toBe("Mar 2021");
  });
});
