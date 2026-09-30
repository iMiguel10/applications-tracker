export const SKILL_LEVELS = ["basic", "intermediate", "advanced", "expert"] as const;
export type SkillLevel = (typeof SKILL_LEVELS)[number];

export const LANGUAGE_LEVELS = ["a1", "a2", "b1", "b2", "c1", "c2", "native"] as const;
export type LanguageLevel = (typeof LANGUAGE_LEVELS)[number];

/** Una habilidad (RF-102). En F15 la IA las referencia por id. */
export interface ProfileSkill {
  id: string;
  name: string;
  category: string | null;
  level: SkillLevel | null;
}

export interface ProfileLanguage {
  id: string;
  language: string;
  level: LanguageLevel;
}

export const MAX_SKILLS = 100;
export const MAX_LANGUAGES = 30;
