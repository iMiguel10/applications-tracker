import { z } from "zod";

import { DOCUMENT_KINDS } from "../types/Document";

/** Aviso amable antes de subir: la API comprueba el contenido de verdad (RF-94). */
export function looksLikePdf(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

/** El tamaño máximo lo da la instalación (`GET /meta`): el esquema se construye con él. */
export function uploadSchema(maxBytes: number) {
  return z.object({
    kind: z.enum(DOCUMENT_KINDS),
    file: z
      .custom<File | null>()
      // ": boolean" evita que TS lo tome por un guard y el tipo de salida deje de admitir null.
      .refine((file): boolean => file instanceof File, "documents.validation.fileRequired")
      .refine((file) => !file || looksLikePdf(file), "documents.validation.notPdf")
      .refine((file) => !file || file.size <= maxBytes, "documents.validation.tooLarge"),
  });
}

export type UploadFormValues = z.infer<ReturnType<typeof uploadSchema>>;

export const emptyUploadForm: UploadFormValues = { kind: "cv", file: null };
