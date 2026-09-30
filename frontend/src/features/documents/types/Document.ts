export const DOCUMENT_KINDS = ["cv", "cover_letter"] as const;
export type DocumentKind = (typeof DOCUMENT_KINDS)[number];

/** RF-91: subido, generado desde el perfil (F14) o adaptado con IA (F15). */
export type DocumentOrigin = "uploaded" | "generated" | "ai_tailored";
export type DocumentStatus = "pending" | "ready" | "failed";

/** Un CV o una carta de la biblioteca (RF-90). */
export interface LibraryDocument {
  id: string;
  kind: DocumentKind;
  origin: DocumentOrigin;
  status: DocumentStatus;
  /** Nombre visible, saneado por la API. */
  name: string;
  size_bytes: number | null;
  /** Archivado (RF-93): fuera de la biblioteca, pero sigue ocupando espacio. */
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export type DocumentKindFilter = DocumentKind | "all";

export interface DocumentListParams {
  page: number;
  limit: number;
  kind: DocumentKindFilter;
}
