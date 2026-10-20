import { describe, expect, it } from "vitest";

import { manualBase, manualUrl } from "./manual";

describe("manualBase", () => {
  it("sin configurar, el manual del mismo dominio", () => {
    expect(manualBase(undefined)).toBe("/manual/");
    expect(manualBase("  ")).toBe("/manual/");
  });

  it("añade la barra final si falta", () => {
    expect(manualBase("http://localhost:3001")).toBe("http://localhost:3001/");
    expect(manualBase("/manual/")).toBe("/manual/");
  });
});

describe("manualUrl", () => {
  it("en español, en la raíz del manual", () => {
    expect(manualUrl("board", "es", "/manual/")).toBe("/manual/uso/tablero");
  });

  it("en inglés, bajo en/", () => {
    expect(manualUrl("board", "en", "/manual/")).toBe("/manual/en/uso/tablero");
    expect(manualUrl("board", "en-GB", "/manual/")).toBe("/manual/en/uso/tablero");
  });

  it("la portada es la base, con su idioma", () => {
    expect(manualUrl("home", "es", "/manual/")).toBe("/manual/");
    expect(manualUrl("home", "en", "/manual/")).toBe("/manual/en/");
  });

  it("un idioma sin manual cae en el español", () => {
    expect(manualUrl("calendar", undefined, "/manual/")).toBe("/manual/uso/calendario");
    expect(manualUrl("calendar", "fr", "/manual/")).toBe("/manual/uso/calendario");
  });

  it("con el manual en otro servidor (desarrollo)", () => {
    expect(manualUrl("dashboard", "es", "http://localhost:3001/")).toBe(
      "http://localhost:3001/uso/dashboard",
    );
  });
});
