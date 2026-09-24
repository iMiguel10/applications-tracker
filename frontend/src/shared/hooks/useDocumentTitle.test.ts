import { renderHook } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { useDocumentTitle } from "./useDocumentTitle";

describe("useDocumentTitle", () => {
  beforeAll(async () => {
    await i18n.changeLanguage("es");
  });

  it("prefixes the page title to the app name", () => {
    renderHook(() => useDocumentTitle("Solicitudes"));

    expect(document.title).toBe(`Solicitudes · ${i18n.t("app.name")}`);
  });

  it("falls back to the bare app name while the title is not known yet", () => {
    renderHook(() => useDocumentTitle(undefined));

    expect(document.title).toBe(i18n.t("app.name"));
  });

  it("follows the title when it changes, e.g. once the application has loaded", () => {
    const { rerender } = renderHook(({ title }) => useDocumentTitle(title), {
      initialProps: { title: undefined as string | undefined },
    });

    rerender({ title: "Backend developer" });

    expect(document.title).toBe(`Backend developer · ${i18n.t("app.name")}`);
  });
});
