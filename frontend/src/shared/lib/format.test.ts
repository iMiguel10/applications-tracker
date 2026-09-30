import { describe, expect, it } from "vitest";

import { formatBytes } from "./format";

describe("formatBytes", () => {
  it("usa la unidad más grande que no baje de 1, en múltiplos de 1024", () => {
    expect(formatBytes(0, "en")).toBe("0 B");
    expect(formatBytes(1536, "en")).toBe("1.5 kB");
    expect(formatBytes(100 * 1024 * 1024, "en")).toBe("100 MB");
    expect(formatBytes(5 * 1024 ** 3, "en")).toBe("5 GB");
  });

  it("formatea en el idioma de la interfaz", () => {
    expect(formatBytes(1.5 * 1024 * 1024, "es")).toBe("1,5 MB");
  });
});
