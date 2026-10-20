import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { ManualLink } from "./ManualLink";

afterEach(async () => {
  cleanup();
  await i18n.changeLanguage("es");
});

describe("ManualLink (issue #6)", () => {
  it("lleva a la portada del manual en otra pestaña y lo anuncia", async () => {
    await i18n.changeLanguage("es");
    render(<ManualLink />);

    const link = screen.getByRole("link", {
      name: `${i18n.t("help.link")} ${i18n.t("help.newTab")}`,
    });
    expect(link.getAttribute("href")).toMatch(/\/$/);
    expect(link.getAttribute("href")).not.toContain("/en/");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("en inglés, la portada del manual en inglés", async () => {
    await i18n.changeLanguage("en");
    render(<ManualLink />);

    expect(screen.getByRole("link").getAttribute("href")).toMatch(/\/en\/$/);
  });
});
