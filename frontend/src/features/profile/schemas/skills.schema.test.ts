import { describe, expect, it } from "vitest";

import { languagesSchema, skillsSchema } from "./skills.schema";

const skill = (name: string) => ({ name, category: "", level: null });

describe("skillsSchema", () => {
  it("acepta habilidades distintas", () => {
    expect(skillsSchema.safeParse({ skills: [skill("Python"), skill("SQL")] }).success).toBe(
      true,
    );
  });

  it("marca la repetida sin distinguir mayúsculas, como el backend", () => {
    const result = skillsSchema.safeParse({ skills: [skill("Python"), skill(" python ")] });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0]).toMatchObject({
      path: ["skills", 1, "name"],
      message: "profile.validation.duplicateSkill",
    });
  });

  it("rechaza una habilidad vacía", () => {
    expect(skillsSchema.safeParse({ skills: [skill("  ")] }).success).toBe(false);
  });
});

describe("languagesSchema", () => {
  it("exige el nivel de cada idioma", () => {
    const result = languagesSchema.safeParse({ languages: [{ language: "Inglés", level: null }] });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].message).toBe("profile.validation.languageLevelRequired");
  });

  it("acepta un idioma con nivel", () => {
    const result = languagesSchema.safeParse({ languages: [{ language: "Inglés", level: "c1" }] });
    expect(result.success).toBe(true);
  });
});
