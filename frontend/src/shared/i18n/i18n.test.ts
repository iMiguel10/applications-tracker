import { afterAll, afterEach, describe, expect, it, vi } from "vitest";

import i18n, { browserLanguage, chooseBrowserLanguage } from "./i18n";

describe("<html lang>", () => {
  afterAll(async () => {
    await i18n.changeLanguage("es");
  });

  it("follows the interface language so screen readers pick the right pronunciation", async () => {
    await i18n.changeLanguage("en");
    expect(document.documentElement.lang).toBe("en");

    await i18n.changeLanguage("es");
    expect(document.documentElement.lang).toBe("es");
  });
});

describe("browserLanguage", () => {
  afterEach(async () => {
    localStorage.clear();
    vi.restoreAllMocks();
    await i18n.changeLanguage("es");
  });

  it("uses the system language when nothing was chosen", () => {
    vi.spyOn(navigator, "language", "get").mockReturnValue("en-GB");
    expect(browserLanguage()).toBe("en");
  });

  it("falls back to Spanish for an unsupported system language", () => {
    vi.spyOn(navigator, "language", "get").mockReturnValue("fr-FR");
    expect(browserLanguage()).toBe("es");
  });

  it("prefers the language chosen on the sign-in screen over the system one", async () => {
    vi.spyOn(navigator, "language", "get").mockReturnValue("es-ES");

    await chooseBrowserLanguage("en");

    expect(i18n.language).toBe("en");
    // Una cuenta que "sigue al navegador" mantiene lo elegido al iniciar sesión.
    expect(browserLanguage()).toBe("en");
  });
});
