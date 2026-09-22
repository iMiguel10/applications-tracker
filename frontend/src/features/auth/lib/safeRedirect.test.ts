import { describe, expect, it } from "vitest";
import { safeRedirect } from "./safeRedirect";

describe("safeRedirect", () => {
  it("keeps an internal path with its query string", () => {
    expect(safeRedirect("/applications?page=2")).toBe("/applications?page=2");
  });

  it.each([
    ["missing", null],
    ["empty", ""],
    ["absolute URL", "https://malo.example/phishing"],
    ["protocol-relative URL", "//malo.example"],
    ["backslash trick", "/\\malo.example"],
    ["javascript URL", "javascript:alert(1)"],
  ])("falls back to the default page for a %s redirect", (_, redirect) => {
    expect(safeRedirect(redirect)).toBe("/applications");
  });
});
