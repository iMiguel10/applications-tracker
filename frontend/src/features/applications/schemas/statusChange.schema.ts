import { z } from "zod";

// Solo formato: la autoridad de qué transiciones son válidas es el backend
// (allowed_transitions, decisión A8). El frontend no repite la tabla de estados.
export const statusChangeSchema = z.object({
  to_status: z.string().min(1, "applications.validation.statusRequired"),
  // "yyyy-MM-dd" o null: sin fecha, el backend usa el instante exacto de ahora.
  changed_at: z.string().nullable(),
  note: z.string().max(5000, "common.validation.notesTooLong"),
});

export type StatusChangeFormValues = z.infer<typeof statusChangeSchema>;

export const emptyStatusChangeForm: StatusChangeFormValues = {
  to_status: "",
  changed_at: null,
  note: "",
};
