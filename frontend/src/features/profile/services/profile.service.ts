import { apiClient } from "@/shared/lib/apiClient";
import type { Profile } from "../types/Profile";
import type { ProfileBasicsFormValues } from "../schemas/profileBasics.schema";

export const profileService = {
  get: () => apiClient.get<Profile>("/profile"),

  /** Sustituye los datos básicos enteros; un campo vacío se guarda como `null`. */
  update: (values: ProfileBasicsFormValues) => apiClient.put<Profile>("/profile", values),
};
