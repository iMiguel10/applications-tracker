import { apiClient } from "@/shared/lib/apiClient";
import { toQueryString } from "@/shared/lib/queryString";
import type { Page } from "@/shared/types/Page";
import type { DocumentKind, DocumentListParams, LibraryDocument } from "../types/Document";

export const documentService = {
  list: ({ kind, ...params }: DocumentListParams) =>
    apiClient.get<Page<LibraryDocument>>(
      `/documents${toQueryString({ ...params, kind: kind === "all" ? undefined : kind })}`,
    ),

  rename: (id: string, name: string) =>
    apiClient.patch<LibraryDocument>(`/documents/${id}`, { name }),

  /** RF-93: archivar lo saca de la biblioteca sin romper sus asociaciones. */
  setArchived: (id: string, archived: boolean) =>
    apiClient.post<LibraryDocument>(`/documents/${id}/${archived ? "archive" : "unarchive"}`),

  remove: (id: string) => apiClient.delete<void>(`/documents/${id}`),

  /** El PDF, como blob: el visor y la descarga lo piden con la sesión, sin
   * navegar a la API (ficheros §4). */
  file: (id: string) => apiClient.getBlob(`/documents/${id}/file`),

  /** El PDF viaja tal cual; el tipo y el nombre, en la query (RF-90). */
  upload: (kind: DocumentKind, file: File) =>
    apiClient.upload<LibraryDocument>(
      `/documents${toQueryString({ kind, name: file.name })}`,
      file,
      "application/pdf",
    ),
};
