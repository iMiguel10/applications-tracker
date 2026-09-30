import { describe, expect, it } from "vitest";

import { entrySchema, toEntryForm, toEntryInput } from "./entry.schema";
import type { ProfileEntry } from "../types/ProfileEntry";

const ENTRY: ProfileEntry = {
  id: "e1",
  kind: "experience",
  title: "Desarrolladora",
  organization: "Acme",
  location: null,
  start_date: "2021-03-01",
  end_date: "2023-06-01",
  is_current: false,
  description: null,
  bullets: [{ id: "b1", text: "Migré los pagos" }],
};

describe("entrySchema", () => {
  it("acepta una entrada guardada tal cual", () => {
    expect(entrySchema.safeParse(toEntryForm(ENTRY)).success).toBe(true);
  });

  it("exige mes y año juntos", () => {
    const values = { ...toEntryForm(ENTRY), start_year: null };
    const result = entrySchema.safeParse(values);
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toEqual(["start_year"]);
  });

  it("rechaza un fin anterior al inicio salvo que siga en curso", () => {
    const values = { ...toEntryForm(ENTRY), end_year: "2020" };
    expect(entrySchema.safeParse(values).success).toBe(false);
    expect(entrySchema.safeParse({ ...values, is_current: true }).success).toBe(true);
  });

  it("rechaza un logro vacío", () => {
    const values = { ...toEntryForm(ENTRY), bullets: [{ text: "  " }] };
    expect(entrySchema.safeParse(values).success).toBe(false);
  });
});

describe("toEntryInput", () => {
  it("vuelve a fechas con el día 1 y conserva el id de los logros guardados", () => {
    const form = toEntryForm(ENTRY);
    const input = toEntryInput({
      ...form,
      bullets: [...form.bullets, { text: "Nuevo" }],
    });
    expect(input.start_date).toBe("2021-03-01");
    expect(input.end_date).toBe("2023-06-01");
    expect(input.bullets).toEqual([{ id: "b1", text: "Migré los pagos" }, { text: "Nuevo" }]);
  });

  it("en curso no envía fecha de fin aunque quedara elegida", () => {
    const input = toEntryInput({ ...toEntryForm(ENTRY), is_current: true });
    expect(input.end_date).toBeNull();
  });
});
