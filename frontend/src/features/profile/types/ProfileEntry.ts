export const ENTRY_KINDS = ["experience", "education", "project", "certification"] as const;
export type EntryKind = (typeof ENTRY_KINDS)[number];

export interface EntryBullet {
  id: string;
  text: string;
}

/** Una experiencia, formación, proyecto o certificación (RF-101, RF-102). Las
 * fechas son `yyyy-MM-dd` con el día 1: un CV muestra mes y año. */
export interface ProfileEntry {
  id: string;
  kind: EntryKind;
  title: string;
  organization: string | null;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  description: string | null;
  bullets: EntryBullet[];
}

/** Lo que se envía al guardar. Un logro sin `id` es nuevo; con él, conserva su
 * identidad (F15 los referencia por id). */
export interface EntryInput {
  title: string;
  organization: string;
  location: string;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  description: string;
  bullets: { id?: string; text: string }[];
}

export const MAX_BULLETS_PER_ENTRY = 20;
export const ENTRY_DESCRIPTION_MAX_LENGTH = 2000;
