import type { CoverLetterProposal, ProfileReference, ReviewedCoverLetter } from "../types/Ai";

/** Mismos topes que el backend (domain/ai.py). */
export const LETTER_PARAGRAPH_MAX_LENGTH = 1500;
export const LETTER_LINE_MAX_LENGTH = 200;
export const MAX_LETTER_PARAGRAPHS = 8;

/** Un párrafo en la revisión: su texto (editable) y en qué se apoya del perfil.
 * `key` identifica la fila al reordenar; el texto cambia y no sirve de clave. */
export interface ReviewParagraph {
  key: string;
  text: string;
  sources: ProfileReference[];
}

export interface LetterState {
  greeting: string;
  paragraphs: ReviewParagraph[];
  closing: string;
}

export function letterFromProposal(proposal: CoverLetterProposal): LetterState {
  return {
    greeting: proposal.greeting,
    paragraphs: proposal.paragraphs.map((paragraph, index) => ({
      key: `p${index}`,
      text: paragraph.text,
      sources: paragraph.sources,
    })),
    closing: proposal.closing,
  };
}

/** Lo que falta para poder generar el PDF, o null si se puede. */
export function letterProblem(
  state: LetterState,
): "greeting" | "closing" | "paragraphs" | "emptyParagraph" | null {
  const line = (text: string) => !!text.trim() && text.trim().length <= LETTER_LINE_MAX_LENGTH;
  if (!line(state.greeting)) return "greeting";
  if (!line(state.closing)) return "closing";
  if (state.paragraphs.length === 0 || state.paragraphs.length > MAX_LETTER_PARAGRAPHS) {
    return "paragraphs";
  }
  const bad = state.paragraphs.some(
    (paragraph) =>
      !paragraph.text.trim() || paragraph.text.trim().length > LETTER_PARAGRAPH_MAX_LENGTH,
  );
  return bad ? "emptyParagraph" : null;
}

/** Lo que se envía al generar el PDF: solo el texto, las fuentes son para revisar. */
export function toReviewedLetter(state: LetterState): ReviewedCoverLetter {
  return {
    greeting: state.greeting.trim(),
    paragraphs: state.paragraphs.map((paragraph) => paragraph.text.trim()),
    closing: state.closing.trim(),
  };
}

/** Cuántas palabras tiene la carta: la IA apunta a 250-350, una página. */
export const wordCount = (state: LetterState) =>
  state.paragraphs
    .map((paragraph) => paragraph.text.trim().split(/\s+/).filter(Boolean).length)
    .reduce((sum, count) => sum + count, 0);
