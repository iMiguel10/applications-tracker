import { apiClient } from "@/shared/lib/apiClient";
import type { UnsubscribeResult } from "../types/NotificationSettings";

const path = (token: string) =>
  `/notifications/unsubscribe?token=${encodeURIComponent(token)}`;

/** Baja con el enlace del email (RF-85). Sin sesión: el token firmado basta. */
export const unsubscribeService = {
  /** Qué aviso es, sin aplicar nada. */
  describe: (token: string) => apiClient.get<UnsubscribeResult>(path(token)),
  confirm: (token: string) => apiClient.post<UnsubscribeResult>(path(token)),
};
