import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { HelpLink } from "./HelpLink";

afterEach(async () => {
  cleanup();
  await i18n.changeLanguage("es");
});

describe("HelpLink (issue #6)", () => {
  it("abre la página del manual en otra pestaña, con un texto que dice de qué es", async () => {
    await i18n.changeLanguage("es");
    render(<HelpLink page="board" />);

    const link = screen.getByRole("link", {
      name: `${i18n.t("help.pages.board")} ${i18n.t("help.newTab")}`,
    });
    // La base depende de VITE_MANUAL_URL (en el contenedor de desarrollo, otro servidor).
    expect(link.getAttribute("href")).toMatch(/\/uso\/tablero$/);
    expect(link.getAttribute("href")).not.toContain("/en/");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link.getAttribute("rel")).toContain("noopener");
  });

  it("en inglés, el manual en inglés", async () => {
    await i18n.changeLanguage("en");
    render(<HelpLink page="board" />);

    expect(screen.getByRole("link").getAttribute("href")).toMatch(/\/en\/uso\/tablero$/);
  });
});
