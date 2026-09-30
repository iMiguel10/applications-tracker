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

/** Un documento del listado de la biblioteca: con en cuántas solicitudes se envió. */
export interface DocumentListItem extends LibraryDocument {
  applications_count: number;
}

/** Lo que hace falta para ver o descargar un documento. */
export type DocumentRef = Pick<LibraryDocument, "id" | "name" | "kind">;

/** Un documento dentro de una solicitud (el CV y la carta enviados, RF-28). */
export interface DocumentSummary extends DocumentRef {
  status: DocumentStatus;
  archived_at: string | null;
}

/** Una solicitud en la que se envió el documento (RF-92). */
export interface DocumentUsage {
  application_id: string;
  position_title: string;
  company_name: string;
  used_as: DocumentKind;
  application_archived: boolean;
}

/** `GET /documents/{id}`: el documento y dónde se usó. */
export interface DocumentDetail extends LibraryDocument {
  used_in: DocumentUsage[];
}

export type DocumentKindFilter = DocumentKind | "all";

export interface DocumentListParams {
  page: number;
  limit: number;
  kind: DocumentKindFilter;
  /** `true`: solo los archivados (RF-93); `false`: la biblioteca. */
  archived: boolean;
}
