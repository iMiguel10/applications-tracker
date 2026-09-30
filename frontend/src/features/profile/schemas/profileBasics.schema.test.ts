import { describe, expect, it } from "vitest";

import { profileBasicsSchema, toProfileBasicsForm } from "./profileBasics.schema";
import type { Profile } from "../types/Profile";

const EMPTY: Profile = {
  full_name: null,
  headline: null,
  contact_email: null,
  phone: null,
  location: null,
  links: [],
  summary: null,
};

const valid = { ...toProfileBasicsForm(EMPTY), full_name: "Ana" };

describe("profileBasicsSchema", () => {
  it("acepta un perfil con todo vacío salvo el nombre", () => {
    expect(profileBasicsSchema.safeParse(valid).success).toBe(true);
  });

  it.each(["javascript:alert(1)", "linkedin.com/in/ana", "ftp://example.com", "https://"])(
    "rechaza el enlace %s",
    (url) => {
      const result = profileBasicsSchema.safeParse({ ...valid, links: [{ label: "Web", url }] });
      expect(result.success).toBe(false);
    },
  );

  it("acepta un enlace https", () => {
    const result = profileBasicsSchema.safeParse({
      ...valid,
      links: [{ label: "GitHub", url: "https://github.com/ana" }],
    });
    expect(result.success).toBe(true);
  });

  it("rechaza un email y un teléfono con formato incorrecto", () => {
    expect(profileBasicsSchema.safeParse({ ...valid, contact_email: "ana" }).success).toBe(false);
    expect(profileBasicsSchema.safeParse({ ...valid, phone: "600; DROP" }).success).toBe(false);
  });
});

describe("toProfileBasicsForm", () => {
  it("propone el email de la cuenta si el perfil no tiene uno", () => {
    expect(toProfileBasicsForm(EMPTY, "ana@example.com").contact_email).toBe("ana@example.com");
  });

  it("no pisa el email de contacto guardado", () => {
    const profile = { ...EMPTY, contact_email: "trabajo@example.com" };
    expect(toProfileBasicsForm(profile, "ana@example.com").contact_email).toBe(
      "trabajo@example.com",
    );
  });
});
