import { describe, expect, it } from "vitest";

import type { ProfileEntry } from "@/features/profile/types/ProfileEntry";
import type { ProfileSkill } from "@/features/profile/types/ProfileSkill";
import type { CvProposal } from "../types/Ai";
import {
  isOutdated,
  isRewritten,
  reviewFromProposal,
  reviewProblem,
  toReviewedProposal,
} from "./review";

const entry = (id: string, bullets: [string, string][]): ProfileEntry => ({
  id,
  kind: "experience",
  title: `Puesto ${id}`,
  organization: "Acme",
  location: null,
  start_date: "2022-01-01",
  end_date: null,
  is_current: true,
  description: null,
  bullets: bullets.map(([bulletId, text]) => ({ id: bulletId, text })),
});

const ENTRIES = [entry("e-a", [["b-a1", "SQL"], ["b-a2", "APIs"]]), entry("e-b", [["b-b1", "Tests"]])];
const SKILLS: ProfileSkill[] = [
  { id: "s-py", name: "Python", category: null, level: null },
  { id: "s-pg", name: "PostgreSQL", category: null, level: null },
];
const PROPOSAL: CvProposal = {
  summary: "Backend con Python",
  experiences: [
    { entry_id: "e-b", bullets: [{ bullet_id: "b-b1", text: "Tests" }] },
    { entry_id: "e-a", bullets: [{ bullet_id: "b-a2", text: "Diseñé APIs REST" }] },
  ],
  skill_ids: ["s-pg", "s-py"],
  gaps: [{ requirement: "Kubernetes", note: "No aparece" }],
};

describe("reviewFromProposal", () => {
  it("pone cada logro propuesto junto a su original, en el orden propuesto", () => {
    const state = reviewFromProposal(PROPOSAL, ENTRIES, SKILLS);

    expect(state.experiences.map((item) => item.entry?.title)).toEqual(["Puesto e-b", "Puesto e-a"]);
    expect(state.experiences[1].bullets).toEqual([
      { bulletId: "b-a2", original: "APIs", text: "Diseñé APIs REST" },
    ]);
    expect(state.skills.map((skill) => skill.name)).toEqual(["PostgreSQL", "Python"]);
    expect(isOutdated(state)).toBe(false);
  });

  it("marca lo que ya no está en el perfil", () => {
    const state = reviewFromProposal(
      {
        ...PROPOSAL,
        experiences: [{ entry_id: "e-a", bullets: [{ bullet_id: "b-borrado", text: "x" }] }],
        skill_ids: ["s-borrada"],
      },
      ENTRIES,
      SKILLS,
    );

    expect(state.experiences[0].bullets[0].original).toBeNull();
    expect(state.skills[0].name).toBeNull();
    expect(isOutdated(state)).toBe(true);
    expect(reviewProblem(state)).toBe("outdated");
  });

  it("marca una experiencia que se borró del perfil", () => {
    const state = reviewFromProposal(
      { ...PROPOSAL, experiences: [{ entry_id: "e-borrada", bullets: [] }] },
      ENTRIES,
      SKILLS,
    );

    expect(state.experiences[0].entry).toBeNull();
    expect(isOutdated(state)).toBe(true);
  });
});

describe("revisión", () => {
  it("distingue un logro reescrito de uno que se deja igual", () => {
    expect(isRewritten({ bulletId: "b", original: "SQL", text: " SQL " })).toBe(false);
    expect(isRewritten({ bulletId: "b", original: "Diseñé APIs", text: "Diseñé APIs." })).toBe(false);
    expect(isRewritten({ bulletId: "b", original: "SQL", text: "Optimicé SQL" })).toBe(true);
    expect(isRewritten({ bulletId: "b", original: null, text: "x" })).toBe(false);
  });

  it("no deja generar sin resumen, sin experiencias o con un logro vacío", () => {
    const state = reviewFromProposal(PROPOSAL, ENTRIES, SKILLS);

    expect(reviewProblem(state)).toBeNull();
    expect(reviewProblem({ ...state, summary: "   " })).toBe("summary");
    expect(reviewProblem({ ...state, experiences: [] })).toBe("experiences");
    const emptyBullet = {
      ...state,
      experiences: [{ ...state.experiences[0], bullets: [{ bulletId: "b-b1", original: "Tests", text: " " }] }],
    };
    expect(reviewProblem(emptyBullet)).toBe("bullets");
  });

  it("envía lo revisado, recortado y en su orden, sin las carencias", () => {
    const state = reviewFromProposal(PROPOSAL, ENTRIES, SKILLS);
    const edited = {
      ...state,
      summary: "  Mi resumen  ",
      experiences: [state.experiences[1]],
      skills: [state.skills[1]],
    };

    expect(toReviewedProposal(edited)).toEqual({
      summary: "Mi resumen",
      experiences: [{ entry_id: "e-a", bullets: [{ bullet_id: "b-a2", text: "Diseñé APIs REST" }] }],
      skill_ids: ["s-py"],
    });
  });
});
