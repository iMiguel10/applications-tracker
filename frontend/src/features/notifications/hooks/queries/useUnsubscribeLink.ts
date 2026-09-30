import { useQuery } from "@tanstack/react-query";
import { notificationKeys } from "../../notifications.keys";
import { unsubscribeService } from "../../services/unsubscribe.service";

/** De qué aviso es un enlace de baja. Solo lee: la baja se aplica al confirmar. */
export function useUnsubscribeLink(token: string | null) {
  return useQuery({
    queryKey: notificationKeys.unsubscribeLink(token ?? ""),
    queryFn: () => unsubscribeService.describe(token ?? ""),
    enabled: Boolean(token),
  });
}
