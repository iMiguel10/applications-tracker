import type { Profile } from "@/features/profile/types/Profile";
import type { ProfileEntry } from "@/features/profile/types/ProfileEntry";
import type { ProfileLanguage, ProfileSkill } from "@/features/profile/types/ProfileSkill";
import type { Requirement } from "../types/Ai";
import type { ReviewState } from "./review";

/**
 * Encaje con la oferta (ia.md §4): cuánto de lo que pide la oferta aparece, con
 * sus palabras, en el texto del CV. Es lo que hace un filtro ATS, no la
 * probabilidad de que llamen. La IA solo da los requisitos y cómo se buscarían;
 * el cálculo es de aquí, determinista y al momento mientras se revisa.
 */

/** Lo que pesa cada requisito: un imprescindible cuenta el doble. */
const WEIGHT = { required: 2, preferred: 1 } as const;

/** Sin mayúsculas, tildes ni puntuación: "PostgreSQL 16." y "postgresql" son la
 * misma palabra. Se conservan `+` y `#` (C++, C#). */
export function tokenize(text: string): string[] {
  return text
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}+#]+/gu, " ")
    .split(" ")
    .filter(Boolean);
}

const isNumber = (token: string) => /^\d+$/.test(token);

// Un plural es la misma palabra: "API" y "APIs", "servidor" y "servidores".
const sameWord = (a: string, b: string) =>
  a === b ||
  (Math.min(a.length, b.length) >= 3 &&
    (a + "s" === b || b + "s" === a || a + "es" === b || b + "es" === a));

/** Las palabras de una búsqueda, sin versiones: "Python 3" busca "python". */
function keywordTokens(keyword: string): string[] {
  const tokens = tokenize(keyword);
  const words = tokens.filter((token) => !isNumber(token));
  return words.length > 0 ? words : tokens;
}

/** Si `keyword` aparece en el texto como palabras seguidas (no dentro de otra:
 * "Go" no está en "Google"). "Node JS" también vale como "nodejs". */
export function containsKeyword(textTokens: string[], keyword: string): boolean {
  const words = keywordTokens(keyword);
  if (words.length === 0) return false;
  const joined = words.join("");
  for (let start = 0; start < textTokens.length; start++) {
    if (words.length > 1 && sameWord(textTokens[start], joined)) return true;
    if (
      words.every((word, offset) => {
        const token = textTokens[start + offset];
        return token !== undefined && sameWord(token, word);
      })
    ) {
      return true;
    }
  }
  return false;
}

export interface CvSource {
  profile: Profile | null;
  entries: ProfileEntry[];
  skills: ProfileSkill[];
  languages: ProfileLanguage[];
}

// Como lo imprime el CV: "Inglés (B2)", así que "Inglés B2" también cuenta.
const languageText = ({ language, level }: ProfileLanguage) =>
  level === "native" ? language : `${language} ${level.toUpperCase()}`;

const entryText = (entry: ProfileEntry, bullets: string[]) => [
  entry.title,
  entry.organization,
  entry.description,
  ...bullets,
];

/** El texto del CV generado con el perfil tal cual, sin adaptar. */
export function profileCvText({ profile, entries, skills, languages }: CvSource): string {
  return [
    profile?.headline,
    profile?.summary,
    ...entries.flatMap((entry) =>
      entryText(
        entry,
        entry.bullets.map((bullet) => bullet.text),
      ),
    ),
    ...skills.map((skill) => skill.name),
    ...languages.map(languageText),
  ]
    .filter(Boolean)
    .join("\n");
}

/** El texto del CV adaptado tal como queda en la revisión: lo mismo que hace el
 * backend al generarlo (`apply_cv_proposal`). */
export function reviewedCvText(state: ReviewState, source: CvSource): string {
  const selected = new Set(state.skills.map((skill) => skill.id));
  return [
    source.profile?.headline,
    state.summary,
    ...state.experiences.flatMap((experience) =>
      experience.entry
        ? entryText(
            experience.entry,
            experience.bullets.map((bullet) => bullet.text),
          )
        : experience.bullets.map((bullet) => bullet.text),
    ),
    ...source.entries
      .filter((entry) => entry.kind !== "experience")
      .flatMap((entry) =>
        entryText(
          entry,
          entry.bullets.map((bullet) => bullet.text),
        ),
      ),
    ...source.skills.filter((skill) => selected.has(skill.id)).map((skill) => skill.name),
    ...source.languages.map(languageText),
  ]
    .filter(Boolean)
    .join("\n");
}

/**
 * - `covered`: el CV lo nombra con alguna de sus palabras. Es lo único que suma.
 * - `dropped`: el perfil lo nombra, pero esta versión del CV no (se quitó).
 * - `unnamed`: el perfil lo demuestra (según la IA), pero con otras palabras.
 * - `missing`: no está en el perfil.
 */
export type RequirementState = "covered" | "dropped" | "unnamed" | "missing";

export interface RequirementMatch {
  requirement: Requirement;
  state: RequirementState;
}

export interface OfferMatch {
  /** Porcentaje con el CV del perfil tal cual. */
  before: number;
  /** Porcentaje con el CV tal como queda en la revisión. */
  after: number;
  requirements: RequirementMatch[];
}

const covers = (tokens: string[], requirement: Requirement) =>
  requirement.keywords.some((keyword) => containsKeyword(tokens, keyword));

function score(requirements: Requirement[], covered: (r: Requirement) => boolean): number {
  const total = requirements.reduce((sum, item) => sum + WEIGHT[item.importance], 0);
  const got = requirements.filter(covered).reduce((sum, item) => sum + WEIGHT[item.importance], 0);
  return total === 0 ? 0 : Math.round((got / total) * 100);
}

/** El encaje antes y después, o null si la propuesta no trae requisitos (cv/v1). */
export function offerMatch(
  requirements: Requirement[] | null | undefined,
  state: ReviewState,
  source: CvSource,
): OfferMatch | null {
  if (!requirements || requirements.length === 0) return null;
  const before = tokenize(profileCvText(source));
  const after = tokenize(reviewedCvText(state, source));
  return {
    before: score(requirements, (item) => covers(before, item)),
    after: score(requirements, (item) => covers(after, item)),
    requirements: requirements.map((requirement) => ({
      requirement,
      state: covers(after, requirement)
        ? "covered"
        : covers(before, requirement)
          ? "dropped"
          : requirement.evidence.length > 0
            ? "unnamed"
            : "missing",
    })),
  };
}

/** Cómo se llama en el perfil lo que la IA dio como evidencia de un requisito. */
export function evidenceLabels(requirement: Requirement, source: CvSource): string[] {
  const bullets = new Map(
    source.entries.flatMap((entry) => entry.bullets.map((bullet) => [bullet.id, bullet.text])),
  );
  const entries = new Map(source.entries.map((entry) => [entry.id, entry.title]));
  const skills = new Map(source.skills.map((skill) => [skill.id, skill.name]));
  const languages = new Map(source.languages.map((item) => [item.id, item.language]));
  const lookup = {
    bullet: bullets,
    entry: entries,
    skill: skills,
    language: languages,
  };
  return requirement.evidence
    .map((item) => lookup[item.kind].get(item.id))
    .filter((label): label is string => !!label);
}
