import { describe, expect, it } from "vitest";

import type { CoverLetterProposal } from "../types/Ai";
import { letterFromProposal, letterProblem, toReviewedLetter, wordCount } from "./letter";

const PROPOSAL: CoverLetterProposal = {
  greeting: "Estimado equipo de Acme:",
  paragraphs: [
    { text: "Me presento al puesto.", sources: [] },
    { text: "Optimicé SQL en Acme.", sources: [{ kind: "bullet", id: "b1" }] },
  ],
  closing: "Atentamente,",
};

describe("letter", () => {
  it("cada párrafo conserva sus fuentes y una clave estable para reordenar", () => {
    const state = letterFromProposal(PROPOSAL);

    expect(state.paragraphs.map((paragraph) => paragraph.key)).toEqual(["p0", "p1"]);
    expect(state.paragraphs[1].sources).toEqual([{ kind: "bullet", id: "b1" }]);
  });

  it("solo envía el texto revisado, sin las fuentes ni espacios de más", () => {
    const state = letterFromProposal(PROPOSAL);
    state.paragraphs[0].text = "  Me presento al puesto de backend.  ";

    expect(toReviewedLetter(state)).toEqual({
      greeting: "Estimado equipo de Acme:",
      paragraphs: ["Me presento al puesto de backend.", "Optimicé SQL en Acme."],
      closing: "Atentamente,",
    });
  });

  it("dice qué falta para poder generar el PDF", () => {
    const state = letterFromProposal(PROPOSAL);
    expect(letterProblem(state)).toBeNull();
    expect(letterProblem({ ...state, greeting: " " })).toBe("greeting");
    expect(letterProblem({ ...state, closing: "x".repeat(201) })).toBe("closing");
    expect(letterProblem({ ...state, paragraphs: [] })).toBe("paragraphs");
    expect(letterProblem({ ...state, paragraphs: [{ key: "p0", text: "  ", sources: [] }] })).toBe(
      "emptyParagraph",
    );
  });

  it("cuenta las palabras de los párrafos", () => {
    expect(wordCount(letterFromProposal(PROPOSAL))).toBe(8);
  });
});
