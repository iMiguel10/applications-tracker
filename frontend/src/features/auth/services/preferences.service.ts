import { apiClient } from "@/shared/lib/apiClient";
import type { Preferences } from "../types/Auth";
import type { PreferencesFormValues } from "../schemas/preferences.schema";

export const preferencesService = {
  get: () => apiClient.get<Preferences>("/me/preferences"),

  update: (values: PreferencesFormValues) =>
    apiClient.patch<Preferences>("/me/preferences", {
      language: values.language,
      stale_after_days: Number(values.stale_after_days),
      timezone: values.timezone,
    }),

  /** Solo la zona: la detección automática no debe tocar el resto. */
  setTimezone: (timezone: string) =>
    apiClient.patch<Preferences>("/me/preferences", { timezone }),
};
