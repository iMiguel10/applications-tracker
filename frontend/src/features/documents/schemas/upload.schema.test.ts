import { describe, expect, it } from "vitest";

import { uploadSchema } from "./upload.schema";

const MAX = 1024;
const pdf = (size: number, name = "cv.pdf", type = "application/pdf") =>
  new File([new Uint8Array(size)], name, { type });

function firstError(file: File | null): string | undefined {
  const result = uploadSchema(MAX).safeParse({ kind: "cv", file });
  return result.success ? undefined : result.error.issues[0]?.message;
}

describe("uploadSchema", () => {
  it("acepta un PDF dentro del tamaño máximo", () => {
    expect(firstError(pdf(MAX))).toBeUndefined();
  });

  it("pide un fichero", () => {
    expect(firstError(null)).toBe("documents.validation.fileRequired");
  });

  it("avisa si no parece un PDF", () => {
    expect(firstError(pdf(10, "cv.docx", "application/msword"))).toBe(
      "documents.validation.notPdf",
    );
  });

  it("avisa si pasa del tamaño máximo", () => {
    expect(firstError(pdf(MAX + 1))).toBe("documents.validation.tooLarge");
  });
});
