import type { ProfileEntry } from "@/features/profile/types/ProfileEntry";
import type { ProfileSkill } from "@/features/profile/types/ProfileSkill";
import type { CvProposal, ReviewedCvProposal } from "../types/Ai";

/** Mismos topes que el backend (domain/profile.py). */
export const BULLET_MAX_LENGTH = 500;
export const SUMMARY_MAX_LENGTH = 2000;

/** Un logro en la revisión: el texto propuesto (editable) junto a su original del
 * perfil (RF-118). `original` es null si el logro ya no está en el perfil. */
export interface ReviewBullet {
  bulletId: string;
  original: string | null;
  text: string;
}

/** Una experiencia en la revisión. El puesto, la empresa y las fechas salen del
 * perfil (`entry`): la propuesta no puede cambiarlos (RF-111). */
export interface ReviewExperience {
  entryId: string;
  entry: ProfileEntry | null;
  bullets: ReviewBullet[];
}

export interface ReviewSkill {
  id: string;
  /** null si la habilidad ya no está en el perfil. */
  name: string | null;
}

export interface ReviewState {
  summary: string;
  experiences: ReviewExperience[];
  skills: ReviewSkill[];
}

/** La propuesta cruzada con el perfil actual, para revisarla (RF-113). */
export function reviewFromProposal(
  proposal: CvProposal,
  entries: ProfileEntry[],
  skills: ProfileSkill[],
): ReviewState {
  const entriesById = new Map(entries.map((entry) => [entry.id, entry]));
  const skillsById = new Map(skills.map((skill) => [skill.id, skill]));
  return {
    summary: proposal.summary,
    experiences: proposal.experiences.map((experience) => {
      const entry = entriesById.get(experience.entry_id) ?? null;
      const originals = new Map(entry?.bullets.map((bullet) => [bullet.id, bullet.text]));
      return {
        entryId: experience.entry_id,
        entry,
        bullets: experience.bullets.map((bullet) => ({
          bulletId: bullet.bullet_id,
          original: originals.get(bullet.bullet_id) ?? null,
          text: bullet.text,
        })),
      };
    }),
    skills: proposal.skill_ids.map((id) => ({ id, name: skillsById.get(id)?.name ?? null })),
  };
}

/** El perfil cambió desde que se pidió: algo de la propuesta ya no está en él y
 * el backend respondería `ai_proposal_outdated`. */
export function isOutdated(state: ReviewState): boolean {
  return (
    state.experiences.some(
      (experience) =>
        experience.entry === null || experience.bullets.some((bullet) => bullet.original === null),
    ) || state.skills.some((skill) => skill.name === null)
  );
}

/** Lo que falta para poder generar el PDF, o null si se puede. */
export function reviewProblem(
  state: ReviewState,
): "outdated" | "summary" | "experiences" | "bullets" | null {
  if (isOutdated(state)) return "outdated";
  const summary = state.summary.trim();
  if (!summary || summary.length > SUMMARY_MAX_LENGTH) return "summary";
  if (state.experiences.length === 0) return "experiences";
  const badBullet = state.experiences.some((experience) =>
    experience.bullets.some(
      (bullet) => !bullet.text.trim() || bullet.text.trim().length > BULLET_MAX_LENGTH,
    ),
  );
  return badBullet ? "bullets" : null;
}

/** Lo que se envía al generar el PDF. */
export function toReviewedProposal(state: ReviewState): ReviewedCvProposal {
  return {
    summary: state.summary.trim(),
    experiences: state.experiences.map((experience) => ({
      entry_id: experience.entryId,
      bullets: experience.bullets.map((bullet) => ({
        bullet_id: bullet.bulletId,
        text: bullet.text.trim(),
      })),
    })),
    skill_ids: state.skills.map((skill) => skill.id),
  };
}

/** El texto se cambió respecto al original del perfil: la interfaz lo resalta para
 * que una exageración se vea a simple vista (RF-118). */
export const isRewritten = (bullet: ReviewBullet) =>
  bullet.original !== null && comparable(bullet.original) !== comparable(bullet.text);

// Un punto final o un espacio de más no es reescribir.
const comparable = (text: string) => text.trim().replace(/[.\s]+$/, "");
