import { apiClient } from "@/shared/lib/apiClient";
import { toQueryString } from "@/shared/lib/queryString";
import type { Page } from "@/shared/types/Page";
import type { DocumentKind, DocumentListParams, LibraryDocument } from "../types/Document";

export const documentService = {
  list: ({ kind, ...params }: DocumentListParams) =>
    apiClient.get<Page<LibraryDocument>>(
      `/documents${toQueryString({ ...params, kind: kind === "all" ? undefined : kind })}`,
    ),

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
