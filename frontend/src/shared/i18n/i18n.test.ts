import { afterAll, describe, expect, it } from "vitest";

import i18n from "./i18n";

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
