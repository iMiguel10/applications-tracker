import { toDateOnly } from "@/shared/lib/dates";
import { CV_SECTIONS, type CvSection } from "../types/Document";

/**
 * Qué entra en un CV generado (RF-103): las secciones marcadas y, dentro de ellas,
 * todo salvo lo excluido. Se guarda al revés que en la interfaz (lo que se quita,
 * no lo que se pone) para que un elemento nuevo del perfil entre por defecto.
 */
export interface CvSelectionState {
  sections: ReadonlySet<CvSection>;
  excluded: ReadonlySet<string>;
}

export const fullSelection = (): CvSelectionState => ({
  sections: new Set(CV_SECTIONS),
  excluded: new Set(),
});

export function toggleSection(state: CvSelectionState, section: CvSection): CvSelectionState {
  const sections = new Set(state.sections);
  if (sections.has(section)) sections.delete(section);
  else sections.add(section);
  return { ...state, sections };
}

export function toggleItem(state: CvSelectionState, id: string): CvSelectionState {
  const excluded = new Set(state.excluded);
  if (excluded.has(id)) excluded.delete(id);
  else excluded.add(id);
  return { ...state, excluded };
}

/** Lo que espera la API, en el orden del CV y sin duplicados. */
export function toRequest(state: CvSelectionState) {
  return {
    sections: CV_SECTIONS.filter((section) => state.sections.has(section)),
    excluded_ids: [...state.excluded].sort(),
  };
}

/** "CV Moderno 2026-10-01": el diseño y el día, para distinguirlos en la
 * biblioteca. El usuario lo puede cambiar antes de generar. */
export function defaultCvName(designName: string, today: Date = new Date()): string {
  return `CV ${designName} ${toDateOnly(today)}`;
}
