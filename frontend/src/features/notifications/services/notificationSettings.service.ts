import { apiClient } from "@/shared/lib/apiClient";
import type { Preferences } from "@/features/auth/types/Auth";
import type { NotificationSettings } from "../types/NotificationSettings";

export const notificationSettingsService = {
  /** Solo los campos que cambian: el resto de preferencias no se toca. */
  update: (changes: Partial<NotificationSettings>) =>
    apiClient.patch<Preferences>("/me/preferences", changes),
};
