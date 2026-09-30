import { z } from "zod";

import {
  LANGUAGE_LEVELS,
  MAX_LANGUAGES,
  MAX_SKILLS,
  SKILL_LEVELS,
  type ProfileLanguage,
  type ProfileSkill,
} from "../types/ProfileSkill";

// El `id` es el del elemento guardado; sin él, es nuevo. La clave de la fila en la
// lista es otra (`keyName: "key"` en `useFieldArray`).

/** Marca el segundo y siguientes nombres repetidos, sin distinguir mayúsculas,
 * como hace el backend. */
function rejectRepeated<T>(
  items: T[],
  nameOf: (item: T) => string,
  field: string,
  message: string,
  ctx: z.RefinementCtx,
) {
  const seen = new Set<string>();
  items.forEach((item, index) => {
    const key = nameOf(item).trim().toLowerCase();
    if (!key) return;
    if (seen.has(key)) ctx.addIssue({ code: "custom", path: [index, field], message });
    seen.add(key);
  });
}

export const skillsSchema = z.object({
  skills: z
    .array(
      z.object({
        id: z.string().optional(),
        name: z
          .string()
          .trim()
          .min(1, "profile.validation.skillRequired")
          .max(100, "common.validation.tooLong"),
        category: z.string().trim().max(100, "common.validation.tooLong"),
        level: z.enum(SKILL_LEVELS).nullable(),
      }),
    )
    .max(MAX_SKILLS)
    .superRefine((skills, ctx) =>
      rejectRepeated(skills, (skill) => skill.name, "name", "profile.validation.duplicateSkill", ctx),
    ),
});

export type SkillsFormValues = z.infer<typeof skillsSchema>;

export function toSkillsForm(skills: ProfileSkill[]): SkillsFormValues {
  return {
    skills: skills.map(({ id, name, category, level }) => ({
      id,
      name,
      category: category ?? "",
      level,
    })),
  };
}

export const languagesSchema = z.object({
  languages: z
    .array(
      z.object({
        id: z.string().optional(),
        language: z
          .string()
          .trim()
          .min(1, "profile.validation.languageRequired")
          .max(100, "common.validation.tooLong"),
        // Nulo solo mientras se edita: un idioma recién añadido aún no lo tiene.
        level: z
          .enum(LANGUAGE_LEVELS)
          .nullable()
          // `: boolean` a propósito: como guarda de tipo, zod quitaría el null del tipo
          // del formulario y el idioma recién añadido no podría empezar sin nivel.
          .refine((level): boolean => level !== null, "profile.validation.languageLevelRequired"),
      }),
    )
    .max(MAX_LANGUAGES)
    .superRefine((languages, ctx) =>
      rejectRepeated(
        languages,
        (language) => language.language,
        "language",
        "profile.validation.duplicateLanguage",
        ctx,
      ),
    ),
});

export type LanguagesFormValues = z.infer<typeof languagesSchema>;


export function toLanguagesForm(languages: ProfileLanguage[]): LanguagesFormValues {
  return { languages: languages.map(({ id, language, level }) => ({ id, language, level })) };
}
