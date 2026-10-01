export const DOCUMENT_KINDS = ["cv", "cover_letter"] as const;
export type DocumentKind = (typeof DOCUMENT_KINDS)[number];

/** RF-91: subido, generado desde el perfil (F14) o adaptado con IA (F15). */
export type DocumentOrigin = "uploaded" | "generated" | "ai_tailored";
export type DocumentStatus = "pending" | "ready" | "failed";
/** Por qué falló un CV generado (F14). */
export type DocumentErrorCode = "render_failed" | "storage_limit_reached";

/** Un CV o una carta de la biblioteca (RF-90). */
export interface LibraryDocument {
  id: string;
  kind: DocumentKind;
  origin: DocumentOrigin;
  status: DocumentStatus;
  /** Nombre visible, saneado por la API. */
  name: string;
  size_bytes: number | null;
  /** Solo en los generados: el diseño (`CvDesign.key`) y el idioma de las etiquetas. */
  template: string | null;
  language: string | null;
  /** Solo en `failed`. */
  error_code: DocumentErrorCode | null;
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

/** Un diseño de CV (RF-104). `names` y `descriptions` van por idioma de la interfaz. */
export interface CvDesign {
  key: string;
  names: Record<string, string>;
  descriptions: Record<string, string>;
  /** Idiomas en que puede salir el CV (sus etiquetas fijas). */
  languages: string[];
  /** RF-105: `false` en un diseño gráfico que un ATS podría leer desordenado. */
  ats_friendly: boolean;
}

export const CV_SECTIONS = [
  "summary",
  "experience",
  "education",
  "project",
  "certification",
  "skills",
  "languages",
] as const;
export type CvSection = (typeof CV_SECTIONS)[number];

/** `POST /documents/generate` (RF-103). */
export interface CvGenerateInput {
  design: string;
  language: string;
  name: string;
  sections: CvSection[];
  /** Entradas, logros, habilidades o idiomas que dejar fuera, por id. */
  excluded_ids: string[];
}
