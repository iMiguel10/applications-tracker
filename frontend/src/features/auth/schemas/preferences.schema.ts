import { z } from "zod";
import { LANGUAGES } from "../types/Auth";

// Solo formato, para dar respuesta inmediata. La autoridad es el backend (1-90).
export const preferencesSchema = z.object({
  language: z.enum(LANGUAGES).nullable(),
  stale_after_days: z
    .string()
    .trim()
    .regex(/^\d{1,2}$/, "preferences.validation.staleAfterDays")
    .refine(
      (v) => Number(v) >= 1 && Number(v) <= 90,
      "preferences.validation.staleAfterDays",
    ),
  // La lista la da el navegador; el backend comprueba que la zona existe.
  timezone: z.string().nullable(),
});

export type PreferencesFormValues = z.infer<typeof preferencesSchema>;
