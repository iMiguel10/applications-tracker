import { describe, expect, it } from "vitest";

import { downloadName } from "./fileName";

describe("downloadName", () => {
  it("mantiene el nombre si ya acaba en .pdf, sin mirar mayúsculas", () => {
    expect(downloadName("currículum.pdf")).toBe("currículum.pdf");
    expect(downloadName("CV.PDF")).toBe("CV.PDF");
  });

  it("añade .pdf si no lo lleva", () => {
    expect(downloadName("passwd")).toBe("passwd.pdf");
  });
});
